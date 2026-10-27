"""
ExcelR Track360 - Assignment Management Service
Implements business rules for assignment templates, rubrics, and cohort/candidate allocations.
"""
from datetime import datetime, timezone
import math
from typing import Optional, Tuple, List
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import utc_now
from app.modules.audit.service import write_audit_log
from app.modules.candidates.models import CourseTrack, Batch, Candidate
from app.modules.assignments.models import (
    Assignment,
    AssignmentAllocation,
    AssignmentSubmission,
)
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AllocationCreateRequest,
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
        await db.refresh(assignment)
        return assignment

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
        await db.refresh(assignment)
        return assignment

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
