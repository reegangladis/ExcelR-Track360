from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
from typing import Optional, Tuple, List
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import utc_now
from app.modules.audit.service import write_audit_log
from app.modules.candidates.models import CourseTrack, Batch, Candidate, Enrollment
from app.modules.assignments.models import (
    Assignment,
    AssignmentAllocation,
    AssignmentSubmission,
    FileAsset,
    SubmissionAttempt,
    SubmissionReview,
    ReviewRubricScore,
)
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AllocationCreateRequest,
    SubmissionReviewCreateRequest,
    BulkAssignmentStatusUpdateRequest,
    BulkAssignmentStatusUpdateResponse,
    BulkAssignmentStatusItemResult,
)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AssignmentService:
    @staticmethod
    async def create_assignment(
        db: AsyncSession,
        payload: AssignmentCreateRequest,
        actor_id: Optional[uuid.UUID] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Assignment:
        # 1. Validate CourseTrack exists
        track_query = select(CourseTrack).where(CourseTrack.id == payload.track_id)
        track_res = await db.execute(track_query)
        track = track_res.scalar_one_or_none()
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course track '{payload.track_id}' not found.",
            )

        # 2. Check code uniqueness
        code_query = select(Assignment).where(Assignment.code == payload.code)
        code_res = await db.execute(code_query)
        if code_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Assignment with code '{payload.code}' already exists.",
            )

        # 3. Create Assignment
        assignment = Assignment(
            id=uuid.uuid4(),
            track_id=payload.track_id,
            code=payload.code,
            title=payload.title.strip(),
            instructions_markdown=payload.instructions_markdown.strip(),
            sequence_order=payload.sequence_order,
            is_mandatory=payload.is_mandatory,
            max_score=payload.max_score,
            passing_score=payload.passing_score,
            rubric_template=payload.rubric_template,
            allowed_file_types=payload.allowed_file_types,
            max_file_size_mb=payload.max_file_size_mb,
            is_active=True,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(assignment)
        await db.flush()

        # 4. Audit Log
        await write_audit_log(
            db=db,
            action="assignment:created",
            actor_id=actor_id,
            resource_type="assignment",
            resource_id=str(assignment.id),
            details={
                "code": assignment.code,
                "title": assignment.title,
                "track_id": str(assignment.track_id),
                "is_mandatory": assignment.is_mandatory,
                "max_score": float(assignment.max_score),
                "passing_score": float(assignment.passing_score),
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await AssignmentService.get_assignment(db, assignment.id)

    @staticmethod
    async def get_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> Assignment:
        query = (
            select(Assignment)
            .options(selectinload(Assignment.track))
            .where(Assignment.id == assignment_id)
        )
        res = await db.execute(query)
        assignment = res.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found.",
            )
        return assignment

    @staticmethod
    async def update_assignment(
        db: AsyncSession,
        assignment_id: uuid.UUID,
        payload: AssignmentUpdateRequest,
        actor_id: Optional[uuid.UUID] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Assignment:
        assignment = await AssignmentService.get_assignment(db, assignment_id)

        update_dict = payload.model_dump(exclude_unset=True)
        if not update_dict:
            return assignment

        new_max = update_dict.get("max_score", float(assignment.max_score))
        new_pass = update_dict.get("passing_score", float(assignment.passing_score))
        if new_pass > new_max:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="passing_score cannot exceed max_score.",
            )

        for key, val in update_dict.items():
            setattr(assignment, key, val)

        assignment.updated_at = utc_now()
        await db.flush()

        await write_audit_log(
            db=db,
            action="assignment:updated",
            actor_id=actor_id,
            resource_type="assignment",
            resource_id=str(assignment.id),
            details=update_dict,
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await AssignmentService.get_assignment(db, assignment.id)

    @staticmethod
    async def list_assignments(
        db: AsyncSession,
        track_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Assignment], int, int]:
        filters = []
        if track_id:
            filters.append(Assignment.track_id == track_id)
        if is_active is not None:
            filters.append(Assignment.is_active == is_active)
        if search and search.strip():
            s = f"%{search.strip()}%"
            filters.append(or_(Assignment.code.ilike(s), Assignment.title.ilike(s)))

        count_query = select(func.count(Assignment.id)).where(*filters)
        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (page - 1) * page_size

        query = (
            select(Assignment)
            .options(selectinload(Assignment.track))
            .where(*filters)
            .order_by(Assignment.sequence_order.asc(), Assignment.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(query)
        assignments = list(res.scalars().all())
        return assignments, total, total_pages

    @staticmethod
    async def create_allocation(
        db: AsyncSession,
        payload: AllocationCreateRequest,
        actor_id: Optional[uuid.UUID] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AssignmentAllocation:
        if not payload.batch_id and not payload.candidate_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must allocate to either a batch_id or candidate_id.",
            )

        # 1. Fetch Assignment
        assignment_query = select(Assignment).where(Assignment.id == payload.assignment_id)
        assignment_res = await db.execute(assignment_query)
        assignment = assignment_res.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment template not found.",
            )
        if not assignment.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot allocate an inactive assignment template.",
            )

        # 2. Check batch existence & duplicate allocation
        if payload.batch_id:
            b_query = select(Batch).where(Batch.id == payload.batch_id)
            b_res = await db.execute(b_query)
            batch = b_res.scalar_one_or_none()
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Batch '{payload.batch_id}' not found.",
                )
            # Check duplicate batch allocation
            dup_b_q = select(AssignmentAllocation).where(
                AssignmentAllocation.batch_id == payload.batch_id,
                AssignmentAllocation.assignment_id == payload.assignment_id,
            )
            dup_b_res = await db.execute(dup_b_q)
            if dup_b_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Assignment '{assignment.code}' is already allocated to batch '{batch.batch_code}'.",
                )

        # 3. Check candidate existence & duplicate allocation
        if payload.candidate_id:
            c_query = select(Candidate).where(Candidate.id == payload.candidate_id)
            c_res = await db.execute(c_query)
            candidate = c_res.scalar_one_or_none()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate '{payload.candidate_id}' not found.",
                )
            dup_c_q = select(AssignmentAllocation).where(
                AssignmentAllocation.candidate_id == payload.candidate_id,
                AssignmentAllocation.assignment_id == payload.assignment_id,
            )
            dup_c_res = await db.execute(dup_c_q)
            if dup_c_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Assignment '{assignment.code}' is already allocated to candidate '{candidate.candidate_number}'.",
                )

        # 4. Create Allocation
        allocation = AssignmentAllocation(
            id=uuid.uuid4(),
            assignment_id=payload.assignment_id,
            batch_id=payload.batch_id,
            candidate_id=payload.candidate_id,
            due_date_utc=_ensure_utc(payload.due_date_utc),
            grace_period_end_utc=_ensure_utc(payload.grace_period_end_utc),
            allocation_status="PENDING",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(allocation)
        await db.flush()

        # 5. Audit Log
        await write_audit_log(
            db=db,
            action="assignment_allocation:created",
            actor_id=actor_id,
            resource_type="assignment_allocation",
            resource_id=str(allocation.id),
            details={
                "assignment_code": assignment.code,
                "batch_id": str(payload.batch_id) if payload.batch_id else None,
                "candidate_id": str(payload.candidate_id) if payload.candidate_id else None,
                "due_date_utc": allocation.due_date_utc.isoformat(),
                "grace_period_end_utc": allocation.grace_period_end_utc.isoformat() if allocation.grace_period_end_utc else None,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        # Re-fetch with eager loaded relationships
        alloc_query = (
            select(AssignmentAllocation)
            .options(
                selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentAllocation.batch),
                selectinload(AssignmentAllocation.candidate),
            )
            .where(AssignmentAllocation.id == allocation.id)
        )
        alloc_res = await db.execute(alloc_query)
        return alloc_res.scalar_one()

    @staticmethod
    async def list_allocations(
        db: AsyncSession,
        assignment_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        candidate_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AssignmentAllocation], int, int]:
        filters = []
        if assignment_id:
            filters.append(AssignmentAllocation.assignment_id == assignment_id)
        if batch_id:
            filters.append(AssignmentAllocation.batch_id == batch_id)
        if candidate_id:
            filters.append(AssignmentAllocation.candidate_id == candidate_id)
        if status:
            filters.append(AssignmentAllocation.allocation_status == status)

        count_query = select(func.count(AssignmentAllocation.id)).where(*filters)
        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (page - 1) * page_size

        query = (
            select(AssignmentAllocation)
            .options(
                selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentAllocation.batch),
                selectinload(AssignmentAllocation.candidate),
            )
            .where(*filters)
            .order_by(AssignmentAllocation.due_date_utc.asc(), AssignmentAllocation.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        res = await db.execute(query)
        allocations = list(res.scalars().all())
        return allocations, total, total_pages

    @staticmethod
    async def submit_assignment(
        db: AsyncSession,
        allocation_id: uuid.UUID,
        candidate_id: uuid.UUID,
        file: Optional[UploadFile] = None,
        repository_url: Optional[str] = None,
        student_notes: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SubmissionAttempt:
        now = utc_now()

        # 1. Fetch Allocation with Assignment
        alloc_query = (
            select(AssignmentAllocation)
            .options(
                selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentAllocation.batch),
            )
            .where(AssignmentAllocation.id == allocation_id)
        )
        alloc_res = await db.execute(alloc_query)
        allocation = alloc_res.scalar_one_or_none()
        if not allocation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment allocation not found.",
            )

        # 2. Authorization & Enrollment verification
        if allocation.candidate_id and allocation.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: This allocation is designated for another candidate.",
            )

        if allocation.batch_id:
            enroll_q = select(Enrollment).where(
                Enrollment.batch_id == allocation.batch_id,
                Enrollment.candidate_id == candidate_id,
                Enrollment.enrollment_status.in_(["ACTIVE", "ENROLLED"]),
            )
            enroll_res = await db.execute(enroll_q)
            if not enroll_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Candidate is not actively enrolled in the allocated cohort batch.",
                )

        # 3. Grace period check
        if allocation.grace_period_end_utc and now > allocation.grace_period_end_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submission rejected: Grace period has expired. Please contact your coordinator for an extension.",
            )

        # 4. Lateness calculation
        is_late = now > allocation.due_date_utc
        lateness_minutes = max(0, int((now - allocation.due_date_utc).total_seconds() / 60)) if is_late else 0

        # 5. File handling & Validation
        file_asset: Optional[FileAsset] = None
        if file:
            filename = file.filename or "submission_file"
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            allowed = allocation.assignment.allowed_file_types or ["pdf", "zip", "ipynb"]
            if ext not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File extension '.{ext}' is not permitted. Allowed extensions: {', '.join(allowed)}.",
                )

            content = await file.read()
            size_bytes = len(content)
            max_bytes = allocation.assignment.max_file_size_mb * 1024 * 1024
            if size_bytes > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size ({size_bytes / (1024*1024):.2f}MB) exceeds limit of {allocation.assignment.max_file_size_mb}MB.",
                )

            checksum = hashlib.sha256(content).hexdigest()
            settings = get_settings()
            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            storage_key = f"{allocation.id}/{uuid.uuid4().hex[:12]}_{filename}"
            file_path = upload_dir / storage_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

            file_asset = FileAsset(
                id=uuid.uuid4(),
                storage_backend="local",
                storage_key=storage_key,
                original_filename=filename,
                file_extension=ext,
                file_size_bytes=size_bytes,
                mime_type=file.content_type or "application/octet-stream",
                checksum_sha256=checksum,
                uploaded_by=actor_id or candidate_id,
                created_at=now,
            )
            db.add(file_asset)
            await db.flush()
        elif not repository_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Must provide either a deliverable file or a repository URL.",
            )

        # 6. Find or Create AssignmentSubmission
        sub_query = select(AssignmentSubmission).where(
            AssignmentSubmission.allocation_id == allocation_id,
            AssignmentSubmission.candidate_id == candidate_id,
        )
        sub_res = await db.execute(sub_query)
        submission = sub_res.scalar_one_or_none()

        new_status = "LATE_SUBMITTED" if is_late else "SUBMITTED"

        if not submission:
            submission = AssignmentSubmission(
                id=uuid.uuid4(),
                allocation_id=allocation_id,
                candidate_id=candidate_id,
                current_submission_status=new_status,
                current_completion_status="INCOMPLETE",
                total_attempts=1,
                first_submitted_at_utc=now,
                latest_submitted_at_utc=now,
                created_at=now,
                updated_at=now,
            )
            db.add(submission)
            await db.flush()
            attempt_number = 1
        else:
            if submission.current_completion_status == "PASSED_COMPLETED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignment has already been approved and passed. Resubmission is not permitted.",
                )
            submission.total_attempts += 1
            submission.current_submission_status = new_status
            submission.latest_submitted_at_utc = now
            submission.updated_at = now
            attempt_number = submission.total_attempts

        # 7. Create SubmissionAttempt record
        attempt = SubmissionAttempt(
            id=uuid.uuid4(),
            submission_id=submission.id,
            attempt_number=attempt_number,
            file_asset_id=file_asset.id if file_asset else None,
            repository_url=repository_url,
            student_notes=student_notes,
            submitted_at_utc=now,
            is_late=is_late,
            lateness_minutes=lateness_minutes,
            created_at=now,
        )
        db.add(attempt)
        await db.flush()

        # 8. Audit Log
        await write_audit_log(
            db=db,
            action="assignment_submission:created",
            actor_id=actor_id or candidate_id,
            resource_type="assignment_submission",
            resource_id=str(submission.id),
            details={
                "attempt_number": attempt_number,
                "is_late": is_late,
                "lateness_minutes": lateness_minutes,
                "file_asset_id": str(file_asset.id) if file_asset else None,
                "repository_url": repository_url,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        # Re-fetch attempt with file asset eager loaded
        att_query = (
            select(SubmissionAttempt)
            .options(selectinload(SubmissionAttempt.file_asset))
            .where(SubmissionAttempt.id == attempt.id)
        )
        att_res = await db.execute(att_query)
        return att_res.scalar_one()

    @staticmethod
    async def review_submission(
        db: AsyncSession,
        submission_id: uuid.UUID,
        payload: SubmissionReviewCreateRequest,
        reviewer_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SubmissionReview:
        now = utc_now()

        # 1. Fetch submission with attempts, allocation, assignment, and candidate
        sub_query = (
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.attempts),
                selectinload(AssignmentSubmission.allocation).selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentSubmission.candidate),
            )
            .where(AssignmentSubmission.id == submission_id)
        )
        sub_res = await db.execute(sub_query)
        submission = sub_res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment submission record not found.",
            )

        if not submission.attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review a submission with no submitted attempts.",
            )

        # Get latest attempt
        latest_attempt = sorted(submission.attempts, key=lambda a: a.attempt_number)[-1]

        # 2. Rubric calculation and Passing Threshold check (BR-ASG-04)
        total_score = sum(r.awarded_points for r in payload.rubric_scores)
        assignment = submission.allocation.assignment

        if payload.review_outcome == "APPROVED":
            if total_score < float(assignment.passing_score):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Cannot approve submission: Total score ({total_score:.1f}) is below the required passing threshold ({assignment.passing_score:.1f}).",
                )
        elif payload.review_outcome == "CORRECTIONS_REQUESTED":
            feedback = (payload.qualitative_feedback or "").strip()
            if not feedback or len(feedback) < 5:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="When requesting corrections (Redo), a meaningful, non-whitespace correction note of at least 5 characters is mandatory.",
                )

        # 3. Create SubmissionReview
        review = SubmissionReview(
            id=uuid.uuid4(),
            attempt_id=latest_attempt.id,
            reviewer_id=reviewer_id,
            review_outcome=payload.review_outcome,
            total_score=total_score,
            qualitative_feedback=payload.qualitative_feedback.strip(),
            internal_evaluator_notes=payload.internal_evaluator_notes.strip() if payload.internal_evaluator_notes else None,
            review_completed_at_utc=now,
            created_at=now,
        )
        db.add(review)
        await db.flush()

        # 4. Insert Rubric Scores
        for item in payload.rubric_scores:
            score_entry = ReviewRubricScore(
                id=uuid.uuid4(),
                review_id=review.id,
                criterion_key=item.criterion_key,
                criterion_title=item.criterion_title,
                max_points=item.max_points,
                awarded_points=item.awarded_points,
                criterion_comments=item.criterion_comments,
            )
            db.add(score_entry)

        # 5. Update AssignmentSubmission states (BR-ASG-01)
        submission.latest_score = total_score
        submission.updated_at = now

        if payload.review_outcome == "APPROVED":
            submission.current_submission_status = "APPROVED"
            submission.current_completion_status = "PASSED_COMPLETED"
        elif payload.review_outcome == "CORRECTIONS_REQUESTED":
            submission.current_submission_status = "CORRECTIONS_REQUESTED"
        elif payload.review_outcome == "REJECTED":
            submission.current_submission_status = "REJECTED"
            submission.current_completion_status = "FAILED"

        await db.flush()

        # 6. Check Prerequisite Gating for Project 1 (BR-PRJ-01: 100% Mandatory Assignment Rule)
        if submission.current_completion_status == "PASSED_COMPLETED":
            candidate = submission.candidate
            # Fetch total mandatory assignments for candidate's track
            track_id = assignment.track_id
            m_count_q = select(func.count(Assignment.id)).where(
                Assignment.track_id == track_id,
                Assignment.is_mandatory == True,
                Assignment.is_active == True,
            )
            m_total = (await db.execute(m_count_q)).scalar() or 0

            # Count how many mandatory assignments candidate has passed
            passed_q = (
                select(func.count(AssignmentSubmission.id))
                .join(AssignmentAllocation, AssignmentSubmission.allocation_id == AssignmentAllocation.id)
                .join(Assignment, AssignmentAllocation.assignment_id == Assignment.id)
                .where(
                    AssignmentSubmission.candidate_id == candidate.id,
                    AssignmentSubmission.current_completion_status == "PASSED_COMPLETED",
                    Assignment.track_id == track_id,
                    Assignment.is_mandatory == True,
                )
            )
            passed_count = (await db.execute(passed_q)).scalar() or 0

            if m_total > 0 and passed_count >= m_total:
                candidate.project_eligible = True
                await write_audit_log(
                    db=db,
                    action="candidate:project_eligible",
                    actor_id=reviewer_id,
                    resource_type="candidate",
                    resource_id=str(candidate.id),
                    details={
                        "track_id": str(track_id),
                        "passed_mandatory_assignments": passed_count,
                        "total_mandatory_assignments": m_total,
                        "reason": "100% mandatory assignment curriculum completed successfully",
                    },
                    request_ip=request_ip,
                    user_agent=user_agent,
                )

        # 7. Audit Log
        await write_audit_log(
            db=db,
            action="assignment_review:completed",
            actor_id=reviewer_id,
            resource_type="assignment_submission",
            resource_id=str(submission.id),
            details={
                "attempt_id": str(latest_attempt.id),
                "review_outcome": payload.review_outcome,
                "total_score": float(total_score),
                "qualitative_feedback": payload.qualitative_feedback,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        # Re-fetch review with rubric scores eager loaded
        rev_q = (
            select(SubmissionReview)
            .options(
                selectinload(SubmissionReview.rubric_scores),
                selectinload(SubmissionReview.reviewer),
            )
            .where(SubmissionReview.id == review.id)
        )
        rev_res = await db.execute(rev_q)
        return rev_res.scalar_one()

    @staticmethod
    async def get_submission_detail(
        db: AsyncSession,
        submission_id: uuid.UUID,
    ) -> AssignmentSubmission:
        query = (
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.candidate),
                selectinload(AssignmentSubmission.allocation).selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentSubmission.attempts).selectinload(SubmissionAttempt.file_asset),
                selectinload(AssignmentSubmission.attempts)
                .selectinload(SubmissionAttempt.reviews)
                .selectinload(SubmissionReview.rubric_scores),
                selectinload(AssignmentSubmission.attempts)
                .selectinload(SubmissionAttempt.reviews)
                .selectinload(SubmissionReview.reviewer),
            )
            .where(AssignmentSubmission.id == submission_id)
        )
        res = await db.execute(query)
        submission = res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found.",
            )
        return submission

    @staticmethod
    async def list_submissions(
        db: AsyncSession,
        status: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        assignment_id: Optional[uuid.UUID] = None,
        candidate_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AssignmentSubmission], int, int]:
        filters = []
        if status:
            filters.append(AssignmentSubmission.current_submission_status == status)
        if candidate_id:
            filters.append(AssignmentSubmission.candidate_id == candidate_id)

        join_alloc = False
        if batch_id:
            filters.append(AssignmentAllocation.batch_id == batch_id)
            join_alloc = True
        if assignment_id:
            filters.append(AssignmentAllocation.assignment_id == assignment_id)
            join_alloc = True

        count_query = select(func.count(AssignmentSubmission.id))
        if join_alloc:
            count_query = count_query.join(AssignmentAllocation, AssignmentSubmission.allocation_id == AssignmentAllocation.id)
        count_query = count_query.where(*filters)
        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (page - 1) * page_size

        query = (
            select(AssignmentSubmission)
            .options(
                selectinload(AssignmentSubmission.candidate),
                selectinload(AssignmentSubmission.allocation).selectinload(AssignmentAllocation.assignment),
                selectinload(AssignmentSubmission.allocation).selectinload(AssignmentAllocation.batch),
                selectinload(AssignmentSubmission.attempts),
            )
        )
        if join_alloc:
            query = query.join(AssignmentAllocation, AssignmentSubmission.allocation_id == AssignmentAllocation.id)
        query = (
            query.where(*filters)
            .order_by(AssignmentSubmission.latest_submitted_at_utc.desc().nullslast(), AssignmentSubmission.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        res = await db.execute(query)
        submissions = list(res.scalars().all())
        return submissions, total, total_pages

    @staticmethod
    async def bulk_update_assignment_statuses(
        db: AsyncSession,
        payload: BulkAssignmentStatusUpdateRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BulkAssignmentStatusUpdateResponse:
        now = utc_now()
        results: List[BulkAssignmentStatusItemResult] = []
        successful_count = 0
        failed_count = 0

        status_map = {
            "NOT_SUBMITTED": "PENDING",
            "Not submitted": "PENDING",
            "SUBMITTED": "SUBMITTED",
            "Submitted": "SUBMITTED",
            "CORRECTIONS_REQUESTED": "CORRECTIONS_REQUESTED",
            "Redo": "CORRECTIONS_REQUESTED",
            "APPROVED": "APPROVED",
            "Done": "APPROVED",
        }

        for item in payload.items:
            norm_status = status_map.get(item.status, item.status)
            if norm_status not in ["PENDING", "SUBMITTED", "CORRECTIONS_REQUESTED", "APPROVED"]:
                results.append(BulkAssignmentStatusItemResult(
                    submission_id=item.submission_id,
                    success=False,
                    error=f"Unsupported status '{item.status}'. Valid statuses: Not submitted, Submitted, Redo, Done."
                ))
                failed_count += 1
                continue

            # Validate Redo mandatory correction note
            if norm_status == "CORRECTIONS_REQUESTED":
                note = (item.correction_note or "").strip()
                if not note or len(note) < 5:
                    results.append(BulkAssignmentStatusItemResult(
                        submission_id=item.submission_id,
                        success=False,
                        error="When setting status to Redo (CORRECTIONS_REQUESTED), a meaningful correction note with at least 5 characters is mandatory."
                    ))
                    failed_count += 1
                    continue

            # Fetch submission
            sub_query = (
                select(AssignmentSubmission)
                .options(
                    selectinload(AssignmentSubmission.attempts),
                    selectinload(AssignmentSubmission.allocation).selectinload(AssignmentAllocation.assignment),
                    selectinload(AssignmentSubmission.candidate),
                )
                .where(AssignmentSubmission.id == item.submission_id)
            )
            sub_res = await db.execute(sub_query)
            submission = sub_res.scalar_one_or_none()
            if not submission:
                results.append(BulkAssignmentStatusItemResult(
                    submission_id=item.submission_id,
                    success=False,
                    error="Assignment submission record not found."
                ))
                failed_count += 1
                continue

            old_sub_status = submission.current_submission_status
            old_comp_status = submission.current_completion_status

            # Ensure submission attempt exists if marking Submitted, Redo, or Done
            if not submission.attempts and norm_status in ["SUBMITTED", "CORRECTIONS_REQUESTED", "APPROVED"]:
                new_attempt = SubmissionAttempt(
                    id=uuid.uuid4(),
                    submission_id=submission.id,
                    attempt_number=1,
                    submitted_at_utc=now,
                    is_late=False,
                    lateness_minutes=0,
                    created_at=now,
                )
                db.add(new_attempt)
                await db.flush()
                submission.attempts.append(new_attempt)
                submission.total_attempts = 1
                submission.latest_submitted_at_utc = now

            latest_attempt = sorted(submission.attempts, key=lambda a: a.attempt_number)[-1] if submission.attempts else None

            # Apply state update
            if norm_status == "PENDING":
                submission.current_submission_status = "PENDING"
                submission.current_completion_status = "INCOMPLETE"
            elif norm_status == "SUBMITTED":
                submission.current_submission_status = "SUBMITTED"
                submission.current_completion_status = "INCOMPLETE"
                submission.latest_submitted_at_utc = now
            elif norm_status == "CORRECTIONS_REQUESTED":
                submission.current_submission_status = "CORRECTIONS_REQUESTED"
                submission.current_completion_status = "INCOMPLETE"
                if latest_attempt:
                    review = SubmissionReview(
                        id=uuid.uuid4(),
                        attempt_id=latest_attempt.id,
                        reviewer_id=actor_id,
                        review_outcome="CORRECTIONS_REQUESTED",
                        total_score=item.awarded_score or 0.0,
                        qualitative_feedback=item.correction_note.strip(),
                        internal_evaluator_notes=item.evaluator_notes.strip() if item.evaluator_notes else None,
                        review_completed_at_utc=now,
                        created_at=now,
                    )
                    db.add(review)
            elif norm_status == "APPROVED":
                submission.current_submission_status = "APPROVED"
                submission.current_completion_status = "PASSED_COMPLETED"
                score = item.awarded_score if item.awarded_score is not None else float(submission.allocation.assignment.passing_score)
                submission.latest_score = score
                if latest_attempt:
                    review = SubmissionReview(
                        id=uuid.uuid4(),
                        attempt_id=latest_attempt.id,
                        reviewer_id=actor_id,
                        review_outcome="APPROVED",
                        total_score=score,
                        qualitative_feedback=item.correction_note.strip() if item.correction_note else "Bulk approved by operational evaluator.",
                        internal_evaluator_notes=item.evaluator_notes.strip() if item.evaluator_notes else None,
                        review_completed_at_utc=now,
                        created_at=now,
                    )
                submission.updated_at = now
                await db.flush()

                # Check 100% prerequisite completion for candidate
                candidate = submission.candidate
                assignment = submission.allocation.assignment
                track_id = assignment.track_id
                m_count_q = select(func.count(Assignment.id)).where(
                    Assignment.track_id == track_id,
                    Assignment.is_mandatory == True,
                    Assignment.is_active == True,
                )
                m_total = (await db.execute(m_count_q)).scalar() or 0

                passed_q = (
                    select(func.count(AssignmentSubmission.id))
                    .join(AssignmentAllocation, AssignmentSubmission.allocation_id == AssignmentAllocation.id)
                    .join(Assignment, AssignmentAllocation.assignment_id == Assignment.id)
                    .where(
                        AssignmentSubmission.candidate_id == candidate.id,
                        AssignmentSubmission.current_completion_status == "PASSED_COMPLETED",
                        Assignment.track_id == track_id,
                        Assignment.is_mandatory == True,
                    )
                )
                passed_count = (await db.execute(passed_q)).scalar() or 0

                if m_total > 0 and passed_count >= m_total and not candidate.project_eligible:
                    candidate.project_eligible = True
                    await db.flush()
                    await write_audit_log(
                        db=db,
                        action="candidate:project_eligible",
                        actor_id=actor_id,
                        resource_type="candidate",
                        resource_id=str(candidate.id),
                        details={
                            "track_id": str(track_id),
                            "passed_mandatory_assignments": passed_count,
                            "total_mandatory_assignments": m_total,
                            "reason": "100% mandatory assignment curriculum completed via bulk update",
                        },
                        request_ip=request_ip,
                        user_agent=user_agent,
                    )

            submission.updated_at = now
            await db.flush()

            # Write individual audit record
            await write_audit_log(
                db=db,
                action="assignment_submission:bulk_status_update",
                actor_id=actor_id,
                resource_type="assignment_submission",
                resource_id=str(submission.id),
                details={
                    "old_submission_status": old_sub_status,
                    "new_submission_status": submission.current_submission_status,
                    "old_completion_status": old_comp_status,
                    "new_completion_status": submission.current_completion_status,
                    "status_label": item.status,
                    "correction_note": item.correction_note,
                },
                request_ip=request_ip,
                user_agent=user_agent,
            )

            results.append(BulkAssignmentStatusItemResult(
                submission_id=item.submission_id,
                success=True,
                status=submission.current_submission_status,
            ))
            successful_count += 1

        await db.commit()

        return BulkAssignmentStatusUpdateResponse(
            total_processed=len(payload.items),
            successful_count=successful_count,
            failed_count=failed_count,
            results=results,
        )

