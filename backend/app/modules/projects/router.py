"""
ExcelR Track360 - Projects Domain API Router
Phase 8: Project Catalog, Milestones, and Capstone Deliverables
Strictly complies with URP-TRK360-V1.0 specifications.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_permission
from app.modules.auth.models import User
from app.modules.projects.models import (
    Project,
    ProjectMilestone,
    ProjectGroup,
    ProjectGroupMember,
    ProjectGroupSubmission,
    ProjectProgressionRequest,
    ProjectAllocation,
)
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
    MentorAssignRequest,
    ProjectAllocationRequest,
    ProjectGroupSubmissionCreate,
    ProjectGroupSubmissionReviewRequest,
    ProjectGroupSubmissionResponse,
    ProjectProgressionRequestCreate,
    GroupReadinessResponse,
    GroupAdvanceRequest,
    ProjectQueuePaginatedResponse,
    ProjectDropRequest,
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
    mentor_name = g.mentor.full_name if g.mentor else None
    milestone_title = g.current_milestone.title if g.current_milestone else None
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
        mentor_id=g.mentor_id,
        mentor_name=mentor_name,
        current_milestone_id=g.current_milestone_id,
        current_milestone_title=milestone_title,
        readiness_status=g.readiness_status,
        allocated_at=g.allocated_at,
        completed_at=g.completed_at,
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
    mentor_name = g.mentor.full_name if g.mentor else None
    return ProjectGroupListItem(
        id=g.id,
        batch_id=g.batch_id,
        batch_code=g.batch.batch_code if g.batch else None,
        project_id=g.project_id,
        project_code=g.project.code if g.project else None,
        project_title=g.project.title if g.project else None,
        group_name=g.group_name,
        group_status=g.group_status,
        readiness_status=g.readiness_status,
        mentor_name=mentor_name,
        member_count=len(active_m),
        min_size=g.min_size,
        target_size=g.target_size,
        max_size=g.max_size,
        created_at=g.created_at,
    )


def _to_submission_response(s: ProjectGroupSubmission) -> ProjectGroupSubmissionResponse:
    return ProjectGroupSubmissionResponse(
        id=s.id,
        group_id=s.group_id,
        project_id=s.project_id,
        project_title=s.project.title if s.project else None,
        milestone_id=s.milestone_id,
        milestone_title=s.milestone.title if s.milestone else None,
        submitted_by_id=s.submitted_by_id,
        submitted_by_name=f"{s.submitted_by.first_name} {s.submitted_by.last_name}" if s.submitted_by else None,
        attempt_number=s.attempt_number,
        repo_url=s.repo_url,
        live_demo_url=s.live_demo_url,
        documentation_url=s.documentation_url,
        file_asset_id=s.file_asset_id,
        notes=s.notes,
        status=s.status,
        score=float(s.score) if s.score is not None else None,
        rubric_scores=s.rubric_scores or [],
        feedback=s.feedback,
        reviewed_by_id=s.reviewed_by_id,
        reviewed_by_name=s.reviewed_by.full_name if s.reviewed_by else None,
        submitted_at=s.submitted_at,
        reviewed_at=s.reviewed_at,
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
    "/queue",
    response_model=ProjectQueuePaginatedResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def get_project_allocation_queue(
    track_id: Optional[uuid.UUID] = Query(None, description="Filter queue by course track"),
    batch_id: Optional[uuid.UUID] = Query(None, description="Filter queue by cohort batch"),
    only_overdue: bool = Query(False, description="Filter only learners exceeding 15 business days"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the project allocation queue for eligible candidates awaiting project placement.
    Includes 15-business-day target tracking (excluding weekends) and overdue flags (BRD Part 7).
    """
    return await ProjectGroupService.get_project_queue(
        db=db,
        track_id=track_id,
        batch_id=batch_id,
        only_overdue=only_overdue,
        page=page,
        page_size=page_size,
    )


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
    reason: Optional[str] = Query(None, description="Reason for member removal / reconstitution"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Removes a candidate from a project group and immediately recalculates readiness (AC-GRP-003)."""
    group = await ProjectGroupService.remove_member(
        db=db,
        group_id=group_id,
        candidate_id=candidate_id,
        override=override,
        reason=reason,
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


# ==============================================================
# Phase 10: Project Allocation & Group Completion Endpoints
# ==============================================================

@router.put(
    "/groups/{group_id}/mentor",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def assign_group_mentor(
    group_id: uuid.UUID,
    payload: MentorAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assigns an authoritative staff mentor/evaluator to a project group."""
    group = await ProjectGroupService.assign_mentor(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.post(
    "/groups/{group_id}/allocate-project",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def allocate_project_to_group(
    group_id: uuid.UUID,
    payload: ProjectAllocationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allocates a project specification to a project group.
    Enforces dynamic group sizing, course track matching, single active project, max 3 projects cap,
    and 100% prerequisite mandatory assignment completion (or waiver with justification).
    """
    group = await ProjectGroupService.allocate_project(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.post(
    "/groups/{group_id}/allocations/{allocation_id}/drop",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def drop_project_allocation(
    group_id: uuid.UUID,
    allocation_id: uuid.UUID,
    payload: ProjectDropRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks an allocated project as DROPPED with a mandatory coordinator reason (BRD Part 7).
    Preserves historical record, does not award completion credit, and logs audit trail.
    """
    group = await ProjectGroupService.drop_project_allocation(
        db=db,
        group_id=group_id,
        allocation_id=allocation_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_group_response(group)


@router.post(
    "/groups/{group_id}/submissions",
    response_model=ProjectGroupSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("candidate:profile_view"))],
)
async def submit_group_deliverable(
    group_id: uuid.UUID,
    payload: ProjectGroupSubmissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits group project deliverables (repository URL, demo URL, documentation, notes)."""
    sub = await ProjectGroupService.submit_deliverable(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_submission_response(sub)


@router.get(
    "/groups/{group_id}/submissions",
    response_model=List[ProjectGroupSubmissionResponse],
    dependencies=[Depends(require_permission("candidate:profile_view"))],
)
async def list_group_submissions(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lists deliverable submissions and review evaluations for a project group."""
    subs = await ProjectGroupService.list_submissions(db, group_id)
    return [_to_submission_response(s) for s in subs]


@router.post(
    "/groups/{group_id}/submissions/{submission_id}/review",
    response_model=ProjectGroupSubmissionResponse,
    dependencies=[Depends(require_permission("assignment:evaluate"))],
)
async def review_group_submission(
    group_id: uuid.UUID,
    submission_id: uuid.UUID,
    payload: ProjectGroupSubmissionReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reviews and evaluates a group deliverable with scores and rubric criteria."""
    sub = await ProjectGroupService.review_submission(
        db=db,
        group_id=group_id,
        submission_id=submission_id,
        payload=payload,
        reviewer_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_submission_response(sub)


@router.post(
    "/groups/{group_id}/progression-request",
    response_model=GroupReadinessResponse,
    dependencies=[Depends(require_permission("candidate:profile_view"))],
)
async def request_group_progression(
    group_id: uuid.UUID,
    payload: ProjectProgressionRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Individual candidate progression sign-off (BR-GRP-01 / AC-GRP-001)."""
    return await ProjectGroupService.request_progression(
        db=db,
        group_id=group_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/groups/{group_id}/readiness",
    response_model=GroupReadinessResponse,
    dependencies=[Depends(require_permission("candidate:profile_view"))],
)
async def get_group_readiness(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetches collaborative group readiness status, checklist, and pending candidate sign-offs."""
    return await ProjectGroupService.get_group_readiness(db, group_id)


@router.post(
    "/groups/{group_id}/advance",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_permission("project:group_manage"))],
)
async def advance_group_progression(
    group_id: uuid.UUID,
    payload: GroupAdvanceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Advances group to next project tier (Tier 1 -> Tier 2 -> Tier 3 Capstone -> Completed).
    Requires all active members to have requested, or coordinator override justification.
    """
    group = await ProjectGroupService.advance_group(
        db=db,
        group_id=group_id,
        payload=payload,
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
