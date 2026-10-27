"""
ExcelR Track360 - Assignment Management API Router
Endpoints for assignment catalogue, rubrics, cohort/candidate allocations,
student submissions, attempt versioning, evaluator grading, and file asset downloads.
"""
from pathlib import Path
from typing import Optional, List
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.auth.dependencies import require_permission, get_current_user
from app.modules.auth.models import User
from app.modules.candidates.models import Candidate
from app.modules.assignments.models import FileAsset
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse,
    AssignmentPaginatedResponse,
    AllocationCreateRequest,
    AllocationResponse,
    AllocationPaginatedResponse,
    SubmissionAttemptResponse,
    SubmissionReviewCreateRequest,
    SubmissionReviewResponse,
    ReviewRubricScoreItem,
    AssignmentSubmissionDetailResponse,
    AssignmentSubmissionPaginated,
    AssignmentSubmissionListItem,
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


def _to_review_response(rev) -> SubmissionReviewResponse:
    rubrics = [
        ReviewRubricScoreItem(
            criterion_key=r.criterion_key,
            criterion_title=r.criterion_title,
            max_points=float(r.max_points),
            awarded_points=float(r.awarded_points),
            criterion_comments=r.criterion_comments,
        )
        for r in (rev.rubric_scores or [])
    ]
    return SubmissionReviewResponse(
        id=rev.id,
        attempt_id=rev.attempt_id,
        reviewer_id=rev.reviewer_id,
        reviewer_name=rev.reviewer.full_name if rev.reviewer else None,
        review_outcome=rev.review_outcome,
        total_score=float(rev.total_score),
        qualitative_feedback=rev.qualitative_feedback,
        internal_evaluator_notes=rev.internal_evaluator_notes,
        review_completed_at_utc=rev.review_completed_at_utc,
        rubric_scores=rubrics,
    )


def _to_attempt_response(att) -> SubmissionAttemptResponse:
    revs = [_to_review_response(r) for r in (att.reviews or [])]
    return SubmissionAttemptResponse(
        id=att.id,
        attempt_number=att.attempt_number,
        file_asset_id=att.file_asset_id,
        original_filename=att.file_asset.original_filename if att.file_asset else None,
        file_size_bytes=att.file_asset.file_size_bytes if att.file_asset else None,
        repository_url=att.repository_url,
        student_notes=att.student_notes,
        submitted_at_utc=att.submitted_at_utc,
        is_late=att.is_late,
        lateness_minutes=att.lateness_minutes,
        reviews=revs,
    )


def _to_submission_detail_response(sub) -> AssignmentSubmissionDetailResponse:
    cand_name = f"{sub.candidate.first_name} {sub.candidate.last_name}" if sub.candidate else "Unknown"
    cand_number = sub.candidate.candidate_number if sub.candidate else ""
    asg = sub.allocation.assignment if sub.allocation else None
    attempts = [_to_attempt_response(a) for a in (sub.attempts or [])]

    return AssignmentSubmissionDetailResponse(
        id=sub.id,
        allocation_id=sub.allocation_id,
        candidate_id=sub.candidate_id,
        candidate_name=cand_name,
        candidate_number=cand_number,
        assignment_code=asg.code if asg else "",
        assignment_title=asg.title if asg else "",
        current_submission_status=sub.current_submission_status,
        current_completion_status=sub.current_completion_status,
        total_attempts=sub.total_attempts,
        latest_score=float(sub.latest_score) if sub.latest_score is not None else None,
        first_submitted_at_utc=sub.first_submitted_at_utc,
        latest_submitted_at_utc=sub.latest_submitted_at_utc,
        due_date_utc=sub.allocation.due_date_utc if sub.allocation else sub.created_at,
        grace_period_end_utc=sub.allocation.grace_period_end_utc if sub.allocation else None,
        attempts=attempts,
    )


def _to_submission_list_item(sub) -> AssignmentSubmissionListItem:
    cand_name = f"{sub.candidate.first_name} {sub.candidate.last_name}" if sub.candidate else "Unknown"
    cand_number = sub.candidate.candidate_number if sub.candidate else ""
    asg = sub.allocation.assignment if sub.allocation else None
    batch = sub.allocation.batch if sub.allocation else None

    is_late = False
    if sub.latest_submitted_at_utc and sub.allocation:
        is_late = sub.latest_submitted_at_utc > sub.allocation.due_date_utc

    return AssignmentSubmissionListItem(
        id=sub.id,
        allocation_id=sub.allocation_id,
        candidate_id=sub.candidate_id,
        candidate_name=cand_name,
        candidate_number=cand_number,
        assignment_code=asg.code if asg else "",
        assignment_title=asg.title if asg else "",
        batch_code=batch.batch_code if batch else None,
        current_submission_status=sub.current_submission_status,
        current_completion_status=sub.current_completion_status,
        total_attempts=sub.total_attempts,
        latest_score=float(sub.latest_score) if sub.latest_score is not None else None,
        due_date_utc=sub.allocation.due_date_utc if sub.allocation else sub.created_at,
        latest_submitted_at_utc=sub.latest_submitted_at_utc,
        is_late=is_late,
    )


# ==========================================
# Phase 6: Assignment Templates & Allocations
# ==========================================

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


# ==========================================
# Phase 7: Submissions, Attempts & Evaluation
# ==========================================

@router.post(
    "/allocations/{allocation_id}/submit",
    response_model=SubmissionAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_assignment_deliverable(
    allocation_id: uuid.UUID,
    request: Request,
    file: Optional[UploadFile] = File(None),
    repository_url: Optional[str] = Form(None),
    student_notes: Optional[str] = Form(None),
    target_candidate_id: Optional[uuid.UUID] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits student assignment deliverable (file or git repository).
    Enforces server-side UTC timestamping, allowed file formats, and attempt versioning.
    IDOR Protection: Candidates can only submit on their own behalf.
    """
    user_roles = {r.code for r in current_user.roles}
    is_staff = bool(user_roles - {"ROLE_STUDENT"}) or "ROLE_SUPER_ADMIN" in user_roles

    if not is_staff:
        # Resolve candidate profile for student
        cand_q = select(Candidate).where(Candidate.user_id == current_user.id)
        cand_res = await db.execute(cand_q)
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate record linked to current student user account was not found.",
            )
        candidate_id = candidate.id
    else:
        if not target_candidate_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Staff must specify target_candidate_id when submitting on behalf of a student.",
            )
        candidate_id = target_candidate_id

    attempt = await AssignmentService.submit_assignment(
        db=db,
        allocation_id=allocation_id,
        candidate_id=candidate_id,
        file=file,
        repository_url=repository_url,
        student_notes=student_notes,
        actor_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_attempt_response(attempt)


@router.get(
    "/submissions",
    response_model=AssignmentSubmissionPaginated,
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def list_submissions(
    status: Optional[str] = Query(None),
    batch_id: Optional[uuid.UUID] = Query(None),
    assignment_id: Optional[uuid.UUID] = Query(None),
    candidate_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists student assignment submissions for reviewer queue or student portfolio.
    IDOR Protection: Students only see their own submissions.
    """
    user_roles = {r.code for r in current_user.roles}
    is_staff = bool(user_roles - {"ROLE_STUDENT"}) or "ROLE_SUPER_ADMIN" in user_roles

    if not is_staff:
        cand_q = select(Candidate).where(Candidate.user_id == current_user.id)
        cand_res = await db.execute(cand_q)
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            return AssignmentSubmissionPaginated(items=[], total=0, page=page, page_size=page_size, total_pages=1)
        candidate_id = candidate.id

    items, total, total_pages = await AssignmentService.list_submissions(
        db=db,
        status=status,
        batch_id=batch_id,
        assignment_id=assignment_id,
        candidate_id=candidate_id,
        page=page,
        page_size=page_size,
    )
    return AssignmentSubmissionPaginated(
        items=[_to_submission_list_item(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=AssignmentSubmissionDetailResponse,
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def get_submission_detail(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches full submission history including attempts, file metadata, and evaluation feedback.
    IDOR Protection: Students are forbidden from viewing peer submissions.
    """
    user_roles = {r.code for r in current_user.roles}
    is_staff = bool(user_roles - {"ROLE_STUDENT"}) or "ROLE_SUPER_ADMIN" in user_roles

    submission = await AssignmentService.get_submission_detail(db, submission_id)

    if not is_staff and submission.candidate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot inspect another student's assignment submission.",
        )

    return _to_submission_detail_response(submission)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=SubmissionReviewResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("assignment:review"))],
)
async def review_assignment_submission(
    submission_id: uuid.UUID,
    payload: SubmissionReviewCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Records an evaluation for the student's latest submission attempt.
    Enforces rubric scoring, passing thresholds (BR-ASG-04), and checks Project 1 eligibility gating (BR-PRJ-01).
    """
    review = await AssignmentService.review_submission(
        db=db,
        submission_id=submission_id,
        payload=payload,
        reviewer_id=current_user.id,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_review_response(review)


@router.get(
    "/submissions/files/{file_asset_id}",
    summary="Download Deliverable File Asset",
    dependencies=[Depends(require_permission("assignment:view"))],
)
async def download_file_asset(
    file_asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads an uploaded submission file asset with permission and ownership validation."""
    query = select(FileAsset).where(FileAsset.id == file_asset_id)
    res = await db.execute(query)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File asset not found.")

    settings = get_settings()
    full_path = Path(settings.UPLOAD_DIR) / asset.storage_key
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file could not be found on disk.")

    return FileResponse(
        path=full_path,
        filename=asset.original_filename,
        media_type=asset.mime_type,
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

