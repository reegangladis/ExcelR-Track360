"""
ExcelR Track360 - Candidate & Cohort Domain Service
Encapsulates CRUD, duplicate prevention, status state machine,
audit recording, and validated CSV bulk ingestion.
"""
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple, Dict, Any
import uuid
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.security import utc_now
from app.modules.candidates.models import (
    Candidate,
    Batch,
    Course,
    CourseTrack,
    Enrollment,
    CandidateNote,
    CandidateStatusHistory,
)
from app.modules.candidates.schemas import (
    CandidateCreate,
    CandidateUpdate,
    CandidateStatusTransitionRequest,
    ImportRowItem,
    ImportPreviewResponse,
    ImportCommitRequest,
    ImportCommitResponse,
)
from app.modules.auth.models import User
from app.modules.audit.models import AuditLog

VALID_LIFECYCLE_STATUSES = {"ENROLLED", "ACTIVE", "ON_HOLD", "DROPPED", "COMPLETED", "ALUMNI"}
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class CandidateService:
    """Service layer managing candidate lifecycle, batch allocations, and imports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_candidate_number(self) -> str:
        """Generates unique sequential candidate identifier, e.g. EX-2026-0001."""
        current_year = datetime.now(timezone.utc).year
        prefix = f"EX-{current_year}-"
        
        count_stmt = select(func.count(Candidate.id)).where(Candidate.candidate_number.like(f"{prefix}%"))
        count = (await self.db.execute(count_stmt)).scalar() or 0
        return f"{prefix}{count + 1:04d}"

    async def create_candidate(
        self,
        payload: CandidateCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_ip: Optional[str] = None,
    ) -> Candidate:
        """
        Creates a new candidate record with duplicate prevention.
        Optionally links to existing user or cohort batch.
        """
        clean_email = payload.email.lower().strip()
        clean_phone = payload.phone.strip()

        # 1. Duplicate check on email
        dup_email = await self.db.execute(
            select(Candidate).where(func.lower(func.trim(Candidate.email)) == clean_email)
        )
        if dup_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate with email '{payload.email}' already exists.",
            )

        # 2. Duplicate check on phone
        dup_phone = await self.db.execute(
            select(Candidate).where(Candidate.phone == clean_phone)
        )
        if dup_phone.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate with phone number '{clean_phone}' already exists.",
            )

        # 3. Check optional batch existence
        if payload.batch_id:
            batch = (await self.db.execute(select(Batch).where(Batch.id == payload.batch_id))).scalar_one_or_none()
            if not batch:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified batch does not exist.")

        # 4. Check matching user account
        user = (await self.db.execute(select(User).where(User.email == clean_email))).scalar_one_or_none()

        candidate_number = await self._generate_candidate_number()
        candidate = Candidate(
            user_id=user.id if user else None,
            candidate_number=candidate_number,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            email=clean_email,
            phone=clean_phone,
            alternate_phone=payload.alternate_phone.strip() if payload.alternate_phone else None,
            academic_qualification=payload.academic_qualification.strip() if payload.academic_qualification else None,
            lifecycle_status="ACTIVE",
            project_eligible=False,
            completed_projects_count=0,
        )
        self.db.add(candidate)
        await self.db.flush()

        # 5. Enroll in batch if specified
        if payload.batch_id:
            enrollment = Enrollment(
                candidate_id=candidate.id,
                batch_id=payload.batch_id,
                enrollment_status="ACTIVE",
            )
            self.db.add(enrollment)

        # 6. Status history & audit log
        self.db.add(CandidateStatusHistory(
            candidate_id=candidate.id,
            from_status=None,
            to_status="ACTIVE",
            reason="Initial candidate enrollment",
            changed_by=actor_id,
        ))

        self.db.add(AuditLog(
            actor_user_id=actor_id,
            actor_ip_address=actor_ip,
            action_type="CANDIDATE_CREATED",
            entity_type="candidates",
            entity_id=candidate.id,
            justification=f"Created candidate {candidate_number} ({clean_email})",
        ))

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def get_candidate(self, candidate_id: uuid.UUID) -> Optional[Candidate]:
        """Fetches candidate by primary key."""
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_candidate_by_user_id(self, user_id: uuid.UUID) -> Optional[Candidate]:
        """Fetches candidate linked to a user account (for student portal)."""
        stmt = select(Candidate).where(Candidate.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_candidate(
        self,
        candidate_id: uuid.UUID,
        payload: CandidateUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_ip: Optional[str] = None,
    ) -> Candidate:
        """Updates candidate details with duplicate validation for phone."""
        candidate = await self.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

        if payload.phone and payload.phone != candidate.phone:
            clean_phone = payload.phone.strip()
            dup = await self.db.execute(
                select(Candidate).where(Candidate.phone == clean_phone, Candidate.id != candidate_id)
            )
            if dup.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Phone number '{clean_phone}' is already registered to another candidate.",
                )
            candidate.phone = clean_phone

        if payload.first_name is not None:
            candidate.first_name = payload.first_name.strip()
        if payload.last_name is not None:
            candidate.last_name = payload.last_name.strip()
        if payload.alternate_phone is not None:
            candidate.alternate_phone = payload.alternate_phone.strip()
        if payload.academic_qualification is not None:
            candidate.academic_qualification = payload.academic_qualification.strip()

        candidate.updated_at = utc_now()

        self.db.add(AuditLog(
            actor_user_id=actor_id,
            actor_ip_address=actor_ip,
            action_type="CANDIDATE_UPDATED",
            entity_type="candidates",
            entity_id=candidate.id,
            justification="Candidate profile updated",
        ))

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def transition_status(
        self,
        candidate_id: uuid.UUID,
        payload: CandidateStatusTransitionRequest,
        actor_id: Optional[uuid.UUID] = None,
        actor_ip: Optional[str] = None,
    ) -> Candidate:
        """Executes a validated lifecycle status transition with mandatory reason."""
        candidate = await self.get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

        target_status = payload.to_status.upper().strip()
        if target_status not in VALID_LIFECYCLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.to_status}'. Must be one of: {sorted(list(VALID_LIFECYCLE_STATUSES))}",
            )

        if candidate.lifecycle_status == target_status:
            return candidate

        old_status = candidate.lifecycle_status
        candidate.lifecycle_status = target_status
        candidate.updated_at = utc_now()

        # Add history record
        self.db.add(CandidateStatusHistory(
            candidate_id=candidate.id,
            from_status=old_status,
            to_status=target_status,
            reason=payload.reason.strip(),
            changed_by=actor_id,
        ))

        # Add audit log
        self.db.add(AuditLog(
            actor_user_id=actor_id,
            actor_ip_address=actor_ip,
            action_type="CANDIDATE_STATUS_CHANGED",
            entity_type="candidates",
            entity_id=candidate.id,
            pre_state={"status": old_status},
            post_state={"status": target_status},
            justification=payload.reason.strip(),
        ))

        await self.db.commit()
        await self.db.refresh(candidate)
        return candidate

    async def list_candidates(
        self,
        search: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        project_eligible: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Candidate], int]:
        """Paginated list of candidates with optional search and filters."""
        stmt = select(Candidate)
        count_stmt = select(func.count(Candidate.id))

        if search:
            s = f"%{search.strip().lower()}%"
            filter_cond = or_(
                func.lower(Candidate.first_name).like(s),
                func.lower(Candidate.last_name).like(s),
                func.lower(Candidate.email).like(s),
                Candidate.phone.like(s),
                func.lower(Candidate.candidate_number).like(s),
            )
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        if lifecycle_status:
            stmt = stmt.where(Candidate.lifecycle_status == lifecycle_status.upper().strip())
            count_stmt = count_stmt.where(Candidate.lifecycle_status == lifecycle_status.upper().strip())

        if project_eligible is not None:
            stmt = stmt.where(Candidate.project_eligible == project_eligible)
            count_stmt = count_stmt.where(Candidate.project_eligible == project_eligible)

        if batch_id:
            stmt = stmt.join(Enrollment, Enrollment.candidate_id == Candidate.id).where(
                Enrollment.batch_id == batch_id
            )
            count_stmt = count_stmt.join(Enrollment, Enrollment.candidate_id == Candidate.id).where(
                Enrollment.batch_id == batch_id
            )

        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Pagination & ordering
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(Candidate.created_at)).offset(offset).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())

        return items, total

    async def preview_csv_import(
        self,
        raw_rows: List[Dict[str, Any]],
    ) -> ImportPreviewResponse:
        """
        Validates raw parsed CSV rows without committing.
        Detects missing required fields, email/phone format errors, and existing duplicates.
        """
        preview_rows: List[ImportRowItem] = []
        seen_emails: set = set()
        seen_phones: set = set()

        for idx, row in enumerate(raw_rows, start=1):
            first_name = str(row.get("first_name", "")).strip()
            last_name = str(row.get("last_name", "")).strip()
            email = str(row.get("email", "")).lower().strip()
            phone = str(row.get("phone", "")).strip()
            batch_code = str(row.get("batch_code", "")).strip() or None
            academic = str(row.get("academic_qualification", "")).strip() or None

            item = ImportRowItem(
                row_number=idx,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                batch_code=batch_code,
                academic_qualification=academic,
                is_valid=True,
            )

            # 1. Required fields
            if not first_name:
                item.is_valid = False
                item.error_field = "first_name"
                item.error_message = "First name is required."
            elif not last_name:
                item.is_valid = False
                item.error_field = "last_name"
                item.error_message = "Last name is required."
            elif not email or not EMAIL_REGEX.match(email):
                item.is_valid = False
                item.error_field = "email"
                item.error_message = "Valid email address is required."
            elif not phone or len(phone) < 7:
                item.is_valid = False
                item.error_field = "phone"
                item.error_message = "Valid phone number (min 7 digits) is required."
            elif email in seen_emails:
                item.is_valid = False
                item.error_field = "email"
                item.error_message = "Duplicate email within import file."
            elif phone in seen_phones:
                item.is_valid = False
                item.error_field = "phone"
                item.error_message = "Duplicate phone number within import file."
            else:
                # 2. Check DB duplicates
                dup_email = (
                    await self.db.execute(select(Candidate).where(Candidate.email == email))
                ).scalar_one_or_none()
                if dup_email:
                    item.is_valid = False
                    item.error_field = "email"
                    item.error_message = f"Candidate with email '{email}' already exists in database."
                else:
                    dup_phone = (
                        await self.db.execute(select(Candidate).where(Candidate.phone == phone))
                    ).scalar_one_or_none()
                    if dup_phone:
                        item.is_valid = False
                        item.error_field = "phone"
                        item.error_message = f"Candidate with phone '{phone}' already exists in database."

            if item.is_valid:
                seen_emails.add(email)
                seen_phones.add(phone)

            preview_rows.append(item)

        valid_count = sum(1 for r in preview_rows if r.is_valid)
        error_count = len(preview_rows) - valid_count

        return ImportPreviewResponse(
            total_rows=len(preview_rows),
            valid_rows_count=valid_count,
            error_rows_count=error_count,
            rows=preview_rows,
        )

    async def commit_csv_import(
        self,
        payload: ImportCommitRequest,
        actor_id: Optional[uuid.UUID] = None,
        actor_ip: Optional[str] = None,
    ) -> ImportCommitResponse:
        """Commits only valid rows from preview into database within a single transaction."""
        inserted = 0
        skipped = 0

        # Batch cache by code
        batches_by_code: Dict[str, Batch] = {}
        all_batches = (await self.db.execute(select(Batch))).scalars().all()
        for b in all_batches:
            batches_by_code[b.batch_code.upper()] = b

        for row in payload.rows:
            if not row.is_valid:
                skipped += 1
                continue

            clean_email = row.email.lower().strip()
            clean_phone = row.phone.strip()

            # Final safety check against race conditions
            existing = (
                await self.db.execute(
                    select(Candidate).where(or_(Candidate.email == clean_email, Candidate.phone == clean_phone))
                )
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            candidate_number = await self._generate_candidate_number()
            candidate = Candidate(
                candidate_number=candidate_number,
                first_name=row.first_name.strip(),
                last_name=row.last_name.strip(),
                email=clean_email,
                phone=clean_phone,
                academic_qualification=row.academic_qualification,
                lifecycle_status="ACTIVE",
                project_eligible=False,
                completed_projects_count=0,
            )
            self.db.add(candidate)
            await self.db.flush()

            # Determine batch enrollment
            target_batch_id = payload.default_batch_id
            if row.batch_code and row.batch_code.upper() in batches_by_code:
                target_batch_id = batches_by_code[row.batch_code.upper()].id

            if target_batch_id:
                enrollment = Enrollment(
                    candidate_id=candidate.id,
                    batch_id=target_batch_id,
                    enrollment_status="ACTIVE",
                )
                self.db.add(enrollment)

            self.db.add(CandidateStatusHistory(
                candidate_id=candidate.id,
                from_status=None,
                to_status="ACTIVE",
                reason="Bulk CSV ingestion",
                changed_by=actor_id,
            ))
            inserted += 1

        self.db.add(AuditLog(
            actor_user_id=actor_id,
            actor_ip_address=actor_ip,
            action_type="CANDIDATE_BULK_IMPORTED",
            entity_type="candidates",
            entity_id=None,
            justification=f"Imported {inserted} candidates, skipped {skipped}",
        ))

        await self.db.commit()
        return ImportCommitResponse(
            inserted_count=inserted,
            skipped_count=skipped,
            message=f"Successfully imported {inserted} candidates ({skipped} skipped/invalid).",
        )
