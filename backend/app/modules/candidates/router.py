"""
ExcelR Track360 - Candidate & Cohort API Endpoints
Provides Candidate CRUD, search, filter, status transitions,
and preview-and-validate CSV bulk ingestion.
Enforces strict server-side authorization and IDOR protection.
"""
import csv
import io
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import (
    get_current_user,
    require_role,
    require_permission,
)
from app.modules.auth.models import User
from app.modules.candidates.models import Course, CourseTrack, Batch, Candidate, Enrollment
from app.modules.candidates.schemas import (
    CourseCreate,
    CourseResponse,
    CourseTrackCreate,
    CourseTrackResponse,
    BatchCreate,
    BatchResponse,
    CandidateCreate,
    CandidateUpdate,
    CandidateStatusTransitionRequest,
    CandidateResponse,
    CandidateMaskedResponse,
    CandidatePaginatedResponse,
    ImportPreviewResponse,
    ImportCommitRequest,
    ImportCommitResponse,
)
from app.modules.candidates.service import CandidateService

router = APIRouter()


def _extract_batch_code(candidate: Candidate) -> Optional[str]:
    """Safely extracts enrolled batch code if present."""
    try:
        if candidate.enrollments and len(candidate.enrollments) > 0:
            first_enrollment = candidate.enrollments[0]
            if hasattr(first_enrollment, "batch") and first_enrollment.batch:
                return first_enrollment.batch.batch_code
    except Exception:
        pass
    return None


# ==========================================
# Course & Cohort Master Endpoints
# ==========================================

@router.get("/courses", response_model=List[CourseResponse], summary="List Academic Courses")
async def list_courses(db: AsyncSession = Depends(get_db)):
    """Public list of active academic courses and tracks."""
    stmt = select(Course).where(Course.is_active == True)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/courses", response_model=CourseResponse, summary="Create Academic Course")
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new academic course (Super Admin / Ops Admin only)."""
    clean_code = payload.code.upper().strip()
    dup = (await db.execute(select(Course).where(Course.code == clean_code))).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail=f"Course with code '{clean_code}' already exists.")

    course = Course(code=clean_code, title=payload.title.strip(), description=payload.description)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.post("/courses/tracks", response_model=CourseTrackResponse, summary="Create Course Track")
async def create_course_track(
    payload: CourseTrackCreate,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Creates a specialization track under a course."""
    clean_code = payload.code.upper().strip()
    dup = (await db.execute(select(CourseTrack).where(CourseTrack.code == clean_code))).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail=f"Course track with code '{clean_code}' already exists.")

    track = CourseTrack(
        course_id=payload.course_id,
        code=clean_code,
        title=payload.title.strip(),
        total_mandatory_assignments=payload.total_mandatory_assignments,
        total_required_projects=payload.total_required_projects,
        duration_policy_config=payload.duration_policy_config,
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


@router.get("/batches", response_model=List[BatchResponse], summary="List Cohort Batches")
async def list_batches(db: AsyncSession = Depends(get_db)):
    """Lists cohort batches."""
    stmt = select(Batch).order_by(Batch.start_date.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.post("/batches", response_model=BatchResponse, summary="Create Cohort Batch")
async def create_batch(
    payload: BatchCreate,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new student cohort batch."""
    clean_code = payload.batch_code.upper().strip()
    dup = (await db.execute(select(Batch).where(Batch.batch_code == clean_code))).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail=f"Batch with code '{clean_code}' already exists.")

    batch = Batch(
        track_id=payload.track_id,
        batch_code=clean_code,
        title=payload.title.strip(),
        start_date=payload.start_date,
        expected_end_date=payload.expected_end_date,
        status=payload.status,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


# ==========================================
# Candidate Lifecycle Endpoints
# ==========================================

@router.get("/candidates", response_model=CandidatePaginatedResponse, summary="List & Search Candidates")
async def list_candidates(
    search: Optional[str] = Query(None, description="Search by name, email, phone, or candidate number"),
    lifecycle_status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ON_HOLD, etc.)"),
    batch_id: Optional[uuid.UUID] = Query(None, description="Filter by cohort batch ID"),
    project_eligible: Optional[bool] = Query(None, description="Filter by project eligibility"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_role(
        "ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD",
        "ROLE_ASG_REVIEWER", "ROLE_PRJ_COORD", "ROLE_INT_COORD",
        "ROLE_CERT_APPROVER", "ROLE_READ_ONLY"
    )),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated candidate registry query.
    Restricted to authorized staff roles. Students are strictly blocked from organization-wide lists.
    """
    service = CandidateService(db)
    items, total = await service.list_candidates(
        search=search,
        lifecycle_status=lifecycle_status,
        batch_id=batch_id,
        project_eligible=project_eligible,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # Map with enrolled batch code if present
    mapped_items = []
    for c in items:
        batch_code = _extract_batch_code(c)
        mapped_items.append(CandidateResponse(
            id=c.id,
            user_id=c.user_id,
            candidate_number=c.candidate_number,
            first_name=c.first_name,
            last_name=c.last_name,
            email=c.email,
            phone=c.phone,
            alternate_phone=c.alternate_phone,
            academic_qualification=c.academic_qualification,
            lifecycle_status=c.lifecycle_status,
            project_eligible=c.project_eligible,
            completed_projects_count=c.completed_projects_count,
            created_at=c.created_at,
            updated_at=c.updated_at,
            batch_code=batch_code,
        ))

    return CandidatePaginatedResponse(
        items=mapped_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/candidates", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED, summary="Create Candidate")
async def create_candidate(
    payload: CandidateCreate,
    request: Request,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD")),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new candidate record with duplicate prevention and audit logging."""
    ip = request.client.host if request.client else None
    service = CandidateService(db)
    candidate = await service.create_candidate(payload, actor_id=current_user.id, actor_ip=ip)

    batch_code = _extract_batch_code(candidate)
    return CandidateResponse(
        id=candidate.id,
        user_id=candidate.user_id,
        candidate_number=candidate.candidate_number,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        alternate_phone=candidate.alternate_phone,
        academic_qualification=candidate.academic_qualification,
        lifecycle_status=candidate.lifecycle_status,
        project_eligible=candidate.project_eligible,
        completed_projects_count=candidate.completed_projects_count,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        batch_code=batch_code,
    )


@router.get("/candidates/me", response_model=CandidateResponse, summary="Get Current Student Candidate Profile")
async def get_my_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Self-service endpoint for students to view their own profile."""
    service = CandidateService(db)
    candidate = await service.get_candidate_by_user_id(current_user.id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate record linked to the current user account.",
        )

    batch_code = _extract_batch_code(candidate)
    return CandidateResponse(
        id=candidate.id,
        user_id=candidate.user_id,
        candidate_number=candidate.candidate_number,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        alternate_phone=candidate.alternate_phone,
        academic_qualification=candidate.academic_qualification,
        lifecycle_status=candidate.lifecycle_status,
        project_eligible=candidate.project_eligible,
        completed_projects_count=candidate.completed_projects_count,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        batch_code=batch_code,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse, summary="Get Candidate Details")
async def get_candidate_details(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches candidate details.
    IDOR Protection: Students are strictly forbidden from accessing any candidate record other than their own.
    """
    user_roles = {r.code for r in current_user.roles}
    is_staff = bool(user_roles - {"ROLE_STUDENT"}) or "ROLE_SUPER_ADMIN" in user_roles

    service = CandidateService(db)
    candidate = await service.get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    # IDOR Check for students
    if not is_staff and candidate.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access another candidate's profile.",
        )

    batch_code = _extract_batch_code(candidate)
    return CandidateResponse(
        id=candidate.id,
        user_id=candidate.user_id,
        candidate_number=candidate.candidate_number,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        alternate_phone=candidate.alternate_phone,
        academic_qualification=candidate.academic_qualification,
        lifecycle_status=candidate.lifecycle_status,
        project_eligible=candidate.project_eligible,
        completed_projects_count=candidate.completed_projects_count,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        batch_code=batch_code,
    )


@router.patch("/candidates/{candidate_id}", response_model=CandidateResponse, summary="Update Candidate Profile")
async def update_candidate_profile(
    candidate_id: uuid.UUID,
    payload: CandidateUpdate,
    request: Request,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD")),
    db: AsyncSession = Depends(get_db),
):
    """Updates candidate contact information and details (authorized staff only)."""
    ip = request.client.host if request.client else None
    service = CandidateService(db)
    candidate = await service.update_candidate(candidate_id, payload, actor_id=current_user.id, actor_ip=ip)

    batch_code = _extract_batch_code(candidate)
    return CandidateResponse(
        id=candidate.id,
        user_id=candidate.user_id,
        candidate_number=candidate.candidate_number,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        alternate_phone=candidate.alternate_phone,
        academic_qualification=candidate.academic_qualification,
        lifecycle_status=candidate.lifecycle_status,
        project_eligible=candidate.project_eligible,
        completed_projects_count=candidate.completed_projects_count,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        batch_code=batch_code,
    )


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateResponse, summary="Modify Candidate Lifecycle Status")
async def transition_candidate_status(
    candidate_id: uuid.UUID,
    payload: CandidateStatusTransitionRequest,
    request: Request,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD")),
    db: AsyncSession = Depends(get_db),
):
    """Executes a lifecycle status transition with mandatory reason logging."""
    ip = request.client.host if request.client else None
    service = CandidateService(db)
    candidate = await service.transition_status(candidate_id, payload, actor_id=current_user.id, actor_ip=ip)

    batch_code = _extract_batch_code(candidate)
    return CandidateResponse(
        id=candidate.id,
        user_id=candidate.user_id,
        candidate_number=candidate.candidate_number,
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        alternate_phone=candidate.alternate_phone,
        academic_qualification=candidate.academic_qualification,
        lifecycle_status=candidate.lifecycle_status,
        project_eligible=candidate.project_eligible,
        completed_projects_count=candidate.completed_projects_count,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        batch_code=batch_code,
    )


# ==========================================
# Bulk Candidate Ingestion Endpoints
# ==========================================

@router.post("/candidates/import/preview", response_model=ImportPreviewResponse, summary="Preview & Validate CSV Roster")
async def preview_candidates_import(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD")),
    db: AsyncSession = Depends(get_db),
):
    """
    Parses uploaded CSV and executes dry-run validation against database constraints.
    Returns row-by-row error reporting without committing records.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for roster ingestion.")

    content = await file.read()
    try:
        text_stream = io.StringIO(content.decode("utf-8-sig"))
        reader = csv.DictReader(text_stream)
        raw_rows = [row for row in reader]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(exc)}")

    if not raw_rows:
        raise HTTPException(status_code=400, detail="Uploaded CSV file contains no data rows.")

    service = CandidateService(db)
    return await service.preview_csv_import(raw_rows)


@router.post("/candidates/import/commit", response_model=ImportCommitResponse, summary="Commit Validated CSV Roster")
async def commit_candidates_import(
    payload: ImportCommitRequest,
    request: Request,
    current_user: User = Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD")),
    db: AsyncSession = Depends(get_db),
):
    """
    Persists validated rows into database with atomic transaction and audit trail.
    """
    ip = request.client.host if request.client else None
    service = CandidateService(db)
    return await service.commit_csv_import(payload, actor_id=current_user.id, actor_ip=ip)
