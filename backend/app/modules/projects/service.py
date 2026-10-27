"""
ExcelR Track360 - Projects Domain Service Layer
Phase 8: Project Catalog, Milestones, and Capstone Deliverables
Strictly complies with URP-TRK360-V1.0 specifications.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.security import utc_now
from app.modules.audit.service import write_audit_log
from app.modules.auth.models import User
from app.modules.assignments.models import Assignment, AssignmentSubmission, AssignmentAllocation
from app.modules.candidates.models import Batch, Candidate, CourseTrack, Enrollment
from app.modules.projects.models import (
    Project,
    ProjectMilestone,
    ProjectGroup,
    ProjectGroupMember,
    ProjectAllocation,
    ProjectGroupSubmission,
    ProjectProgressionRequest,
)
from app.modules.projects.schemas import (
    MilestoneCreateItem,
    MilestoneUpdateItem,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ProjectGroupCreateRequest,
    ProjectGroupUpdateRequest,
    GroupMemberAddRequest,
    MentorAssignRequest,
    ProjectAllocationRequest,
    ProjectGroupSubmissionCreate,
    ProjectGroupSubmissionReviewRequest,
    ProjectProgressionRequestCreate,
    GroupAdvanceRequest,
    GroupReadinessResponse,
    ProjectProgressionRequestItem,
)


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        payload: ProjectCreateRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Project:
        """Creates a project specification template along with sequential milestone deliverables."""
        # 1. Verify track exists and is active
        track_query = select(CourseTrack).where(CourseTrack.id == payload.track_id)
        track_res = await db.execute(track_query)
        track = track_res.scalar_one_or_none()
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course track referenced by track_id does not exist.",
            )

        # 2. Check code uniqueness
        norm_code = payload.code.strip().upper()
        existing_query = select(Project).where(func.upper(Project.code) == norm_code)
        existing_res = await db.execute(existing_query)
        if existing_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with code '{norm_code}' already exists.",
            )

        now = utc_now()

        # 3. Create Project record
        project = Project(
            id=uuid.uuid4(),
            track_id=payload.track_id,
            code=norm_code,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            tier=payload.tier,
            complexity=payload.complexity,
            min_team_size=payload.min_team_size,
            max_team_size=payload.max_team_size,
            passing_score=payload.passing_score,
            deliverable_specs=[d.model_dump() for d in payload.deliverable_specs],
            rubric_template=[r.model_dump() for r in payload.rubric_template],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(project)
        await db.flush()

        # 4. Insert Milestones
        for m in payload.milestones:
            milestone = ProjectMilestone(
                id=uuid.uuid4(),
                project_id=project.id,
                sequence_order=m.sequence_order,
                title=m.title.strip(),
                description=m.description.strip() if m.description else None,
                weight_percentage=m.weight_percentage,
                max_score=m.max_score,
                is_mandatory=m.is_mandatory,
                required_deliverables=m.required_deliverables,
                created_at=now,
                updated_at=now,
            )
            db.add(milestone)

        # 5. Audit Log
        await write_audit_log(
            db=db,
            action="project:created",
            actor_id=actor_id,
            resource_type="project",
            resource_id=str(project.id),
            details={
                "code": project.code,
                "title": project.title,
                "tier": project.tier,
                "track_id": str(project.track_id),
                "milestone_count": len(payload.milestones),
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        # Re-fetch with eager loaded relationships
        return await ProjectService.get_project(db, project.id)

    @staticmethod
    async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
        """Fetches full project specification including milestones ordered by sequence."""
        query = (
            select(Project)
            .options(
                selectinload(Project.track),
                selectinload(Project.milestones),
            )
            .where(Project.id == project_id)
        )
        res = await db.execute(query)
        project = res.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project specification not found.",
            )
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        track_id: Optional[uuid.UUID] = None,
        tier: Optional[str] = None,
        complexity: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Project], int, int]:
        """Lists projects with filtering, search, and pagination."""
        base_query = select(Project).options(
            selectinload(Project.track),
            selectinload(Project.milestones),
        )

        if track_id:
            base_query = base_query.where(Project.track_id == track_id)
        if tier:
            base_query = base_query.where(Project.tier == tier)
        if complexity:
            base_query = base_query.where(Project.complexity == complexity)
        if is_active is not None:
            base_query = base_query.where(Project.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            base_query = base_query.where(
                or_(Project.code.ilike(s), Project.title.ilike(s), Project.description.ilike(s))
            )

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # Pagination & sorting
        offset = (page - 1) * page_size
        items_query = base_query.order_by(Project.tier.asc(), Project.code.asc()).offset(offset).limit(page_size)
        items_res = await db.execute(items_query)
        items = list(items_res.scalars().all())

        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, total, total_pages

    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: ProjectUpdateRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Project:
        """Updates project details, team parameters, rubrics, or active state."""
        project = await ProjectService.get_project(db, project_id)
        now = utc_now()

        if payload.title is not None:
            project.title = payload.title.strip()
        if payload.description is not None:
            project.description = payload.description.strip()
        if payload.complexity is not None:
            project.complexity = payload.complexity
        if payload.min_team_size is not None:
            project.min_team_size = payload.min_team_size
        if payload.max_team_size is not None:
            if payload.max_team_size < project.min_team_size:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="max_team_size cannot be smaller than min_team_size.",
                )
            project.max_team_size = payload.max_team_size
        if payload.passing_score is not None:
            project.passing_score = payload.passing_score
        if payload.deliverable_specs is not None:
            project.deliverable_specs = [d.model_dump() for d in payload.deliverable_specs]
        if payload.rubric_template is not None:
            project.rubric_template = [r.model_dump() for r in payload.rubric_template]
        if payload.is_active is not None:
            project.is_active = payload.is_active

        project.updated_at = now

        await write_audit_log(
            db=db,
            action="project:updated",
            actor_id=actor_id,
            resource_type="project",
            resource_id=str(project.id),
            details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await ProjectService.get_project(db, project.id)

    @staticmethod
    async def add_milestone(
        db: AsyncSession,
        project_id: uuid.UUID,
        payload: MilestoneCreateItem,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectMilestone:
        """Adds a new sequential milestone stage to an existing project template."""
        project = await ProjectService.get_project(db, project_id)

        # Check sequence order uniqueness
        for m in project.milestones:
            if m.sequence_order == payload.sequence_order:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Milestone sequence_order {payload.sequence_order} is already used.",
                )

        now = utc_now()
        milestone = ProjectMilestone(
            id=uuid.uuid4(),
            project_id=project.id,
            sequence_order=payload.sequence_order,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            weight_percentage=payload.weight_percentage,
            max_score=payload.max_score,
            is_mandatory=payload.is_mandatory,
            required_deliverables=payload.required_deliverables,
            created_at=now,
            updated_at=now,
        )
        db.add(milestone)

        await write_audit_log(
            db=db,
            action="project_milestone:created",
            actor_id=actor_id,
            resource_type="project_milestone",
            resource_id=str(milestone.id),
            details={"project_id": str(project.id), "sequence_order": milestone.sequence_order, "title": milestone.title},
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        await db.refresh(milestone)
        return milestone

    @staticmethod
    async def update_milestone(
        db: AsyncSession,
        project_id: uuid.UUID,
        milestone_id: uuid.UUID,
        payload: MilestoneUpdateItem,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectMilestone:
        """Updates a milestone stage details, weight percentage, or score."""
        query = select(ProjectMilestone).where(
            ProjectMilestone.id == milestone_id,
            ProjectMilestone.project_id == project_id,
        )
        res = await db.execute(query)
        milestone = res.scalar_one_or_none()
        if not milestone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project milestone record not found.",
            )

        now = utc_now()
        if payload.title is not None:
            milestone.title = payload.title.strip()
        if payload.description is not None:
            milestone.description = payload.description.strip()
        if payload.weight_percentage is not None:
            milestone.weight_percentage = payload.weight_percentage
        if payload.max_score is not None:
            milestone.max_score = payload.max_score
        if payload.is_mandatory is not None:
            milestone.is_mandatory = payload.is_mandatory
        if payload.required_deliverables is not None:
            milestone.required_deliverables = payload.required_deliverables

        milestone.updated_at = now

        await write_audit_log(
            db=db,
            action="project_milestone:updated",
            actor_id=actor_id,
            resource_type="project_milestone",
            resource_id=str(milestone.id),
            details={"project_id": str(project_id)},
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        await db.refresh(milestone)
        return milestone


class ProjectGroupService:
    @staticmethod
    async def create_group(
        db: AsyncSession,
        payload: ProjectGroupCreateRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Forms a student collaboration project group within a cohort batch.
        Enforces dynamic sizing constraints (min 2, target 4, max 5).
        """
        # 1. Verify batch exists
        batch_q = select(Batch).where(Batch.id == payload.batch_id)
        batch_res = await db.execute(batch_q)
        batch = batch_res.scalar_one_or_none()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cohort batch not found.",
            )

        # 2. Verify project exists if provided
        if payload.project_id:
            prj_q = select(Project).where(Project.id == payload.project_id)
            prj_res = await db.execute(prj_q)
            if not prj_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Project specification not found.",
                )

        # 3. Check initial candidates count against bounds
        if len(payload.initial_candidate_ids) > payload.max_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Initial member count ({len(payload.initial_candidate_ids)}) exceeds maximum group capacity ({payload.max_size}).",
            )

        now = utc_now()
        group = ProjectGroup(
            id=uuid.uuid4(),
            batch_id=payload.batch_id,
            project_id=payload.project_id,
            group_name=payload.group_name.strip(),
            group_status="FORMING",
            min_size=payload.min_size,
            target_size=payload.target_size,
            max_size=payload.max_size,
            created_by_id=actor_id,
            created_at=now,
            updated_at=now,
        )
        db.add(group)
        await db.flush()

        # 4. Validate and attach initial candidate members
        for cand_id in payload.initial_candidate_ids:
            # Check candidate enrollment in this batch
            enr_q = select(Enrollment).where(
                Enrollment.batch_id == payload.batch_id,
                Enrollment.candidate_id == cand_id,
                Enrollment.enrollment_status == "ACTIVE",
            )
            enr_res = await db.execute(enr_q)
            if not enr_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Candidate {cand_id} is not actively enrolled in batch {batch.batch_code}.",
                )

            # Check candidate is not already in an active project group in this batch
            active_mem_q = (
                select(ProjectGroupMember)
                .join(ProjectGroup, ProjectGroupMember.group_id == ProjectGroup.id)
                .where(
                    ProjectGroup.batch_id == payload.batch_id,
                    ProjectGroupMember.candidate_id == cand_id,
                    ProjectGroupMember.status == "ACTIVE",
                    ProjectGroup.group_status.in_(["FORMING", "ACTIVE", "LOCKED"]),
                )
            )
            active_mem_res = await db.execute(active_mem_q)
            if active_mem_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate {cand_id} is already a member of an active project group in this batch.",
                )

            role = "LEADER" if payload.leader_candidate_id and cand_id == payload.leader_candidate_id else "MEMBER"
            member = ProjectGroupMember(
                id=uuid.uuid4(),
                group_id=group.id,
                candidate_id=cand_id,
                role=role,
                status="ACTIVE",
                joined_at=now,
            )
            db.add(member)

        # 5. Audit Log
        await write_audit_log(
            db=db,
            action="project_group:created",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "group_name": group.group_name,
                "batch_id": str(group.batch_id),
                "member_count": len(payload.initial_candidate_ids),
                "min_size": group.min_size,
                "target_size": group.target_size,
                "max_size": group.max_size,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        gid = group.id
        await db.commit()
        return await ProjectGroupService.get_group(db, gid)

    @staticmethod
    async def get_group(db: AsyncSession, group_id: uuid.UUID) -> ProjectGroup:
        """Fetches full project group details with batch, project, mentor, milestones, members, submissions, and progression requests."""
        query = (
            select(ProjectGroup)
            .options(
                joinedload(ProjectGroup.batch),
                joinedload(ProjectGroup.project),
                joinedload(ProjectGroup.mentor),
                joinedload(ProjectGroup.current_milestone),
                selectinload(ProjectGroup.members).joinedload(ProjectGroupMember.candidate),
                selectinload(ProjectGroup.allocations).joinedload(ProjectAllocation.project),
                selectinload(ProjectGroup.submissions).joinedload(ProjectGroupSubmission.submitted_by),
                selectinload(ProjectGroup.submissions).joinedload(ProjectGroupSubmission.reviewed_by),
                selectinload(ProjectGroup.submissions).joinedload(ProjectGroupSubmission.milestone),
                selectinload(ProjectGroup.progression_requests).joinedload(ProjectProgressionRequest.candidate),
            )
            .where(ProjectGroup.id == group_id)
        )
        res = await db.execute(query)
        group = res.unique().scalar_one_or_none()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project group not found.",
            )
        return group

    @staticmethod
    async def list_groups(
        db: AsyncSession,
        batch_id: Optional[uuid.UUID] = None,
        group_status: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ProjectGroup], int, int]:
        """Lists project groups with batch/status filters and search."""
        base_query = select(ProjectGroup).options(
            joinedload(ProjectGroup.batch),
            joinedload(ProjectGroup.project),
            joinedload(ProjectGroup.mentor),
            joinedload(ProjectGroup.current_milestone),
            selectinload(ProjectGroup.members).joinedload(ProjectGroupMember.candidate),
        )

        if batch_id:
            base_query = base_query.where(ProjectGroup.batch_id == batch_id)
        if group_status:
            base_query = base_query.where(ProjectGroup.group_status == group_status)
        if project_id:
            base_query = base_query.where(ProjectGroup.project_id == project_id)
        if search:
            base_query = base_query.where(ProjectGroup.group_name.ilike(f"%{search.strip()}%"))

        count_query = select(func.count(func.distinct(ProjectGroup.id))).select_from(base_query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        offset = (page - 1) * page_size
        items_query = base_query.order_by(ProjectGroup.created_at.desc()).offset(offset).limit(page_size)
        items_res = await db.execute(items_query)
        items = list(items_res.unique().scalars().all())

        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, total, total_pages

    @staticmethod
    async def add_member(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: GroupMemberAddRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Adds a candidate to a project group.
        Enforces maximum capacity (<= 5) and single active group membership per cohort batch.
        """
        group = await ProjectGroupService.get_group(db, group_id)

        if group.group_status in ["LOCKED", "COMPLETED", "DISSOLVED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add members to group in '{group.group_status}' status.",
            )

        active_members = [m for m in group.members if m.status == "ACTIVE"]
        if len(active_members) >= group.max_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Group has reached maximum capacity of {group.max_size} members.",
            )

        # Verify candidate enrollment in group's batch
        enr_q = select(Enrollment).where(
            Enrollment.batch_id == group.batch_id,
            Enrollment.candidate_id == payload.candidate_id,
            Enrollment.enrollment_status == "ACTIVE",
        )
        enr_res = await db.execute(enr_q)
        if not enr_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Candidate is not actively enrolled in the cohort batch of this group.",
            )

        # Verify candidate is not already active in another group in this batch
        other_q = (
            select(ProjectGroupMember)
            .join(ProjectGroup, ProjectGroupMember.group_id == ProjectGroup.id)
            .where(
                ProjectGroup.batch_id == group.batch_id,
                ProjectGroupMember.candidate_id == payload.candidate_id,
                ProjectGroupMember.status == "ACTIVE",
                ProjectGroup.group_status.in_(["FORMING", "ACTIVE", "LOCKED"]),
            )
        )
        other_res = await db.execute(other_q)
        if other_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Candidate is already an active member of another project group in this batch.",
            )

        now = utc_now()

        # If role is LEADER, demote existing leader
        if payload.role == "LEADER":
            for m in active_members:
                if m.role == "LEADER":
                    m.role = "MEMBER"

        # Check existing member record in this group (e.g. previously removed)
        existing_mem = next((m for m in group.members if m.candidate_id == payload.candidate_id), None)
        if existing_mem:
            existing_mem.status = "ACTIVE"
            existing_mem.role = payload.role
            existing_mem.joined_at = now
        else:
            new_mem = ProjectGroupMember(
                id=uuid.uuid4(),
                group_id=group.id,
                candidate_id=payload.candidate_id,
                role=payload.role,
                status="ACTIVE",
                joined_at=now,
            )
            db.add(new_mem)

        group.updated_at = now

        await write_audit_log(
            db=db,
            action="project_group:member_added",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "candidate_id": str(payload.candidate_id),
                "role": payload.role,
                "new_member_count": len(active_members) + 1,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        db.expire(group)
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        group_id: uuid.UUID,
        candidate_id: uuid.UUID,
        actor_id: uuid.UUID,
        override: bool = False,
        reason: Optional[str] = None,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Removes a member from a project group.
        Enforces minimum team size (>= 2) unless override is specified.
        Immediately recalculates group readiness for remaining members (AC-GRP-003 / BR-GRP-02).
        """
        group = await ProjectGroupService.get_group(db, group_id)
        active_members = [m for m in group.members if m.status == "ACTIVE"]

        member = next((m for m in active_members if m.candidate_id == candidate_id), None)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active membership for candidate not found in this group.",
            )

        if not override and len(active_members) <= group.min_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot remove member: Group would drop below minimum size constraint of {group.min_size} members.",
            )

        member.status = "REMOVED"
        now = utc_now()
        group.updated_at = now

        # If removed member was LEADER, promote first active member
        if member.role == "LEADER":
            remaining = [m for m in active_members if m.candidate_id != candidate_id]
            if remaining:
                remaining[0].role = "LEADER"

        # AC-GRP-003: Immediately recalculate group readiness with remaining active members
        await ProjectGroupService.recalculate_readiness_internal(db, group)

        await write_audit_log(
            db=db,
            action="project_group:member_removed",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "candidate_id": str(candidate_id),
                "override": override,
                "reason": reason or "Member removed by coordinator",
                "remaining_member_count": len(active_members) - 1,
                "recalculated_readiness": group.readiness_status,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def assign_leader(
        db: AsyncSession,
        group_id: uuid.UUID,
        candidate_id: uuid.UUID,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """Designates a candidate as the group leader."""
        group = await ProjectGroupService.get_group(db, group_id)
        active_members = [m for m in group.members if m.status == "ACTIVE"]

        target_member = next((m for m in active_members if m.candidate_id == candidate_id), None)
        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate is not an active member of this group.",
            )

        for m in active_members:
            m.role = "LEADER" if m.candidate_id == candidate_id else "MEMBER"

        now = utc_now()
        group.updated_at = now

        await write_audit_log(
            db=db,
            action="project_group:leader_assigned",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={"leader_candidate_id": str(candidate_id)},
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def update_group(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: ProjectGroupUpdateRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """Updates group name, project assignment, or status transitions."""
        group = await ProjectGroupService.get_group(db, group_id)
        now = utc_now()

        if payload.group_name is not None:
            group.group_name = payload.group_name.strip()
        if payload.project_id is not None:
            prj_q = select(Project).where(Project.id == payload.project_id)
            prj_res = await db.execute(prj_q)
            if not prj_res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project specification not found.")
            group.project_id = payload.project_id
        if payload.group_status is not None:
            if payload.group_status in ["ACTIVE", "LOCKED"]:
                active_count = len([m for m in group.members if m.status == "ACTIVE"])
                if active_count < group.min_size:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Cannot activate group: Needs at least {group.min_size} active members (currently {active_count}).",
                    )
            group.group_status = payload.group_status

        group.updated_at = now

        await write_audit_log(
            db=db,
            action="project_group:updated",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await ProjectGroupService.get_group(db, group_id)

    # ==============================================================
    # Phase 10: Project Allocation & Group Completion Engine
    # ==============================================================

    @staticmethod
    async def assign_mentor(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: MentorAssignRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """Assigns an authoritative staff mentor/evaluator to the project group."""
        group = await ProjectGroupService.get_group(db, group_id)

        mentor = await db.get(User, payload.mentor_id)
        if not mentor or not mentor.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff mentor not found or inactive.",
            )

        group.mentor_id = payload.mentor_id
        group.updated_at = utc_now()

        await write_audit_log(
            db=db,
            action="project_group:mentor_assigned",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "mentor_id": str(payload.mentor_id),
                "mentor_name": mentor.full_name,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        db.expire_all()
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def allocate_project(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: ProjectAllocationRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Allocates a project specification to a project group.
        Strictly enforces:
        1. AC-PRJ-003 Dynamic Group Sizing: min_size <= len(active_members) <= max_size
        2. Course Track Consistency: project.track_id == batch.track_id
        3. BR-PRJ-04 Single Active Project Constraint per candidate
        4. BR-PRJ-02 Maximum 3 Projects Cap per candidate (AC-PRJ-002)
        5. BR-PRJ-01 Prerequisite Assignment Completion Gating (or manual waiver with justification)
        """
        group = await ProjectGroupService.get_group(db, group_id)
        active_members = [m for m in group.members if m.status == "ACTIVE"]

        # 1. AC-PRJ-003: Dynamic group sizing check
        if len(active_members) < group.min_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Group size {len(active_members)} is below minimum permitted size of {group.min_size}.",
            )
        if len(active_members) > group.max_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Group size {len(active_members)} exceeds maximum permitted size of {group.max_size}.",
            )

        # 2. Fetch Project specification
        prj_q = select(Project).options(selectinload(Project.milestones)).where(Project.id == payload.project_id)
        prj_res = await db.execute(prj_q)
        project = prj_res.unique().scalar_one_or_none()
        if not project or not project.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active project specification not found.",
            )

        # 3. Track matching check
        if project.track_id != group.batch.track_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Project track does not match the cohort batch course track.",
            )

        now = utc_now()

        # 4. Validate each active candidate in group
        for member in active_members:
            candidate = member.candidate

            # BR-PRJ-04: Single Active Project Constraint
            other_active_q = (
                select(ProjectGroupMember)
                .join(ProjectGroup, ProjectGroupMember.group_id == ProjectGroup.id)
                .where(
                    ProjectGroupMember.candidate_id == candidate.id,
                    ProjectGroupMember.status == "ACTIVE",
                    ProjectGroup.id != group.id,
                    ProjectGroup.project_id.isnot(None),
                    ProjectGroup.group_status.in_(["ACTIVE", "LOCKED"]),
                )
            )
            other_active = (await db.execute(other_active_q)).scalar_one_or_none()
            if other_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate {candidate.full_name} is already assigned to another active project group (BR-PRJ-04).",
                )

            # BR-PRJ-02: Maximum 3 Projects Cap (AC-PRJ-002)
            completed_alloc_q = (
                select(func.count(ProjectAllocation.id))
                .join(ProjectGroup, ProjectAllocation.group_id == ProjectGroup.id)
                .join(ProjectGroupMember, ProjectGroupMember.group_id == ProjectGroup.id)
                .where(
                    ProjectGroupMember.candidate_id == candidate.id,
                    ProjectAllocation.status == "COMPLETED",
                )
            )
            completed_count = (await db.execute(completed_alloc_q)).scalar() or 0
            if completed_count >= 3:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Maximum standard project limit (3) reached for Candidate {candidate.full_name}.",
                )

            # BR-PRJ-01: Prerequisite Gating for Tier 1
            if project.tier == "TIER_1_FOUNDATIONAL":
                if not payload.waive_prerequisites:
                    # Check if mandatory assignments are passed
                    m_total_q = select(func.count(Assignment.id)).where(
                        Assignment.track_id == group.batch.track_id,
                        Assignment.is_mandatory == True,
                        Assignment.is_active == True,
                    )
                    m_total = (await db.execute(m_total_q)).scalar() or 0
                    track_mandatory = group.batch.track.total_mandatory_assignments if (group.batch and group.batch.track) else 0
                    if (m_total > 0 or track_mandatory > 0) and not candidate.project_eligible:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Candidate {candidate.full_name} has not completed prerequisite mandatory assignments for Project 1 allocation (BR-PRJ-01).",
                        )
                else:
                    if not payload.waiver_justification or not payload.waiver_justification.strip():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Waiver justification is mandatory when waiving project prerequisites.",
                        )
                    await write_audit_log(
                        db=db,
                        action="project_allocation:prerequisite_waived",
                        actor_id=actor_id,
                        resource_type="candidate",
                        resource_id=str(candidate.id),
                        details={
                            "group_id": str(group.id),
                            "project_id": str(project.id),
                            "justification": payload.waiver_justification.strip(),
                        },
                        request_ip=request_ip,
                        user_agent=user_agent,
                    )

            elif project.tier == "TIER_2_INTERMEDIATE":
                if completed_count < 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Candidate {candidate.full_name} must complete Tier 1 project before Tier 2 allocation.",
                    )
            elif project.tier == "TIER_3_CAPSTONE":
                if completed_count < 2:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Candidate {candidate.full_name} must complete Tier 2 project before Tier 3 Capstone allocation.",
                    )

        # 5. Create ProjectAllocation record
        allocation = ProjectAllocation(
            id=uuid.uuid4(),
            group_id=group.id,
            project_id=project.id,
            tier=project.tier,
            status="ALLOCATED",
            allocated_by_id=actor_id,
            allocated_at=now,
        )
        db.add(allocation)

        # 6. Update ProjectGroup state
        group.project_id = project.id
        group.group_status = "ACTIVE"
        group.readiness_status = "AWAITING_SUBMISSION"
        group.allocated_at = now
        group.updated_at = now

        # Set initial milestone if project defines milestones
        sorted_milestones = sorted(project.milestones, key=lambda m: m.sequence_order) if project.milestones else []
        group.current_milestone_id = sorted_milestones[0].id if sorted_milestones else None

        await write_audit_log(
            db=db,
            action="project_group:project_allocated",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "project_id": str(project.id),
                "project_code": project.code,
                "tier": project.tier,
                "waive_prerequisites": payload.waive_prerequisites,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        db.expire_all()
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def submit_deliverable(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: ProjectGroupSubmissionCreate,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroupSubmission:
        """
        Submits group project deliverables (repository, deployment link, notes).
        Submitted by any active group member on behalf of the group (WF-05).
        """
        group = await ProjectGroupService.get_group(db, group_id)
        if not group.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group does not have an active project allocated.",
            )

        active_candidate_ids = [m.candidate_id for m in group.members if m.status == "ACTIVE"]
        if payload.submitted_by_candidate_id not in active_candidate_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submitter must be an active member of this project group.",
            )

        prev_sub_q = select(func.count(ProjectGroupSubmission.id)).where(
            ProjectGroupSubmission.group_id == group.id,
            ProjectGroupSubmission.project_id == group.project_id,
        )
        attempt_number = ((await db.execute(prev_sub_q)).scalar() or 0) + 1

        now = utc_now()
        submission = ProjectGroupSubmission(
            id=uuid.uuid4(),
            group_id=group.id,
            project_id=group.project_id,
            milestone_id=payload.milestone_id or group.current_milestone_id,
            submitted_by_id=payload.submitted_by_candidate_id,
            attempt_number=attempt_number,
            repo_url=payload.repo_url,
            live_demo_url=payload.live_demo_url,
            documentation_url=payload.documentation_url,
            file_asset_id=payload.file_asset_id,
            notes=payload.notes,
            status="SUBMITTED",
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(submission)

        group.readiness_status = "SUBMITTED"
        group.updated_at = now

        await write_audit_log(
            db=db,
            action="project_group:deliverable_submitted",
            actor_id=actor_id,
            resource_type="project_group_submission",
            resource_id=str(submission.id),
            details={
                "group_id": str(group.id),
                "attempt_number": attempt_number,
                "submitted_by_id": str(payload.submitted_by_candidate_id),
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        # Re-fetch submission with joins
        sub_full_q = (
            select(ProjectGroupSubmission)
            .options(
                joinedload(ProjectGroupSubmission.project),
                joinedload(ProjectGroupSubmission.milestone),
                joinedload(ProjectGroupSubmission.submitted_by),
                joinedload(ProjectGroupSubmission.reviewed_by),
            )
            .where(ProjectGroupSubmission.id == submission.id)
        )
        return (await db.execute(sub_full_q)).unique().scalar_one()

    @staticmethod
    async def review_submission(
        db: AsyncSession,
        group_id: uuid.UUID,
        submission_id: uuid.UUID,
        payload: ProjectGroupSubmissionReviewRequest,
        reviewer_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroupSubmission:
        """
        Reviews a group project deliverable submission.
        Assigns score and rubric criteria.
        Transitions readiness state to BLOCKED_PENDING_MEMBERS upon approval to await member sign-offs.
        """
        sub_q = (
            select(ProjectGroupSubmission)
            .where(
                ProjectGroupSubmission.id == submission_id,
                ProjectGroupSubmission.group_id == group_id,
            )
        )
        submission = (await db.execute(sub_q)).scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group submission not found.",
            )

        now = utc_now()
        submission.status = payload.status
        submission.score = payload.score
        submission.feedback = payload.feedback
        submission.rubric_scores = payload.rubric_scores
        submission.reviewed_by_id = reviewer_id
        submission.reviewed_at = now
        submission.updated_at = now

        group = await ProjectGroupService.get_group(db, group_id)
        group.updated_at = now

        if payload.status == "APPROVED":
            # Check milestone sequence
            project = await db.get(Project, submission.project_id)
            milestones = sorted(project.milestones, key=lambda m: m.sequence_order) if (project and project.milestones) else []
            curr_idx = next((i for i, m in enumerate(milestones) if m.id == submission.milestone_id), None)

            if curr_idx is not None and curr_idx + 1 < len(milestones):
                # Intermediate milestone approved -> advance to next milestone
                group.current_milestone_id = milestones[curr_idx + 1].id
                group.readiness_status = "AWAITING_SUBMISSION"
            else:
                # Final deliverable of project tier approved!
                # Clear any obsolete progression requests for this project tier
                del_q = select(ProjectProgressionRequest).where(
                    ProjectProgressionRequest.group_id == group.id,
                    ProjectProgressionRequest.project_id == submission.project_id,
                )
                del_res = await db.execute(del_q)
                for r in del_res.scalars().all():
                    await db.delete(r)

                group.readiness_status = "BLOCKED_PENDING_MEMBERS"
        else:
            group.readiness_status = "CORRECTIONS_REQUESTED"

        await write_audit_log(
            db=db,
            action="project_group:submission_reviewed",
            actor_id=reviewer_id,
            resource_type="project_group_submission",
            resource_id=str(submission.id),
            details={
                "group_id": str(group.id),
                "review_status": payload.status,
                "score": float(payload.score) if payload.score is not None else None,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()

        sub_full_q = (
            select(ProjectGroupSubmission)
            .options(
                joinedload(ProjectGroupSubmission.project),
                joinedload(ProjectGroupSubmission.milestone),
                joinedload(ProjectGroupSubmission.submitted_by),
                joinedload(ProjectGroupSubmission.reviewed_by),
            )
            .where(ProjectGroupSubmission.id == submission.id)
        )
        return (await db.execute(sub_full_q)).unique().scalar_one()

    @staticmethod
    async def request_progression(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: ProjectProgressionRequestCreate,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> GroupReadinessResponse:
        """
        Individual candidate progression sign-off (BR-GRP-01).
        When ALL active members submit, group transitions to READY_FOR_NEXT_PROJECT.
        """
        group = await ProjectGroupService.get_group(db, group_id)
        active_members = [m for m in group.members if m.status == "ACTIVE"]

        if payload.candidate_id not in [m.candidate_id for m in active_members]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate is not an active member of this project group.",
            )

        # Verify current deliverable is marked APPROVED
        latest_sub_q = (
            select(ProjectGroupSubmission)
            .where(
                ProjectGroupSubmission.group_id == group.id,
                ProjectGroupSubmission.project_id == group.project_id,
            )
            .order_by(ProjectGroupSubmission.submitted_at.desc())
        )
        latest_sub = (await db.execute(latest_sub_q)).scalars().first()
        if not latest_sub or latest_sub.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request progression: Group deliverable has not been marked APPROVED.",
            )

        now = utc_now()

        # Check existing request
        req_q = select(ProjectProgressionRequest).where(
            ProjectProgressionRequest.group_id == group.id,
            ProjectProgressionRequest.project_id == group.project_id,
            ProjectProgressionRequest.candidate_id == payload.candidate_id,
        )
        req = (await db.execute(req_q)).scalar_one_or_none()
        if not req:
            req = ProjectProgressionRequest(
                id=uuid.uuid4(),
                group_id=group.id,
                project_id=group.project_id,
                candidate_id=payload.candidate_id,
                status="REQUESTED",
                notes=payload.notes,
                requested_at=now,
            )
            db.add(req)
        else:
            req.status = "REQUESTED"
            req.notes = payload.notes
            req.requested_at = now

        await db.flush()

        # Recalculate readiness
        await ProjectGroupService.recalculate_readiness_internal(db, group)

        await write_audit_log(
            db=db,
            action="project_group:progression_requested",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "candidate_id": str(payload.candidate_id),
                "readiness_status": group.readiness_status,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        return await ProjectGroupService.get_group_readiness(db, group_id)

    @staticmethod
    async def recalculate_readiness_internal(db: AsyncSession, group: ProjectGroup) -> str:
        """
        Evaluates group deliverable status and candidate sign-off requests.
        Sets readiness_status to READY_FOR_NEXT_PROJECT if all active members requested,
        or BLOCKED_PENDING_MEMBERS if any active member is lagging (AC-GRP-001, AC-GRP-002, AC-GRP-003).
        """
        if not group.project_id:
            group.readiness_status = "NOT_READY"
            return group.readiness_status

        # Query latest submission
        latest_sub_q = (
            select(ProjectGroupSubmission)
            .where(
                ProjectGroupSubmission.group_id == group.id,
                ProjectGroupSubmission.project_id == group.project_id,
            )
            .order_by(ProjectGroupSubmission.submitted_at.desc())
        )
        latest_sub = (await db.execute(latest_sub_q)).scalars().first()

        if not latest_sub:
            group.readiness_status = "AWAITING_SUBMISSION"
            return group.readiness_status

        if latest_sub.status == "SUBMITTED":
            group.readiness_status = "SUBMITTED"
            return group.readiness_status
        elif latest_sub.status == "UNDER_REVIEW":
            group.readiness_status = "UNDER_REVIEW"
            return group.readiness_status
        elif latest_sub.status == "CORRECTIONS_REQUESTED":
            group.readiness_status = "CORRECTIONS_REQUESTED"
            return group.readiness_status
        elif latest_sub.status == "APPROVED":
            active_members = [m for m in group.members if m.status == "ACTIVE"]
            reqs_q = select(ProjectProgressionRequest).where(
                ProjectProgressionRequest.group_id == group.id,
                ProjectProgressionRequest.project_id == group.project_id,
                ProjectProgressionRequest.status.in_(["REQUESTED", "WAIVED", "OVERRIDDEN"]),
            )
            reqs = list((await db.execute(reqs_q)).scalars().all())
            ready_ids = set([r.candidate_id for r in reqs])
            active_ids = set([m.candidate_id for m in active_members])
            pending_ids = active_ids - ready_ids

            if len(active_ids) > 0 and len(pending_ids) == 0:
                group.readiness_status = "READY_FOR_NEXT_PROJECT"
            else:
                group.readiness_status = "BLOCKED_PENDING_MEMBERS"
            return group.readiness_status

        return group.readiness_status

    @staticmethod
    async def get_group_readiness(db: AsyncSession, group_id: uuid.UUID) -> GroupReadinessResponse:
        """Computes comprehensive group readiness evaluation breakdown."""
        group = await ProjectGroupService.get_group(db, group_id)
        active_members = [m for m in group.members if m.status == "ACTIVE"]

        # Latest submission
        latest_sub_q = (
            select(ProjectGroupSubmission)
            .where(
                ProjectGroupSubmission.group_id == group.id,
                ProjectGroupSubmission.project_id == group.project_id,
            )
            .order_by(ProjectGroupSubmission.submitted_at.desc())
        )
        latest_sub = (await db.execute(latest_sub_q)).scalars().first()
        deliverable_approved = bool(latest_sub and latest_sub.status == "APPROVED")

        # Requests
        reqs_q = (
            select(ProjectProgressionRequest)
            .options(joinedload(ProjectProgressionRequest.candidate))
            .where(
                ProjectProgressionRequest.group_id == group.id,
                ProjectProgressionRequest.project_id == group.project_id,
            )
        )
        reqs = list((await db.execute(reqs_q)).unique().scalars().all())
        ready_ids = [r.candidate_id for r in reqs if r.status in ["REQUESTED", "WAIVED", "OVERRIDDEN"]]

        active_id_map = {m.candidate_id: m.candidate for m in active_members}
        pending_ids = [cid for cid in active_id_map.keys() if cid not in ready_ids]
        pending_names = [f"{active_id_map[cid].first_name} {active_id_map[cid].last_name}" for cid in pending_ids]

        can_advance = group.readiness_status == "READY_FOR_NEXT_PROJECT"

        req_items = [
            ProjectProgressionRequestItem(
                id=r.id,
                candidate_id=r.candidate_id,
                candidate_name=f"{r.candidate.first_name} {r.candidate.last_name}" if r.candidate else None,
                candidate_number=r.candidate.candidate_number if r.candidate else None,
                status=r.status,
                requested_at=r.requested_at,
                notes=r.notes,
            )
            for r in reqs
        ]

        return GroupReadinessResponse(
            group_id=group.id,
            group_name=group.group_name,
            group_status=group.group_status,
            readiness_status=group.readiness_status,
            current_project_id=group.project_id,
            current_project_title=group.project.title if group.project else None,
            current_tier=group.project.tier if group.project else None,
            current_milestone_id=group.current_milestone_id,
            current_milestone_title=group.current_milestone.title if group.current_milestone else None,
            deliverable_approved=deliverable_approved,
            active_members_count=len(active_members),
            requests_count=len(ready_ids),
            ready_candidate_ids=ready_ids,
            pending_candidate_ids=pending_ids,
            pending_candidate_names=pending_names,
            can_advance=can_advance,
            latest_submission_status=latest_sub.status if latest_sub else None,
            latest_submission_score=float(latest_sub.score) if (latest_sub and latest_sub.score is not None) else None,
            progression_requests=req_items,
        )

    @staticmethod
    async def advance_group(
        db: AsyncSession,
        group_id: uuid.UUID,
        payload: GroupAdvanceRequest,
        actor_id: uuid.UUID,
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Advances a project group to the next milestone/project tier (WF-06).
        Enforces:
        - Readiness requirement (READY_FOR_NEXT_PROJECT) unless admin override justification is supplied.
        - Completes current project allocation with final score.
        - Capstone (Tier 3) completion marks group as COMPLETED and prevents 4th project allocation (BR-PRJ-02).
        """
        group = await ProjectGroupService.get_group(db, group_id)

        if group.readiness_status != "READY_FOR_NEXT_PROJECT":
            if not payload.override_justification or not payload.override_justification.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Group is not ready for advancement. All active members must submit progression requests, or an override justification is required.",
                )

        now = utc_now()

        # 1. Complete current project allocation
        curr_alloc_q = (
            select(ProjectAllocation)
            .where(
                ProjectAllocation.group_id == group.id,
                ProjectAllocation.project_id == group.project_id,
                ProjectAllocation.status != "COMPLETED",
            )
            .order_by(ProjectAllocation.allocated_at.desc())
        )
        curr_alloc = (await db.execute(curr_alloc_q)).scalars().first()
        if curr_alloc:
            curr_alloc.status = "COMPLETED"
            curr_alloc.completed_at = now

            # Fetch latest score
            latest_sub_q = (
                select(ProjectGroupSubmission)
                .where(
                    ProjectGroupSubmission.group_id == group.id,
                    ProjectGroupSubmission.project_id == group.project_id,
                    ProjectGroupSubmission.status == "APPROVED",
                )
                .order_by(ProjectGroupSubmission.submitted_at.desc())
            )
            latest_sub = (await db.execute(latest_sub_q)).scalars().first()
            if latest_sub:
                curr_alloc.final_score = latest_sub.score

        # 2. Check current tier
        current_tier = group.project.tier if group.project else "TIER_1_FOUNDATIONAL"

        if current_tier == "TIER_3_CAPSTONE":
            # Completed all 3 tiers! Group completes fully.
            group.group_status = "COMPLETED"
            group.readiness_status = "COMPLETED"
            group.completed_at = now
        else:
            if payload.next_project_id:
                next_prj_q = select(Project).options(selectinload(Project.milestones)).where(Project.id == payload.next_project_id)
                next_prj = (await db.execute(next_prj_q)).unique().scalar_one_or_none()
                if not next_prj or not next_prj.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Next project specification not found or inactive.",
                    )

                # Create next allocation
                next_alloc = ProjectAllocation(
                    id=uuid.uuid4(),
                    group_id=group.id,
                    project_id=next_prj.id,
                    tier=next_prj.tier,
                    status="ALLOCATED",
                    allocated_by_id=actor_id,
                    allocated_at=now,
                )
                db.add(next_alloc)

                group.project_id = next_prj.id
                group.group_status = "ACTIVE"
                group.readiness_status = "AWAITING_SUBMISSION"
                sorted_milestones = sorted(next_prj.milestones, key=lambda m: m.sequence_order) if next_prj.milestones else []
                group.current_milestone_id = sorted_milestones[0].id if sorted_milestones else None
            else:
                # Group is set to READY_FOR_NEXT_PROJECT awaiting coordinator project selection
                group.project_id = None
                group.current_milestone_id = None
                group.readiness_status = "READY_FOR_NEXT_PROJECT"

        group.updated_at = now

        await write_audit_log(
            db=db,
            action="project_group:advanced",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "previous_tier": current_tier,
                "new_group_status": group.group_status,
                "new_readiness_status": group.readiness_status,
                "override": bool(payload.override_justification),
                "justification": payload.override_justification,
            },
            request_ip=request_ip,
            user_agent=user_agent,
        )

        await db.commit()
        db.expire_all()
        return await ProjectGroupService.get_group(db, group_id)

    @staticmethod
    async def list_submissions(
        db: AsyncSession,
        group_id: uuid.UUID,
    ) -> List[ProjectGroupSubmission]:
        """Lists all deliverable submissions for a project group."""
        query = (
            select(ProjectGroupSubmission)
            .options(
                joinedload(ProjectGroupSubmission.project),
                joinedload(ProjectGroupSubmission.milestone),
                joinedload(ProjectGroupSubmission.submitted_by),
                joinedload(ProjectGroupSubmission.reviewed_by),
            )
            .where(ProjectGroupSubmission.group_id == group_id)
            .order_by(ProjectGroupSubmission.submitted_at.desc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())


