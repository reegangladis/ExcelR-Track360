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
from app.modules.candidates.models import Batch, Candidate, CourseTrack, Enrollment
from app.modules.projects.models import Project, ProjectMilestone, ProjectGroup, ProjectGroupMember
from app.modules.projects.schemas import (
    MilestoneCreateItem,
    MilestoneUpdateItem,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ProjectGroupCreateRequest,
    ProjectGroupUpdateRequest,
    GroupMemberAddRequest,
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
        """Fetches full project group details with batch, project, and members."""
        query = (
            select(ProjectGroup)
            .options(
                joinedload(ProjectGroup.batch),
                joinedload(ProjectGroup.project),
                joinedload(ProjectGroup.members).joinedload(ProjectGroupMember.candidate),
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
            joinedload(ProjectGroup.members).joinedload(ProjectGroupMember.candidate),
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
        request_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProjectGroup:
        """
        Removes a member from a project group.
        Enforces minimum team size (>= 2) unless override is specified.
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

        await write_audit_log(
            db=db,
            action="project_group:member_removed",
            actor_id=actor_id,
            resource_type="project_group",
            resource_id=str(group.id),
            details={
                "candidate_id": str(candidate_id),
                "override": override,
                "remaining_member_count": len(active_members) - 1,
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
            # Verify project exists
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

