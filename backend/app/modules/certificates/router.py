"""
ExcelR Track360 - Certificate Management API Router
Domain 6: Credentials, Two-Stage Approvals, Dynamic QR Verification, and PDF Generation.
Strictly adheres to DBS-TRK360-V1.0, BR-CERT-01, BR-CERT-02, and SEC-CERT-01.
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.candidates.models import Candidate
from app.modules.certificates.models import CertificateRecord
from app.modules.certificates.schemas import (
    CertificateIssueRequest,
    CertificateReviewRequest,
    CertificateApprovalRequest,
    CertificateRevokeRequest,
    CertificateResponse,
    CertificateApprovalItem,
    CertificateRevocationItem,
    CertificatePublicVerifyResponse,
    CertificateListResponse,
    CertificateEligibilityDiagnostic,
)
from app.modules.certificates.service import CertificateService

router = APIRouter(prefix="/certificates", tags=["Certificates"])


def _to_certificate_response(c: CertificateRecord) -> CertificateResponse:
    approvals = [
        CertificateApprovalItem(
            id=a.id,
            certificate_id=a.certificate_id,
            approver_id=a.approver_id,
            approver_name=f"{a.approver.first_name} {a.approver.last_name}".strip() if a.approver else None,
            approver_email=a.approver.email if a.approver else None,
            stage=a.stage,
            decision=a.decision,
            decision_notes=a.decision_notes,
            decided_at_utc=a.decided_at_utc,
        )
        for a in (c.approvals or [])
    ]
    revocations = [
        CertificateRevocationItem(
            id=r.id,
            certificate_id=r.certificate_id,
            revoked_by_id=r.revoked_by_id,
            revoker_name=f"{r.revoker.first_name} {r.revoker.last_name}".strip() if r.revoker else None,
            revoker_email=r.revoker.email if r.revoker else None,
            reason_category=r.reason_category,
            detailed_reason=r.detailed_reason,
            revoked_at_utc=r.revoked_at_utc,
        )
        for r in (c.revocations or [])
    ]
    return CertificateResponse(
        id=c.id,
        candidate_id=c.candidate_id,
        candidate_display_name=c.candidate_display_name,
        track_id=c.track_id,
        course_display_title=c.course_display_title,
        internship_record_id=c.internship_record_id,
        serial_number=c.serial_number,
        certificate_type=c.certificate_type,
        milestone_level=c.milestone_level,
        accredited_duration_months=c.accredited_duration_months,
        issue_date=c.issue_date,
        verification_hash=c.verification_hash,
        verification_qr_url=c.verification_qr_url,
        status=c.status,
        pdf_file_asset_id=c.pdf_file_asset_id,
        requested_by_id=c.requested_by_id,
        requested_at=c.requested_at,
        stage1_reviewer_id=c.stage1_reviewer_id,
        stage1_reviewed_at=c.stage1_reviewed_at,
        stage1_notes=c.stage1_notes,
        stage2_approver_id=c.stage2_approver_id,
        stage2_approved_at=c.stage2_approved_at,
        stage2_notes=c.stage2_notes,
        issued_at_utc=c.issued_at_utc,
        revoked_by_id=c.revoked_by_id,
        revoked_at=c.revoked_at,
        revocation_category=c.revocation_category,
        revocation_reason=c.revocation_reason,
        created_at=c.created_at,
        updated_at=c.updated_at,
        approvals=approvals,
        revocations=revocations,
    )


# ============================================================================
# 1. PUBLIC VERIFICATION ENDPOINT (No Authentication Required)
# ============================================================================
@router.get(
    "/public-verify/{identifier}",
    response_model=CertificatePublicVerifyResponse,
    summary="Publicly verify certificate authenticity by serial number or hash",
)
async def verify_certificate_public(
    identifier: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Publicly accessible verification portal endpoint (FR-CER-005).
    Requires zero authentication.
    Returns authentic cryptographic verification state, candidate name, track, and duration.
    """
    return await CertificateService.verify_certificate_public(db, identifier)


# ============================================================================
# 2. PREREQUISITE ELIGIBILITY DIAGNOSTICS (BR-CERT-01)
# ============================================================================
@router.get(
    "/eligibility/{candidate_id}",
    response_model=CertificateEligibilityDiagnostic,
    summary="Check prerequisite completion & calculate eligibility diagnostic",
)
async def check_certificate_eligibility(
    candidate_id: uuid.UUID,
    track_id: Optional[uuid.UUID] = Query(None, description="Optional track ID override"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates 100% assignment passing, project milestone achievements, and internship completion.
    Enforces student isolation: students can only query their own diagnostic.
    """
    user_roles = {r.code for r in current_user.roles}
    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        c_res = await db.execute(select(Candidate).where(Candidate.user_id == current_user.id))
        student_candidate = c_res.scalar_one_or_none()
        if not student_candidate or student_candidate.id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Students may only inspect their own certificate eligibility diagnostic.",
            )

    return await CertificateService.calculate_candidate_eligibility(
        db=db,
        candidate_id=candidate_id,
        track_id=track_id,
    )


# ============================================================================
# 3. STAGE 0: INITIATE CERTIFICATE REQUEST
# ============================================================================
@router.post(
    "",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new certificate issuance request",
)
async def initiate_certificate(
    payload: CertificateIssueRequest,
    current_user: User = Depends(
        require_role(
            "ROLE_SUPER_ADMIN",
            "ROLE_OPS_ADMIN",
            "ROLE_CAN_COORD",
            "ROLE_PRJ_COORD",
            "ROLE_INT_COORD",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a new certificate issuance request into the approval pipeline.
    Validates candidate eligibility and provisions cryptographically unique serial ID.
    """
    user_roles = {r.code for r in current_user.roles}
    is_super_admin = "ROLE_SUPER_ADMIN" in user_roles
    record = await CertificateService.initiate_certificate_request(
        db=db,
        payload=payload,
        actor_user=current_user,
        is_admin_override=is_super_admin,
    )
    return _to_certificate_response(record)


# ============================================================================
# 4. STAGE 1: COORDINATOR REVIEW
# ============================================================================
@router.post(
    "/{id}/review",
    response_model=CertificateResponse,
    summary="Stage 1: Coordinator review of candidate credentials",
)
async def review_certificate_stage1(
    id: uuid.UUID,
    payload: CertificateReviewRequest,
    current_user: User = Depends(
        require_role(
            "ROLE_SUPER_ADMIN",
            "ROLE_OPS_ADMIN",
            "ROLE_INT_COORD",
            "ROLE_PRJ_COORD",
            "ROLE_CAN_COORD",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Stage 1 review by an authorized Coordinator.
    Advances certificate to REVIEWED or sets REJECTED.
    """
    record = await CertificateService.review_certificate_stage1(
        db=db,
        certificate_id=id,
        payload=payload,
        actor_user=current_user,
    )
    return _to_certificate_response(record)


# ============================================================================
# 5. STAGE 2: FORMAL APPROVER / DIRECTOR SIGN-OFF
# ============================================================================
@router.post(
    "/{id}/approve",
    response_model=CertificateResponse,
    summary="Stage 2: Formal approver sign-off & automated PDF/QR generation",
)
async def approve_certificate_stage2(
    id: uuid.UUID,
    payload: CertificateApprovalRequest,
    allow_override: bool = Query(False, description="Super Admin SoD override flag"),
    current_user: User = Depends(
        require_role(
            "ROLE_SUPER_ADMIN",
            "ROLE_CERT_APPROVER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Stage 2 formal sign-off.
    Enforces Separation of Duties (SoD) against the initiator/reviewer.
    Generates official high-resolution PDF certificate with dynamic QR code.
    """
    user_roles = [r.code for r in current_user.roles]
    record = await CertificateService.approve_certificate_stage2(
        db=db,
        certificate_id=id,
        payload=payload,
        actor_user=current_user,
        user_roles=user_roles,
        allow_override=allow_override,
    )
    return _to_certificate_response(record)


# ============================================================================
# 6. REVOCATION ENGINE
# ============================================================================
@router.post(
    "/{id}/revoke",
    response_model=CertificateResponse,
    summary="Revoke an issued certificate credential",
)
async def revoke_certificate(
    id: uuid.UUID,
    payload: CertificateRevokeRequest,
    current_user: User = Depends(
        require_role(
            "ROLE_SUPER_ADMIN",
            "ROLE_CERT_APPROVER",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Authorized revocation of an authentic certificate.
    Immediately updates public verification registry status to REVOKED.
    """
    record = await CertificateService.revoke_certificate(
        db=db,
        certificate_id=id,
        payload=payload,
        actor_user=current_user,
    )
    return _to_certificate_response(record)


# ============================================================================
# 7. DIRECTORY & RECORD RETRIEVAL (With Student IDOR Protection)
# ============================================================================
@router.get(
    "",
    response_model=CertificateListResponse,
    summary="List certificate records with role-based filtering",
)
async def list_certificates(
    candidate_id: Optional[uuid.UUID] = Query(None),
    track_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists certificates with support for search, status, and track filtering.
    Enforces student isolation: students can only see their own ISSUED certificates.
    """
    user_roles = {r.code for r in current_user.roles}

    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        c_res = await db.execute(select(Candidate).where(Candidate.user_id == current_user.id))
        student_candidate = c_res.scalar_one_or_none()
        if not student_candidate:
            return CertificateListResponse(items=[], total=0, page=page, page_size=page_size)

        candidate_id = student_candidate.id
        status_filter = "ISSUED"  # Students cannot see drafts or pending reviews

    items, total = await CertificateService.list_certificates(
        db=db,
        candidate_id=candidate_id,
        track_id=track_id,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )

    return CertificateListResponse(
        items=[_to_certificate_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{id}",
    response_model=CertificateResponse,
    summary="Get single certificate detail by ID",
)
async def get_certificate_detail(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches full certificate detail including approvals and revocations history.
    Enforces student isolation.
    """
    cert = await CertificateService.get_certificate(db, id)
    user_roles = {r.code for r in current_user.roles}

    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        c_res = await db.execute(select(Candidate).where(Candidate.user_id == current_user.id))
        student_candidate = c_res.scalar_one_or_none()
        if not student_candidate or cert.candidate_id != student_candidate.id or cert.status != "ISSUED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to view this certificate record.",
            )

    return _to_certificate_response(cert)


# ============================================================================
# 8. DOWNLOAD ARTIFACT PDF
# ============================================================================
@router.get(
    "/{id}/pdf",
    summary="Download certificate artifact PDF with embedded QR code",
)
async def download_certificate_pdf(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams official certificate PDF file.
    Enforces student isolation: students can only download their own issued certificates.
    """
    cert = await CertificateService.get_certificate(db, id)
    user_roles = {r.code for r in current_user.roles}

    if "ROLE_STUDENT" in user_roles and len(user_roles) == 1:
        c_res = await db.execute(select(Candidate).where(Candidate.user_id == current_user.id))
        student_candidate = c_res.scalar_one_or_none()
        if not student_candidate or cert.candidate_id != student_candidate.id or cert.status != "ISSUED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to download this certificate PDF.",
            )

    pdf_bytes, filename = await CertificateService.get_certificate_pdf_bytes(db, id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
