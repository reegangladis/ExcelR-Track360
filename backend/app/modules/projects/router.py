"""
ExcelR Track360 - Projects Domain API Router
Phase 8: Project Catalog, Milestones, and Capstone Deliverables
Strictly complies with URP-TRK360-V1.0 specifications.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_permission
from app.modules.auth.models import User
from app.modules.projects.models import Project, ProjectMilestone, ProjectGroup, ProjectGroupMember
from app.modules.projects.schemas import (
    MilestoneCreateItem,
    MilestoneResponse,
    MilestoneUpdateItem,
    ProjectCreateRequest,
    ProjectListItem,
    ProjectPaginatedResponse,
    ProjectResponse,
    ProjectUpdateRequest,
    GroupMemberAddRequest,
    GroupMemberItem,
    ProjectGroupCreateRequest,
    ProjectGroupListItem,
    ProjectGroupPaginatedResponse,
    ProjectGroupResponse,
    ProjectGroupUpdateRequest,
)
from app.modules.projects.service import ProjectService, ProjectGroupService

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_milestone_response(m: ProjectMilestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=m.id,
        project_id=m.project_id,
        sequence_order=m.sequence_order,
        title=m.title,
        description=m.description,
        weight_percentage=float(m.weight_percentage),
        max_score=float(m.max_score),
        is_mandatory=m.is_mandatory,
        required_deliverables=m.required_deliverables or [],
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _to_project_response(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        track_id=p.track_id,
        track_title=p.track.title if p.track else None,
        code=p.code,
        title=p.title,
        description=p.description,
        tier=p.tier,
        complexity=p.complexity,
        min_team_size=p.min_team_size,
        max_team_size=p.max_team_size,
        passing_score=float(p.passing_score),
        deliverable_specs=p.deliverable_specs or [],
        rubric_template=p.rubric_template or [],
        is_active=p.is_active,
        milestones=[_to_milestone_response(m) for m in p.milestones],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_project_list_item(p: Project) -> ProjectListItem:
    return ProjectListItem(
        id=p.id,
        track_id=p.track_id,
        track_title=p.track.title if p.track else None,
        code=p.code,
        title=p.title,
        tier=p.tier,
        complexity=p.complexity,
        min_team_size=p.min_team_size,
        max_team_size=p.max_team_size,
        passing_score=float(p.passing_score),
        milestone_count=len(p.milestones) if p.milestones else 0,
        is_active=p.is_active,
        created_at=p.created_at,
    )


def _to_group_member_item(m: ProjectGroupMember) -> GroupMemberItem:
    return GroupMemberItem(
        id=m.id,
        candidate_id=m.candidate_id,
        candidate_name=f"{m.candidate.first_name} {m.candidate.last_name}" if m.candidate else "Unknown",
        candidate_number=m.candidate.candidate_number if m.candidate else "",
        candidate_email=m.candidate.email if m.candidate else "",
        role=m.role,
        status=m.status,
        joined_at=m.joined_at,
    )


def _to_group_response(g: ProjectGroup) -> ProjectGroupResponse:
    active_m = [m for m in g.members if m.status == "ACTIVE"]
    return ProjectGroupResponse(
        id=g.id,
        batch_id=g.batch_id,
        batch_code=g.batch.batch_code if g.batch else None,
        batch_title=g.batch.title if g.batch else None,
        project_id=g.project_id,
        project_code=g.project.code if g.project else None,
        project_title=g.project.title if g.project else None,
        group_name=g.group_name,
        group_status=g.group_status,
        min_size=g.min_size,
        target_size=g.target_size,
        max_size=g.max_size,
        member_count=len(active_m),
        members=[_to_group_member_item(m) for m in active_m],
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


def _to_group_list_item(g: ProjectGroup) -> ProjectGroupListItem:
    active_m = [m for m in g.members if m.status == "ACTIVE"]
    return ProjectGroupListItem(
        id=g.id,
        batch_id=g.batch_id,
        batch_code=g.batch.batch_code if g.batch else None,
        project_id=g.project_id,
        project_code=g.project.code if g.project else None,
        group_name=g.group_name,
        group_status=g.group_status,
        member_count=len(active_m),
        min_size=g.min_size,
        target_size=g.target_size,
        max_size=g.max_size,
        created_at=g.created_at,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def create_project(
    payload: ProjectCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new project specification in the curriculum catalog.
    Validates tier classification, deliverable specifications, and milestone weights (100%).
    """
    project = await ProjectService.create_project(
        db=db,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_project_response(project)


@router.get(
    "",
    response_model=ProjectPaginatedResponse,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def list_projects(
    track_id: Optional[uuid.UUID] = Query(None, description="Filter by course track"),
    tier: Optional[str] = Query(None, description="Filter by tier (TIER_1_FOUNDATIONAL, TIER_2_INTERMEDIATE, TIER_3_CAPSTONE)"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by code or title"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lists project catalog specifications with filtering, search, and pagination."""
    items, total, total_pages = await ProjectService.list_projects(
        db=db,
        track_id=track_id,
        tier=tier,
        complexity=complexity,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ProjectPaginatedResponse(
        items=[_to_project_list_item(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==========================================
# Phase 9: Project Groups & Dynamic Sizing
# ==========================================

@router.post(
    "/groups",
    response_model=ProjectGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def create_project_group(
    payload: ProjectGroupCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forms a new student collaboration project group within a cohort batch."""
    group = await ProjectGroupService.create_group(
        db=db,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.get(
    "/groups",
    response_model=ProjectGroupPaginatedResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def list_project_groups(
    batch_id: Optional[uuid.UUID] = Query(None, description="Filter by cohort batch"),
    group_status: Optional[str] = Query(None, description="Filter by group status"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project specification"),
    search: Optional[str] = Query(None, description="Search by group name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lists project groups with filters and pagination."""
    items, total, total_pages = await ProjectGroupService.list_groups(
        db=db,
        batch_id=batch_id,
        group_status=group_status,
        project_id=project_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ProjectGroupPaginatedResponse(
        items=[_to_group_list_item(g) for g in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/groups/{group_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def get_project_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetches complete project group details, active members, and batch assignment."""
    group = await ProjectGroupService.get_group(db, group_id)
    return _to_group_response(group)


@router.patch(
    "/groups/{group_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def update_project_group(
    group_id: uuid.UUID,
    payload: ProjectGroupUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates group parameters or status transitions."""
    group = await ProjectGroupService.update_group(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.post(
    "/groups/{group_id}/members",
    response_model=ProjectGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def add_group_member(
    group_id: uuid.UUID,
    payload: GroupMemberAddRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adds an eligible enrolled candidate to a collaboration group."""
    group = await ProjectGroupService.add_member(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.delete(
    "/groups/{group_id}/members/{candidate_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def remove_group_member(
    group_id: uuid.UUID,
    candidate_id: uuid.UUID,
    request: Request,
    override: bool = Query(False, description="Administrative override for minimum team size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Removes a candidate from a project group while enforcing minimum capacity."""
    group = await ProjectGroupService.remove_member(
        db=db,
        group_id=group_id,
        candidate_id=candidate_id,
        override=override,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.patch(
    "/groups/{group_id}/leader/{candidate_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def assign_group_leader(
    group_id: uuid.UUID,
    candidate_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Designates an active candidate as the team leader."""
    group = await ProjectGroupService.assign_leader(
        db=db,
        group_id=group_id,
        candidate_id=candidate_id,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetches full project specification including all milestone stages."""
    project = await ProjectService.get_project(db, project_id)
    return _to_project_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates project specification details, rubrics, or active status."""
    project = await ProjectService.update_project(
        db=db,
        project_id=project_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_project_response(project)


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def add_project_milestone(
    project_id: uuid.UUID,
    payload: MilestoneCreateItem,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Adds a sequential milestone deliverable stage to a project specification."""
    milestone = await ProjectService.add_milestone(
        db=db,
        project_id=project_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_milestone_response(milestone)


@router.patch(
    "/{project_id}/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    dependencies=[Depends(require_permission("project:catalog_manage"))],
)
async def update_project_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    payload: MilestoneUpdateItem,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates a milestone deliverable stage description, weight, or score."""
    milestone = await ProjectService.update_milestone(
        db=db,
        project_id=project_id,
        milestone_id=milestone_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_milestone_response(milestone)
