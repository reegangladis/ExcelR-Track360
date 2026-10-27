"""
ExcelR Track360 - Certificate Management & Verification Engine Service
Domain 6: Credentials, Two-Stage Approvals, Cryptographic Verification & Revocations.
Strictly adheres to BR-CERT-01, BR-CERT-02, SEC-CERT-01, and Separation of Duties (SoD).
"""
import hmac
import hashlib
import io
import os
import secrets
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import utc_now
from app.modules.auth.models import User
from app.modules.candidates.models import Candidate, CourseTrack
from app.modules.assignments.models import Assignment, SubmissionAttempt, FileAsset
from app.modules.projects.models import (
    Project,
    ProjectGroup,
    ProjectGroupMember,
    ProjectGroupSubmission,
)
from app.modules.internships.models import InternshipRecord
from app.modules.certificates.models import (
    CertificateRecord,
    CertificateApproval,
    CertificateRevocation,
)
from app.modules.certificates.schemas import (
    CertificateIssueRequest,
    CertificateReviewRequest,
    CertificateApprovalRequest,
    CertificateRevokeRequest,
    CertificateEligibilityDiagnostic,
    CertificatePublicVerifyResponse,
)
from app.modules.certificates.generator import render_certificate_pdf_bytes
from app.modules.audit.service import write_audit_log


class CertificateService:
    """Authoritative business logic for certificate lifecycle, two-tier approvals, and cryptographic verification."""

    @staticmethod
    def compute_verification_hash(
        serial_number: str,
        candidate_id: uuid.UUID,
        track_id: uuid.UUID,
        accredited_duration_months: int,
        issue_date: date,
    ) -> str:
        """
        Computes HMAC-SHA256 signature for the certificate payload (SEC-CERT-01).
        Guarantees that tamper attempts on serial, candidate, track, or duration are detected.
        """
        settings = get_settings()
        secret_key = settings.SECRET_KEY.encode("utf-8")
        payload = (
            f"{serial_number.strip().upper()}:"
            f"{candidate_id}:"
            f"{track_id}:"
            f"{accredited_duration_months}:"
            f"{issue_date.isoformat()}"
        ).encode("utf-8")

        return hmac.new(secret_key, payload, hashlib.sha256).hexdigest()

    @staticmethod
    async def generate_unique_serial_number(db: AsyncSession, track_code: str) -> str:
        """
        Generates a non-sequential, cryptographically unique serial number:
        Format: EXCELR-{YEAR}-{TRACK_CODE}-{HEX8}
        Example: EXCELR-2026-FSD-4E8A1D3C
        """
        year = datetime.now(timezone.utc).year
        # Sanitize track code (uppercase alphanumeric, max 8 chars)
        clean_code = "".join(ch for ch in track_code.upper() if ch.isalnum())[:8] or "TRK"

        for _ in range(20):  # Retry loop to guarantee uniqueness
            hex_token = secrets.token_hex(4).upper()
            serial = f"EXCELR-{year}-{clean_code}-{hex_token}"
            res = await db.execute(
                select(CertificateRecord.id).where(CertificateRecord.serial_number == serial)
            )
            if not res.scalar_one_or_none():
                return serial

        # Fallback with uuid if collision loop exhausts
        return f"EXCELR-{year}-{clean_code}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    async def calculate_candidate_eligibility(
        cls,
        db: AsyncSession,
        candidate_id: uuid.UUID,
        track_id: Optional[uuid.UUID] = None,
    ) -> CertificateEligibilityDiagnostic:
        """
        Evaluates candidate eligibility across all prerequisite domains (BR-CERT-01):
        1. 100% prerequisite/mandatory assignments passed.
        2. Verified project tier achievement or accredited internship completion.
        3. No active, non-revoked duplicate certificate.
        """
        # 1. Fetch Candidate
        c_res = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = c_res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )

        target_track_id = track_id
        if not target_track_id:
            from app.modules.candidates.models import Enrollment, Batch
            enroll_res = await db.execute(
                select(Batch.track_id)
                .join(Enrollment, Enrollment.batch_id == Batch.id)
                .where(Enrollment.candidate_id == candidate.id)
            )
            target_track_id = enroll_res.scalars().first()

        if not target_track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate is not enrolled in an academic course track.",
            )

        # 2. Fetch Course Track
        t_res = await db.execute(
            select(CourseTrack).where(CourseTrack.id == target_track_id)
        )
        track = t_res.scalar_one_or_none()
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course track with ID '{target_track_id}' not found.",
            )

        # 3. Check Mandatory Assignments
        # Query total mandatory assignments for track
        total_mandatory_query = select(func.count(Assignment.id)).where(
            Assignment.track_id == track.id,
            Assignment.is_mandatory == True,
            Assignment.is_active == True,
        )
        total_mandatory_res = await db.execute(total_mandatory_query)
        total_mandatory = total_mandatory_res.scalar() or 0
        if total_mandatory == 0 and track.total_mandatory_assignments > 0:
            total_mandatory = track.total_mandatory_assignments

        # Query passed mandatory assignments by candidate
        from app.modules.assignments.models import AssignmentAllocation, AssignmentSubmission
        passed_asg_query = (
            select(func.count(func.distinct(Assignment.id)))
            .join(AssignmentAllocation, AssignmentAllocation.assignment_id == Assignment.id)
            .join(AssignmentSubmission, AssignmentSubmission.allocation_id == AssignmentAllocation.id)
            .where(
                Assignment.track_id == track.id,
                Assignment.is_mandatory == True,
                AssignmentSubmission.candidate_id == candidate.id,
                or_(
                    AssignmentSubmission.current_completion_status == "PASSED_COMPLETED",
                    AssignmentSubmission.current_submission_status == "APPROVED",
                ),
            )
        )
        passed_asg_res = await db.execute(passed_asg_query)
        passed_mandatory = passed_asg_res.scalar() or 0
        assignments_completed = (passed_mandatory >= total_mandatory) if total_mandatory > 0 else True

        # 4. Check Approved Project Milestones
        groups_query = (
            select(ProjectGroup)
            .join(ProjectGroupMember, ProjectGroupMember.group_id == ProjectGroup.id)
            .where(
                ProjectGroupMember.candidate_id == candidate.id,
                ProjectGroupMember.status == "ACTIVE",
            )
        )
        groups_res = await db.execute(groups_query)
        groups = groups_res.scalars().all()

        approved_projects_count = 0
        for group in groups:
            sub_res = await db.execute(
                select(ProjectGroupSubmission).where(
                    ProjectGroupSubmission.group_id == group.id,
                    ProjectGroupSubmission.status == "APPROVED",
                )
            )
            if sub_res.scalars().first() or group.group_status in ["READY_FOR_NEXT_PROJECT", "COMPLETED"]:
                approved_projects_count += 1

        total_required_projects = track.total_required_projects or 1
        projects_completed = approved_projects_count >= 1

        # 5. Check Internship Record
        int_query = select(InternshipRecord).where(
            InternshipRecord.candidate_id == candidate.id,
            InternshipRecord.track_id == track.id,
        )
        int_res = await db.execute(int_query)
        internship = int_res.scalars().first()

        has_internship = internship is not None
        internship_status_val = internship.internship_status if internship else None
        internship_completed = internship is not None and internship.internship_status == "COMPLETED"

        # Accredited duration (from internship record or policy config based on projects)
        duration_policy = track.duration_policy_config or {"1": 3, "2": 6, "3": 9}
        if internship and internship.accredited_duration_months:
            accredited_duration = internship.accredited_duration_months
        elif approved_projects_count >= 3:
            accredited_duration = duration_policy.get("3", 9)
        elif approved_projects_count >= 2:
            accredited_duration = duration_policy.get("2", 6)
        elif approved_projects_count >= 1:
            accredited_duration = duration_policy.get("1", 3)
        else:
            accredited_duration = 3

        # 6. Check Duplicate Active Certificate
        active_cert_query = select(CertificateRecord).where(
            CertificateRecord.candidate_id == candidate.id,
            CertificateRecord.track_id == track.id,
            CertificateRecord.status.in_(["PENDING_APPROVAL", "REVIEWED", "APPROVED", "ISSUED"]),
        )
        active_cert_res = await db.execute(active_cert_query)
        existing_cert = active_cert_res.scalars().first()

        has_active_certificate = existing_cert is not None
        existing_cert_id = existing_cert.id if existing_cert else None
        existing_cert_number = existing_cert.serial_number if existing_cert else None

        # 7. Collect Ineligibility Reasons
        ineligibility_reasons: List[str] = []
        if not assignments_completed:
            ineligibility_reasons.append(
                f"Candidate has passed {passed_mandatory}/{total_mandatory} mandatory assignments. 100% completion required."
            )
        if not (projects_completed or internship_completed):
            ineligibility_reasons.append(
                "Candidate has not achieved any approved project deliverables or completed formal internship."
            )
        if has_active_certificate:
            ineligibility_reasons.append(
                f"Candidate already has an active certificate ({existing_cert_number}) in status '{existing_cert.status}'."
            )

        is_eligible = (
            assignments_completed
            and (projects_completed or internship_completed)
            and not has_active_certificate
        )

        return CertificateEligibilityDiagnostic(
            candidate_id=candidate.id,
            candidate_name=f"{candidate.first_name} {candidate.last_name}".strip(),
            track_id=track.id,
            track_title=track.title,
            total_mandatory_assignments=total_mandatory,
            passed_mandatory_assignments=passed_mandatory,
            assignments_completed=assignments_completed,
            total_required_projects=total_required_projects,
            approved_project_milestones=approved_projects_count,
            projects_completed=projects_completed,
            has_internship=has_internship,
            internship_status=internship_status_val,
            internship_completed=internship_completed,
            accredited_duration_months=accredited_duration,
            is_eligible=is_eligible,
            ineligibility_reasons=ineligibility_reasons,
            has_active_certificate=has_active_certificate,
            existing_certificate_id=existing_cert_id,
            existing_certificate_number=existing_cert_number,
        )

    @classmethod
    async def initiate_certificate_request(
        cls,
        db: AsyncSession,
        payload: CertificateIssueRequest,
        actor_user: User,
        is_admin_override: bool = False,
    ) -> CertificateRecord:
        """
        Stage 0: Initiates a new certificate issuance request.
        Validates candidate prerequisite eligibility and provisions a cryptographically signed draft.
        """
        # Diagnostic Check
        diag = await cls.calculate_candidate_eligibility(db, payload.candidate_id, payload.track_id)
        if not is_admin_override and not diag.is_eligible:
            reasons_str = "; ".join(diag.ineligibility_reasons)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Candidate is not eligible for certificate issuance: {reasons_str}",
            )

        if diag.has_active_certificate and not is_admin_override:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active certificate already exists ({diag.existing_certificate_number}) for this candidate.",
            )

        # Fetch Candidate and Track
        c_res = await db.execute(select(Candidate).where(Candidate.id == payload.candidate_id))
        candidate = c_res.scalar_one()

        t_res = await db.execute(select(CourseTrack).where(CourseTrack.id == payload.track_id))
        track = t_res.scalar_one()

        candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
        issue_date_val = payload.issue_date or date.today()
        accredited_duration = diag.accredited_duration_months

        # Generate unique serial number & cryptographic hash
        serial_number = await cls.generate_unique_serial_number(db, track.code)
        verification_hash = cls.compute_verification_hash(
            serial_number=serial_number,
            candidate_id=candidate.id,
            track_id=track.id,
            accredited_duration_months=accredited_duration,
            issue_date=issue_date_val,
        )
        verification_url = f"/verify/{serial_number}"

        record = CertificateRecord(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            track_id=track.id,
            internship_record_id=payload.internship_record_id,
            serial_number=serial_number,
            certificate_type=payload.certificate_type,
            milestone_level=payload.milestone_level,
            accredited_duration_months=accredited_duration,
            issue_date=issue_date_val,
            candidate_display_name=candidate_name,
            course_display_title=track.title,
            verification_hash=verification_hash,
            verification_qr_url=verification_url,
            status="PENDING_APPROVAL",
            requested_by_id=actor_user.id,
            requested_at=utc_now(),
        )
        db.add(record)

        # Audit log
        await write_audit_log(
            db=db,
            action="certificate:requested",
            actor_id=actor_user.id,
            resource_type="certificate",
            resource_id=str(record.id),
            details={
                "serial_number": serial_number,
                "candidate_id": str(candidate.id),
                "candidate_name": candidate_name,
                "track_id": str(track.id),
                "track_title": track.title,
                "accredited_duration_months": accredited_duration,
                "status": "PENDING_APPROVAL",
            },
        )

        record_id = record.id
        await db.commit()
        return await cls.get_certificate(db, record_id)

    @classmethod
    async def review_certificate_stage1(
        cls,
        db: AsyncSession,
        certificate_id: uuid.UUID,
        payload: CertificateReviewRequest,
        actor_user: User,
    ) -> CertificateRecord:
        """
        Stage 1: Coordinator Review.
        Verifies student progress and passes certificate to Stage 2 Approval Queue or marks REJECTED.
        """
        cert = await cls.get_certificate(db, certificate_id)
        if cert.status != "PENDING_APPROVAL":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Certificate cannot undergo Stage 1 review in '{cert.status}' status (must be 'PENDING_APPROVAL').",
            )

        now = utc_now()
        cert.stage1_reviewer_id = actor_user.id
        cert.stage1_reviewed_at = now
        cert.stage1_notes = payload.decision_notes

        new_status = "REVIEWED" if payload.decision == "APPROVED" else "REJECTED"
        cert.status = new_status

        # Create immutable approval record
        approval = CertificateApproval(
            id=uuid.uuid4(),
            certificate_id=cert.id,
            approver_id=actor_user.id,
            stage="STAGE_1_REVIEW",
            decision=payload.decision,
            decision_notes=payload.decision_notes,
            decided_at_utc=now,
        )
        approval.approver = actor_user
        cert.approvals.append(approval)
        db.add(approval)

        await write_audit_log(
            db=db,
            action=f"certificate:stage1_{payload.decision.lower()}",
            actor_id=actor_user.id,
            resource_type="certificate",
            resource_id=str(cert.id),
            details={
                "serial_number": cert.serial_number,
                "decision": payload.decision,
                "notes": payload.decision_notes,
                "new_status": new_status,
            },
        )

        cert_id = cert.id
        await db.commit()
        return await cls.get_certificate(db, cert_id)

    @classmethod
    async def approve_certificate_stage2(
        cls,
        db: AsyncSession,
        certificate_id: uuid.UUID,
        payload: CertificateApprovalRequest,
        actor_user: User,
        user_roles: List[str],
        allow_override: bool = False,
    ) -> CertificateRecord:
        """
        Stage 2: Director / Approver Final Sign-off.
        Strictly enforces Separation of Duties (SoD):
        The same user who requested or reviewed Stage 1 CANNOT grant Stage 2 sign-off.
        On approval, triggers automated high-resolution PDF & dynamic QR generation.
        """
        cert = await cls.get_certificate(db, certificate_id)
        if cert.status not in ["REVIEWED", "PENDING_APPROVAL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Certificate cannot be signed in '{cert.status}' status.",
            )

        # Separation of Duties (SoD) Enforcement:
        # A Coordinator who initiated or reviewed the request cannot sign off as approver.
        is_same_requester = cert.requested_by_id == actor_user.id
        is_same_reviewer = cert.stage1_reviewer_id == actor_user.id
        if (is_same_requester or is_same_reviewer) and not (allow_override and "ROLE_SUPER_ADMIN" in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of Duties violation: Initiator or Stage 1 Reviewer cannot sign off on Stage 2 Approval.",
            )

        now = utc_now()
        cert.stage2_approver_id = actor_user.id
        cert.stage2_approved_at = now
        cert.stage2_notes = payload.decision_notes

        if payload.decision == "APPROVED":
            cert.status = "ISSUED"
            cert.issued_at_utc = now

            # Automated High-Res PDF & Dynamic QR Generation
            pdf_bytes = render_certificate_pdf_bytes(
                serial_number=cert.serial_number,
                candidate_name=cert.candidate_display_name,
                track_title=cert.course_display_title,
                accredited_duration_months=cert.accredited_duration_months,
                issue_date=cert.issue_date,
                verification_hash=cert.verification_hash,
                verification_url=cert.verification_qr_url,
            )

            # Save File Asset
            settings = get_settings()
            cert_dir = Path(settings.UPLOAD_DIR) / "certificates"
            cert_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{cert.serial_number}.pdf"
            file_path = cert_dir / filename

            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

            file_asset = FileAsset(
                id=uuid.uuid4(),
                storage_backend="local",
                storage_key=f"certificates/{filename}",
                original_filename=filename,
                file_extension="pdf",
                file_size_bytes=len(pdf_bytes),
                mime_type="application/pdf",
                checksum_sha256=hashlib.sha256(pdf_bytes).hexdigest(),
                uploaded_by=actor_user.id,
                created_at=now,
            )
            db.add(file_asset)
            cert.pdf_file_asset_id = file_asset.id

        else:
            cert.status = "REJECTED"

        # Create immutable approval record
        approval = CertificateApproval(
            id=uuid.uuid4(),
            certificate_id=cert.id,
            approver_id=actor_user.id,
            stage="STAGE_2_APPROVAL",
            decision=payload.decision,
            decision_notes=payload.decision_notes,
            decided_at_utc=now,
        )
        approval.approver = actor_user
        cert.approvals.append(approval)
        db.add(approval)

        await write_audit_log(
            db=db,
            action=f"certificate:stage2_{payload.decision.lower()}",
            actor_id=actor_user.id,
            resource_type="certificate",
            resource_id=str(cert.id),
            details={
                "serial_number": cert.serial_number,
                "decision": payload.decision,
                "notes": payload.decision_notes,
                "final_status": cert.status,
            },
        )

        cert_id = cert.id
        await db.commit()
        return await cls.get_certificate(db, cert_id)

    @classmethod
    async def revoke_certificate(
        cls,
        db: AsyncSession,
        certificate_id: uuid.UUID,
        payload: CertificateRevokeRequest,
        actor_user: User,
    ) -> CertificateRecord:
        """
        Formally revokes an issued certificate credential.
        Immediately reflects as REVOKED on the public verification portal.
        """
        cert = await cls.get_certificate(db, certificate_id)
        if cert.status != "ISSUED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revoke a certificate with status '{cert.status}'. Only 'ISSUED' certificates can be revoked.",
            )

        now = utc_now()
        cert.status = "REVOKED"
        cert.revoked_by_id = actor_user.id
        cert.revoked_at = now
        cert.revocation_category = payload.reason_category
        cert.revocation_reason = payload.detailed_reason

        # Create immutable revocation record
        revocation = CertificateRevocation(
            id=uuid.uuid4(),
            certificate_id=cert.id,
            revoked_by_id=actor_user.id,
            reason_category=payload.reason_category,
            detailed_reason=payload.detailed_reason,
            revoked_at_utc=now,
        )
        revocation.revoker = actor_user
        cert.revocations.append(revocation)
        db.add(revocation)

        await write_audit_log(
            db=db,
            action="certificate:revoked",
            actor_id=actor_user.id,
            resource_type="certificate",
            resource_id=str(cert.id),
            details={
                "serial_number": cert.serial_number,
                "candidate_name": cert.candidate_display_name,
                "reason_category": payload.reason_category,
                "detailed_reason": payload.detailed_reason,
            },
        )

        cert_id = cert.id
        await db.commit()
        return await cls.get_certificate(db, cert_id)

    @classmethod
    async def verify_certificate_public(
        cls,
        db: AsyncSession,
        identifier: str,
    ) -> CertificatePublicVerifyResponse:
        """
        Public verification portal engine (FR-CER-005).
        Requires zero authentication.
        Checks existence, validates cryptographic integrity hash, and returns authentic status.
        """
        clean_id = identifier.strip()
        query = select(CertificateRecord).where(
            or_(
                func.upper(CertificateRecord.serial_number) == clean_id.upper(),
                func.lower(CertificateRecord.verification_hash) == clean_id.lower(),
            )
        )
        res = await db.execute(query)
        cert = res.scalars().first()

        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificate credential not found in ExcelR National Registry.",
            )

        # Cryptographic Signature Verification
        expected_hash = cls.compute_verification_hash(
            serial_number=cert.serial_number,
            candidate_id=cert.candidate_id,
            track_id=cert.track_id,
            accredited_duration_months=cert.accredited_duration_months,
            issue_date=cert.issue_date,
        )

        is_hash_valid = hmac.compare_digest(expected_hash, cert.verification_hash)
        if not is_hash_valid:
            # Tampering detected!
            return CertificatePublicVerifyResponse(
                is_valid=False,
                status="TAMPERED",
                serial_number=cert.serial_number,
                candidate_name=cert.candidate_display_name,
                track_title=cert.course_display_title,
                accredited_duration_months=cert.accredited_duration_months,
                issue_date=cert.issue_date,
                verification_hash=cert.verification_hash,
                issued_at_utc=cert.issued_at_utc,
                revoked_at=cert.revoked_at,
                revocation_category="SECURITY_INTEGRITY_TAMPER_DETECTED",
                verification_qr_url=cert.verification_qr_url,
            )

        is_valid = cert.status == "ISSUED"
        return CertificatePublicVerifyResponse(
            is_valid=is_valid,
            status=cert.status,
            serial_number=cert.serial_number,
            candidate_name=cert.candidate_display_name,
            track_title=cert.course_display_title,
            accredited_duration_months=cert.accredited_duration_months,
            issue_date=cert.issue_date,
            verification_hash=cert.verification_hash,
            issued_at_utc=cert.issued_at_utc,
            revoked_at=cert.revoked_at,
            revocation_category=cert.revocation_category,
            verification_qr_url=cert.verification_qr_url,
        )

    @classmethod
    async def get_certificate(
        cls,
        db: AsyncSession,
        certificate_id: uuid.UUID,
    ) -> CertificateRecord:
        """Fetches certificate record with selectin-loaded approvals and revocations."""
        query = (
            select(CertificateRecord)
            .options(
                selectinload(CertificateRecord.approvals),
                selectinload(CertificateRecord.revocations),
            )
            .where(CertificateRecord.id == certificate_id)
        )
        res = await db.execute(query)
        cert = res.scalar_one_or_none()
        if not cert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certificate with ID '{certificate_id}' not found.",
            )
        return cert

    @classmethod
    async def list_certificates(
        cls,
        db: AsyncSession,
        candidate_id: Optional[uuid.UUID] = None,
        track_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[CertificateRecord], int]:
        """Queries certificate records with filtering, searching, and pagination."""
        query = select(CertificateRecord).options(
            selectinload(CertificateRecord.approvals),
            selectinload(CertificateRecord.revocations),
        )

        conditions = []
        if candidate_id:
            conditions.append(CertificateRecord.candidate_id == candidate_id)
        if track_id:
            conditions.append(CertificateRecord.track_id == track_id)
        if status_filter:
            conditions.append(CertificateRecord.status == status_filter)
        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    CertificateRecord.serial_number.ilike(search_pattern),
                    CertificateRecord.candidate_display_name.ilike(search_pattern),
                    CertificateRecord.course_display_title.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        # Total count
        count_q = select(func.count(CertificateRecord.id))
        if conditions:
            count_q = count_q.where(and_(*conditions))
        total_res = await db.execute(count_q)
        total = total_res.scalar() or 0

        # Pagination & sorting (newest first)
        offset = (page - 1) * page_size
        query = query.order_by(CertificateRecord.created_at.desc()).offset(offset).limit(page_size)

        res = await db.execute(query)
        return list(res.scalars().all()), total

    @classmethod
    async def get_certificate_pdf_bytes(
        cls,
        db: AsyncSession,
        certificate_id: uuid.UUID,
    ) -> Tuple[bytes, str]:
        """
        Retrieves the raw PDF bytes and filename for certificate download.
        Re-renders dynamically if file asset is missing on disk.
        """
        cert = await cls.get_certificate(db, certificate_id)
        if cert.status != "ISSUED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot download certificate in '{cert.status}' status (must be 'ISSUED').",
            )

        settings = get_settings()
        filename = f"{cert.serial_number}.pdf"
        file_path = Path(settings.UPLOAD_DIR) / "certificates" / filename

        if file_path.exists():
            with open(file_path, "rb") as f:
                return f.read(), filename

        # Regenerate on demand
        pdf_bytes = render_certificate_pdf_bytes(
            serial_number=cert.serial_number,
            candidate_name=cert.candidate_display_name,
            track_title=cert.course_display_title,
            accredited_duration_months=cert.accredited_duration_months,
            issue_date=cert.issue_date,
            verification_hash=cert.verification_hash,
            verification_url=cert.verification_qr_url,
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        return pdf_bytes, filename
