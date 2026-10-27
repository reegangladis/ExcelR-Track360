"""
ExcelR Track360 - Assignment Management API Router
Endpoints for assignment catalogue, rubrics, and cohort/candidate allocations.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission, get_current_user
from app.modules.auth.models import User
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse,
    AssignmentPaginatedResponse,
    AllocationCreateRequest,
    AllocationResponse,
    AllocationPaginatedResponse,
)
from app.modules.assignments.service import AssignmentService

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _to_assignment_response(assignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=assignment.id,
        track_id=assignment.track_id,
        code=assignment.code,
        title=assignment.title,
        instructions_markdown=assignment.instructions_markdown,
        sequence_order=assignment.sequence_order,
        is_mandatory=assignment.is_mandatory,
        max_score=float(assignment.max_score),
        passing_score=float(assignment.passing_score),
        rubric_template=assignment.rubric_template,
        allowed_file_types=assignment.allowed_file_types,
        max_file_size_mb=assignment.max_file_size_mb,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        track_name=assignment.track.title if assignment.track else None,
    )


def _to_allocation_response(allocation) -> AllocationResponse:
    cand_name = None
    if allocation.candidate:
        cand_name = f"{allocation.candidate.first_name} {allocation.candidate.last_name}"

    return AllocationResponse(
        id=allocation.id,
        assignment_id=allocation.assignment_id,
        assignment_code=allocation.assignment.code if allocation.assignment else "",
        assignment_title=allocation.assignment.title if allocation.assignment else "",
        batch_id=allocation.batch_id,
        batch_code=allocation.batch.batch_code if allocation.batch else None,
        candidate_id=allocation.candidate_id,
        candidate_name=cand_name,
        due_date_utc=allocation.due_date_utc,
        grace_period_end_utc=allocation.grace_period_end_utc,
        allocation_status=allocation.allocation_status,
        created_at=allocation.created_at,
    )


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("assignment:template_manage"))],
)
async def create_assignment(
    payload: AssignmentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new assignment template with rubric definition and score rules."""
    assignment = await AssignmentService.create_assignment(
        db=db,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_assignment_response(assignment)


@router.get(
    "",
    response_model=AssignmentPaginatedResponse,
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def list_assignments(
    track_id: Optional[uuid.UUID] = Query(None, description="Filter by course track"),
    search: Optional[str] = Query(None, description="Search by code or title"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List assignment templates with pagination and search."""
    items, total, total_pages = await AssignmentService.list_assignments(
        db=db,
        track_id=track_id,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return AssignmentPaginatedResponse(
        items=[_to_assignment_response(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/allocations",
    response_model=AllocationPaginatedResponse,
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def list_allocations(
    assignment_id: Optional[uuid.UUID] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    candidate_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List assignment allocations to batches or candidates."""
    items, total, total_pages = await AssignmentService.list_allocations(
        db=db,
        assignment_id=assignment_id,
        batch_id=batch_id,
        candidate_id=candidate_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return AllocationPaginatedResponse(
        items=[_to_allocation_response(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full assignment specification and rubric template."""
    assignment = await AssignmentService.get_assignment(db, assignment_id)
    return _to_assignment_response(assignment)


@router.patch(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    dependencies=[Depends(require_permission("assignment:template_manage"))],
)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update assignment details, rubrics, scores, or active status."""
    assignment = await AssignmentService.update_assignment(
        db=db,
        assignment_id=assignment_id,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_assignment_response(assignment)


@router.post(
    "/allocations",
    response_model=AllocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("assignment:allocate"))],
)
async def create_allocation(
    payload: AllocationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allocate an assignment to an entire cohort batch or an individual candidate."""
    allocation = await AssignmentService.create_allocation(
        db=db,
        payload=payload,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_allocation_response(allocation)
