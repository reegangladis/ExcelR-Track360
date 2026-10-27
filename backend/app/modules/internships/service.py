"""
ExcelR Track360 - Internship Lifecycle & Duration Mapping Service
Domain 5: Internship Tracking, Decoupled Calendar Dates & Accredited Duration Policy.
Strictly adheres to BR-INT-01, BR-INT-02, and SoD security constraints.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.security import utc_now
from app.modules.auth.models import User
from app.modules.candidates.models import Candidate, CourseTrack, Batch
from app.modules.projects.models import (
    Project,
    ProjectGroup,
    ProjectGroupMember,
    ProjectAllocation,
    ProjectGroupSubmission,
)
from app.modules.internships.models import InternshipRecord, InternshipMilestone
from app.modules.internships.schemas import (
    InternshipCreateRequest,
    InternshipUpdateRequest,
    InternshipCompleteRequest,
    InternshipTerminateRequest,
    CandidateInternshipEligibilityResponse,
)
from app.modules.audit.service import write_audit_log


class InternshipService:
    """Authoritative business logic for candidate internships and accredited milestone progression."""

    @staticmethod
    async def count_candidate_approved_projects(db: AsyncSession, candidate_id: uuid.UUID) -> int:
        """
        Calculates the number of approved project achievements for a candidate across all groups.
        A project is approved if:
        1. A group where the candidate is an active member has an APPROVED deliverable submission, OR
        2. The group has completed the project or is in READY_FOR_NEXT_PROJECT / COMPLETED status.
        """
        # Groups where candidate is an active member
        groups_query = (
            select(ProjectGroup)
            .join(ProjectGroupMember, ProjectGroupMember.group_id == ProjectGroup.id)
            .where(
                ProjectGroupMember.candidate_id == candidate_id,
                ProjectGroupMember.status == "ACTIVE",
            )
        )
        groups_result = await db.execute(groups_query)
        groups = groups_result.scalars().all()

        if not groups:
            return 0

        group_ids = [g.id for g in groups]

        # Check completed allocations or approved submissions
        submissions_query = (
            select(func.count(func.distinct(ProjectGroupSubmission.project_id)))
            .where(
                ProjectGroupSubmission.group_id.in_(group_ids),
                ProjectGroupSubmission.status == "APPROVED",
            )
        )
        sub_res = await db.execute(submissions_query)
        approved_by_submission = sub_res.scalar() or 0

        # Also check groups marked COMPLETED or READY_FOR_NEXT_PROJECT
        completed_groups_count = sum(
            1 for g in groups if g.readiness_status in ("READY_FOR_NEXT_PROJECT", "COMPLETED")
        )

        return max(approved_by_submission, completed_groups_count)

    @staticmethod
    def calculate_duration_from_projects(approved_projects_count: int, multiplier_months: int = 3) -> int:
        """
        Applies BR-INT-02 Configurable Policy Matrix:
        Tier 1 (1 PRJ) -> 3 Months
        Tier 2 (2 PRJ) -> 6 Months
        Tier 3 (3 PRJ) -> 9 Months
        Default baseline is minimum 3 months upon first project approval.
        """
        if approved_projects_count <= 1:
            return 3
        elif approved_projects_count == 2:
            return 6
        else:
            return min(approved_projects_count * multiplier_months, 9)

    @classmethod
    async def calculate_candidate_eligibility(
        cls, db: AsyncSession, candidate_id: uuid.UUID
    ) -> CandidateInternshipEligibilityResponse:
        """Evaluates whether a candidate satisfies academic criteria for formal internship."""
        candidate = await db.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found.",
            )

        # Check existing record
        existing_res = await db.execute(
            select(InternshipRecord).where(InternshipRecord.candidate_id == candidate_id)
        )
        existing_rec = existing_res.scalars().first()

        approved_projects = await cls.count_candidate_approved_projects(db, candidate_id)
        recommended_duration = cls.calculate_duration_from_projects(approved_projects)

        # Candidate is eligible if they have passed assignments, project eligible, or already have 1 project
        is_eligible = (
            candidate.project_eligible or
            approved_projects >= 1 or
            existing_rec is not None
        )

        reason = (
            "Candidate has completed prerequisite coursework and verified project milestones."
            if is_eligible
            else "Candidate requires completion of prerequisite assignments or Project Tier 1."
        )

        return CandidateInternshipEligibilityResponse(
            candidate_id=candidate.id,
            candidate_name=candidate.full_name,
            is_eligible=is_eligible,
            approved_projects_count=approved_projects,
            mandatory_assignments_passed=candidate.project_eligible,
            recommended_accredited_months=recommended_duration,
            existing_record_id=existing_rec.id if existing_rec else None,
            eligible_reason=reason,
        )

    @classmethod
    async def initialize_internship(
        cls,
        db: AsyncSession,
        payload: InternshipCreateRequest,
        actor_user: User,
    ) -> InternshipRecord:
        """
        Initializes a formal InternshipRecord (WF-07).
        Strictly decouples calendar dates from accredited duration policy (BR-INT-01).
        """
        candidate = await db.get(Candidate, payload.candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {payload.candidate_id} not found.",
            )

        track = await db.get(CourseTrack, payload.track_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course Track with ID {payload.track_id} not found.",
            )

        # Check duplicate active record
        existing_res = await db.execute(
            select(InternshipRecord).where(
                InternshipRecord.candidate_id == payload.candidate_id,
                InternshipRecord.track_id == payload.track_id,
            )
        )
        if existing_res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An internship record already exists for candidate {candidate.full_name} under track {track.code}.",
            )

        # Validate calendar dates
        if payload.expected_end_date and payload.expected_end_date < payload.start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expected end date cannot be earlier than internship start date.",
            )

        # Determine accredited duration via BR-INT-02
        approved_projects = await cls.count_candidate_approved_projects(db, payload.candidate_id)
        accredited_months = cls.calculate_duration_from_projects(approved_projects)

        record = InternshipRecord(
            id=uuid.uuid4(),
            candidate_id=payload.candidate_id,
            track_id=payload.track_id,
            start_date=payload.start_date,
            expected_end_date=payload.expected_end_date,
            accredited_duration_months=accredited_months,
            internship_status=payload.initial_status or "ACTIVE",
            company_name=payload.company_name or "ExcelR Technology Labs",
            coordinator_notes=payload.coordinator_notes,
        )
        db.add(record)

        # Create sequential accredited milestone tiers (Tiers 1, 2, and 3)
        milestone_definitions = [
            (1, "Milestone 1: Foundational Practical Implementation", 3),
            (2, "Milestone 2: Intermediate Systems Architecture", 6),
            (3, "Milestone 3: Enterprise Capstone Integration", 9),
        ]

        for tier, title, months in milestone_definitions:
            m_status = "ACHIEVED" if approved_projects >= tier else ("IN_PROGRESS" if tier == 1 else "PENDING")
            achieved_dt = utc_now() if m_status == "ACHIEVED" else None
            m = InternshipMilestone(
                id=uuid.uuid4(),
                internship_record_id=record.id,
                milestone_tier=tier,
                title=title,
                accredited_months=months,
                status=m_status,
                achieved_at=achieved_dt,
                verified_by_id=actor_user.id if m_status == "ACHIEVED" else None,
                notes="Auto-verified based on project tier completion." if m_status == "ACHIEVED" else None,
            )
            db.add(m)

        # Audit Log
        await write_audit_log(
            db=db,
            action="internship:initialized",
            actor_id=actor_user.id,
            resource_type="internship_record",
            resource_id=str(record.id),
            details={
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.full_name,
                "track_id": str(track.id),
                "track_code": track.code,
                "start_date": str(record.start_date),
                "expected_end_date": str(record.expected_end_date) if record.expected_end_date else None,
                "accredited_duration_months": record.accredited_duration_months,
                "internship_status": record.internship_status,
                "company_name": record.company_name,
            },
        )

        record_id = record.id
        await db.commit()
        return await cls.get_internship(db, record_id)

    @classmethod
    async def update_internship(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        payload: InternshipUpdateRequest,
        actor_user: User,
    ) -> InternshipRecord:
        """Updates operational calendar dates or company mapping (BR-INT-01)."""
        record = await db.get(InternshipRecord, record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Internship record with ID {record_id} not found.",
            )

        start = payload.start_date or record.start_date
        exp_end = payload.expected_end_date if payload.expected_end_date is not None else record.expected_end_date
        if exp_end and exp_end < start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expected end date cannot be earlier than start date.",
            )

        if payload.start_date is not None:
            record.start_date = payload.start_date
        if payload.expected_end_date is not None:
            record.expected_end_date = payload.expected_end_date
        if payload.actual_completion_date is not None:
            record.actual_completion_date = payload.actual_completion_date
        if payload.company_name is not None:
            record.company_name = payload.company_name
        if payload.coordinator_notes is not None:
            record.coordinator_notes = payload.coordinator_notes
        if payload.internship_status is not None:
            record.internship_status = payload.internship_status

        record.updated_at = utc_now()

        # Audit Log
        await write_audit_log(
            db=db,
            action="internship:updated",
            actor_id=actor_user.id,
            resource_type="internship_record",
            resource_id=str(record.id),
            details={
                "start_date": str(record.start_date),
                "expected_end_date": str(record.expected_end_date) if record.expected_end_date else None,
                "actual_completion_date": str(record.actual_completion_date) if record.actual_completion_date else None,
                "internship_status": record.internship_status,
                "company_name": record.company_name,
            },
        )

        rec_id = record.id
        await db.commit()
        return await cls.get_internship(db, rec_id)

    @classmethod
    async def complete_internship(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        payload: InternshipCompleteRequest,
        actor_user: User,
    ) -> InternshipRecord:
        """Formally confirms verified completion of an internship record."""
        record = await db.get(InternshipRecord, record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Internship record with ID {record_id} not found.",
            )

        if record.internship_status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Internship record is already marked as COMPLETED.",
            )

        if record.internship_status == "TERMINATED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete an internship that has been marked as TERMINATED.",
            )

        completion_date = payload.actual_completion_date or date.today()
        if completion_date < record.start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Actual completion date cannot be earlier than start date.",
            )

        record.internship_status = "COMPLETED"
        record.actual_completion_date = completion_date
        if payload.completion_notes:
            existing_notes = record.coordinator_notes or ""
            record.coordinator_notes = f"{existing_notes}\n[Completion Note]: {payload.completion_notes}".strip()
        record.updated_at = utc_now()

        # Ensure active milestone tier is marked ACHIEVED
        milestones_res = await db.execute(
            select(InternshipMilestone).where(InternshipMilestone.internship_record_id == record.id)
        )
        milestones = milestones_res.scalars().all()
        for m in milestones:
            if m.status != "ACHIEVED" and m.accredited_months <= record.accredited_duration_months:
                m.status = "ACHIEVED"
                m.achieved_at = utc_now()
                m.verified_by_id = actor_user.id
                m.updated_at = utc_now()

        # Audit Log
        await write_audit_log(
            db=db,
            action="internship:completed",
            actor_id=actor_user.id,
            resource_type="internship_record",
            resource_id=str(record.id),
            details={
                "actual_completion_date": str(record.actual_completion_date),
                "accredited_duration_months": record.accredited_duration_months,
                "verified_by_id": str(actor_user.id),
            },
        )

        rec_id = record.id
        await db.commit()
        return await cls.get_internship(db, rec_id)

    @classmethod
    async def terminate_internship(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        payload: InternshipTerminateRequest,
        actor_user: User,
    ) -> InternshipRecord:
        """Terminates an internship with mandatory justification."""
        record = await db.get(InternshipRecord, record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Internship record with ID {record_id} not found.",
            )

        if record.internship_status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot terminate an internship that is already COMPLETED.",
            )

        record.internship_status = "TERMINATED"
        existing_notes = record.coordinator_notes or ""
        record.coordinator_notes = f"{existing_notes}\n[Terminated on {date.today()}]: {payload.reason}".strip()
        record.updated_at = utc_now()

        # Audit Log
        await write_audit_log(
            db=db,
            action="internship:terminated",
            actor_id=actor_user.id,
            resource_type="internship_record",
            resource_id=str(record.id),
            details={
                "reason": payload.reason,
                "previous_status": record.internship_status,
            },
            justification=payload.reason,
        )

        rec_id = record.id
        await db.commit()
        return await cls.get_internship(db, rec_id)

    @classmethod
    async def sync_accredited_duration(
        cls,
        db: AsyncSession,
        record_id: uuid.UUID,
        actor_user: User,
    ) -> InternshipRecord:
        """Recalculates accredited duration from candidate's latest approved projects (BR-INT-02)."""
        record = await db.get(InternshipRecord, record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Internship record with ID {record_id} not found.",
            )

        approved_projects = await cls.count_candidate_approved_projects(db, record.candidate_id)
        new_duration = cls.calculate_duration_from_projects(approved_projects)
        old_duration = record.accredited_duration_months
        record.accredited_duration_months = new_duration
        record.updated_at = utc_now()

        # Update milestones
        milestones_res = await db.execute(
            select(InternshipMilestone).where(InternshipMilestone.internship_record_id == record.id)
        )
        milestones = milestones_res.scalars().all()
        for m in milestones:
            if approved_projects >= m.milestone_tier and m.status != "ACHIEVED":
                m.status = "ACHIEVED"
                m.achieved_at = utc_now()
                m.verified_by_id = actor_user.id
                m.updated_at = utc_now()

        # Audit Log
        await write_audit_log(
            db=db,
            action="internship:duration_synced",
            actor_id=actor_user.id,
            resource_type="internship_record",
            resource_id=str(record.id),
            details={
                "previous_duration_months": old_duration,
                "new_duration_months": new_duration,
                "approved_projects_count": approved_projects,
            },
        )

        rec_id = record.id
        await db.commit()
        return await cls.get_internship(db, rec_id)

    @classmethod
    async def get_internship(cls, db: AsyncSession, record_id: uuid.UUID) -> InternshipRecord:
        """Retrieves an InternshipRecord with candidate, track, and milestones."""
        stmt = (
            select(InternshipRecord)
            .options(
                joinedload(InternshipRecord.candidate),
                joinedload(InternshipRecord.track),
                selectinload(InternshipRecord.milestones).joinedload(InternshipMilestone.project),
                selectinload(InternshipRecord.milestones).joinedload(InternshipMilestone.verified_by),
            )
            .where(InternshipRecord.id == record_id)
        )
        res = await db.execute(stmt)
        record = res.scalars().first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Internship record with ID {record_id} not found.",
            )
        return record

    @classmethod
    async def get_internship_by_candidate(
        cls, db: AsyncSession, candidate_id: uuid.UUID
    ) -> Optional[InternshipRecord]:
        """Retrieves candidate's active or latest internship record."""
        stmt = (
            select(InternshipRecord)
            .options(
                joinedload(InternshipRecord.candidate),
                joinedload(InternshipRecord.track),
                selectinload(InternshipRecord.milestones).joinedload(InternshipMilestone.project),
                selectinload(InternshipRecord.milestones).joinedload(InternshipMilestone.verified_by),
            )
            .where(InternshipRecord.candidate_id == candidate_id)
            .order_by(InternshipRecord.created_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def list_internships(
        cls,
        db: AsyncSession,
        track_id: Optional[uuid.UUID] = None,
        candidate_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[InternshipRecord], int]:
        """Lists internship records with multi-criteria filtering and pagination."""
        stmt = (
            select(InternshipRecord)
            .options(
                joinedload(InternshipRecord.candidate),
                joinedload(InternshipRecord.track),
                selectinload(InternshipRecord.milestones),
            )
            .join(Candidate, Candidate.id == InternshipRecord.candidate_id)
            .join(CourseTrack, CourseTrack.id == InternshipRecord.track_id)
        )

        count_stmt = (
            select(func.count(InternshipRecord.id))
            .join(Candidate, Candidate.id == InternshipRecord.candidate_id)
            .join(CourseTrack, CourseTrack.id == InternshipRecord.track_id)
        )

        if track_id:
            stmt = stmt.where(InternshipRecord.track_id == track_id)
            count_stmt = count_stmt.where(InternshipRecord.track_id == track_id)

        if candidate_id:
            stmt = stmt.where(InternshipRecord.candidate_id == candidate_id)
            count_stmt = count_stmt.where(InternshipRecord.candidate_id == candidate_id)

        if status_filter:
            stmt = stmt.where(InternshipRecord.internship_status == status_filter)
            count_stmt = count_stmt.where(InternshipRecord.internship_status == status_filter)

        if search:
            search_clause = or_(
                Candidate.first_name.ilike(f"%{search}%"),
                Candidate.last_name.ilike(f"%{search}%"),
                Candidate.candidate_number.ilike(f"%{search}%"),
                Candidate.email.ilike(f"%{search}%"),
                CourseTrack.title.ilike(f"%{search}%"),
                CourseTrack.code.ilike(f"%{search}%"),
                InternshipRecord.company_name.ilike(f"%{search}%"),
            )
            stmt = stmt.where(search_clause)
            count_stmt = count_stmt.where(search_clause)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(InternshipRecord.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        records_res = await db.execute(stmt)
        records = records_res.scalars().all()

        return records, total
