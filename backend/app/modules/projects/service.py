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
from sqlalchemy.orm import selectinload

from app.core.security import utc_now
from app.modules.audit.service import write_audit_log
from app.modules.candidates.models import CourseTrack
from app.modules.projects.models import Project, ProjectMilestone
from app.modules.projects.schemas import (
    MilestoneCreateItem,
    MilestoneUpdateItem,
    ProjectCreateRequest,
    ProjectUpdateRequest,
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
