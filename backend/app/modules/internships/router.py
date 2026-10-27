"""
ExcelR Track360 - Internship Management API Router
Domain 5: Internship Tracking, Decoupled Calendar Dates & Accredited Duration Policies.
Strictly adheres to DBS-TRK360-V1.0, BR-INT-01, and BR-INT-02.
"""
import uuid
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.candidates.models import Candidate
from app.modules.internships.models import InternshipRecord, InternshipMilestone
from app.modules.internships.schemas import (
    InternshipCreateRequest,
    InternshipUpdateRequest,
    InternshipCompleteRequest,
    InternshipTerminateRequest,
    InternshipMilestoneItem,
    InternshipResponse,
    InternshipListItem,
    InternshipPaginatedResponse,
    CandidateInternshipEligibilityResponse,
)
from app.modules.internships.service import InternshipService

router = APIRouter(prefix="/internships", tags=["Internships"])


def _to_milestone_item(m: InternshipMilestone) -> InternshipMilestoneItem:
    return InternshipMilestoneItem(
        id=m.id,
        milestone_tier=m.milestone_tier,
        title=m.title,
        project_id=m.project_id,
        project_title=m.project.title if m.project else None,
        accredited_months=m.accredited_months,
        status=m.status,
        achieved_at=m.achieved_at,
        verified_by_name=m.verified_by.full_name if m.verified_by else None,
        notes=m.notes,
    )


def _to_internship_response(r: InternshipRecord) -> InternshipResponse:
    return InternshipResponse(
        id=r.id,
        candidate_id=r.candidate_id,
        candidate_number=r.candidate.candidate_number if r.candidate else None,
        candidate_name=r.candidate.full_name if r.candidate else None,
        candidate_email=r.candidate.email if r.candidate else None,
        track_id=r.track_id,
        track_code=r.track.code if r.track else None,
        track_title=r.track.title if r.track else None,
        start_date=r.start_date,
        expected_end_date=r.expected_end_date,
        actual_completion_date=r.actual_completion_date,
        accredited_duration_months=r.accredited_duration_months,
        internship_status=r.internship_status,
        company_name=r.company_name,
        coordinator_notes=r.coordinator_notes,
        milestones=[_to_milestone_item(m) for m in r.milestones],
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _to_list_item(r: InternshipRecord) -> InternshipListItem:
    return InternshipListItem(
        id=r.id,
        candidate_id=r.candidate_id,
        candidate_number=r.candidate.candidate_number if r.candidate else None,
        candidate_name=r.candidate.full_name if r.candidate else None,
        candidate_email=r.candidate.email if r.candidate else None,
        track_id=r.track_id,
        track_code=r.track.code if r.track else None,
        track_title=r.track.title if r.track else None,
        start_date=r.start_date,
        expected_end_date=r.expected_end_date,
        actual_completion_date=r.actual_completion_date,
        accredited_duration_months=r.accredited_duration_months,
        internship_status=r.internship_status,
        company_name=r.company_name,
        created_at=r.created_at,
    )


@router.get("", response_model=InternshipPaginatedResponse)
async def list_internships(
    track_id: Optional[uuid.UUID] = Query(None),
    candidate_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(
            "ROLE_SUPER_ADMIN",
            "ROLE_OPS_ADMIN",
            "ROLE_CAN_COORD",
            "ROLE_PRJ_COORD",
            "ROLE_INT_COORD",
            "ROLE_CERT_APPROVER",
            "ROLE_READ_ONLY",
        )
    ),
):
    """Lists candidate internship records with multi-criteria filtering and search."""
    records, total = await InternshipService.list_internships(
        db=db,
        track_id=track_id,
        candidate_id=candidate_id,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return InternshipPaginatedResponse(
        items=[_to_list_item(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=InternshipResponse, status_code=status.HTTP_201_CREATED)
async def initialize_internship(
    payload: InternshipCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_INT_COORD")
    ),
):
    """Initializes formal candidate internship record (WF-07)."""
    record = await InternshipService.initialize_internship(
        db=db,
        payload=payload,
        actor_user=current_user,
    )
    return _to_internship_response(record)


@router.get("/candidates/{candidate_id}/eligibility", response_model=CandidateInternshipEligibilityResponse)
async def check_candidate_eligibility(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Checks candidate internship readiness and recommended accredited duration."""
    # Student IDOR check
    user_roles = {r.code for r in current_user.roles}
    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        candidate = await db.get(Candidate, candidate_id)
        if not candidate or (candidate.user_id != current_user.id and candidate.email != current_user.email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Students can only inspect their own internship eligibility.",
            )

    return await InternshipService.calculate_candidate_eligibility(db, candidate_id)


@router.get("/candidates/{candidate_id}", response_model=Optional[InternshipResponse])
async def get_candidate_internship(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches candidate's active or latest internship record."""
    # Student IDOR check
    user_roles = {r.code for r in current_user.roles}
    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        candidate = await db.get(Candidate, candidate_id)
        if not candidate or (candidate.user_id != current_user.id and candidate.email != current_user.email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Students can only view their own internship record.",
            )

    record = await InternshipService.get_internship_by_candidate(db, candidate_id)
    return _to_internship_response(record) if record else None


@router.get("/{record_id}", response_model=InternshipResponse)
async def get_internship_detail(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detailed view of an internship record including sequential milestones."""
    record = await InternshipService.get_internship(db, record_id)

    # Student IDOR check
    user_roles = {r.code for r in current_user.roles}
    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        if not record.candidate or (
            record.candidate.user_id != current_user.id and record.candidate.email != current_user.email
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Students can only view their own internship record.",
            )

    return _to_internship_response(record)


@router.patch("/{record_id}", response_model=InternshipResponse)
async def update_internship(
    record_id: uuid.UUID,
    payload: InternshipUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_INT_COORD")
    ),
):
    """Updates operational calendar dates or company mapping (BR-INT-01)."""
    record = await InternshipService.update_internship(
        db=db,
        record_id=record_id,
        payload=payload,
        actor_user=current_user,
    )
    return _to_internship_response(record)


@router.post("/{record_id}/complete", response_model=InternshipResponse)
async def complete_internship(
    record_id: uuid.UUID,
    payload: InternshipCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_INT_COORD")
    ),
):
    """Formally confirms verified completion of an internship record."""
    record = await InternshipService.complete_internship(
        db=db,
        record_id=record_id,
        payload=payload,
        actor_user=current_user,
    )
    return _to_internship_response(record)


@router.post("/{record_id}/terminate", response_model=InternshipResponse)
async def terminate_internship(
    record_id: uuid.UUID,
    payload: InternshipTerminateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_INT_COORD")
    ),
):
    """Terminates an internship with mandatory justification."""
    record = await InternshipService.terminate_internship(
        db=db,
        record_id=record_id,
        payload=payload,
        actor_user=current_user,
    )
    return _to_internship_response(record)


@router.post("/{record_id}/sync-duration", response_model=InternshipResponse)
async def sync_internship_duration(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_INT_COORD")
    ),
):
    """Recalculates accredited duration from candidate's latest approved projects (BR-INT-02)."""
    record = await InternshipService.sync_accredited_duration(
        db=db,
        record_id=record_id,
        actor_user=current_user,
    )
    return _to_internship_response(record)
