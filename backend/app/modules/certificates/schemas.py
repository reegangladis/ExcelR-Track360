"""
ExcelR Track360 - Certificate Management & Verification Engine Schemas
Pydantic v2 schemas for requests, responses, diagnostics, and public verification.
Strictly adheres to DBS-TRK360-V1.0, BR-CERT-01, BR-CERT-02, and SEC-CERT-01.
"""
import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CertificateEligibilityDiagnostic(BaseModel):
    """Prerequisite diagnostics for a candidate prior to certificate issuance."""
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_number: Optional[str] = None
    track_id: uuid.UUID
    track_title: str
    total_mandatory_assignments: int
    passed_mandatory_assignments: int
    assignments_completed: bool
    total_required_projects: int
    approved_project_milestones: int
    projects_completed: bool
    has_internship: bool
    internship_status: Optional[str] = None
    internship_completed: bool
    accredited_duration_months: int
    is_eligible: bool
    ineligibility_reasons: List[str]
    has_active_certificate: bool
    existing_certificate_id: Optional[uuid.UUID] = None
    existing_certificate_number: Optional[str] = None

    # Learnova Integration Compatibility Fields
    is_course_certificate_eligible: bool = False
    is_internship_certificate_eligible: bool = False
    mandatory_assignments_completed: bool = False
    nasscom_clearance_passed: bool = True
    completed_projects_count: int = 0
    internship_accredited_months: int = 0
    unmet_prerequisites: List[str] = Field(default_factory=list)


class CertificateIssueRequest(BaseModel):
    """Payload to initiate a new certificate request (Stage 0)."""
    candidate_id: uuid.UUID
    track_id: uuid.UUID
    internship_record_id: Optional[uuid.UUID] = None
    certificate_type: str = Field(default="FINAL_COMPREHENSIVE", pattern="^(FINAL_COMPREHENSIVE|MILESTONE)$")
    milestone_level: Optional[int] = Field(default=None, ge=1, le=5)
    issue_date: Optional[date] = None
    notes: Optional[str] = None


class CertificateReviewRequest(BaseModel):
    """Payload for Stage 1: Coordinator Review."""
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    decision_notes: Optional[str] = Field(default=None, max_length=1000)


class CertificateApprovalRequest(BaseModel):
    """Payload for Stage 2: Formal Approver / Director Sign-off."""
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    decision_notes: Optional[str] = Field(default=None, max_length=1000)


class CertificateRevokeRequest(BaseModel):
    """Payload to revoke an issued certificate."""
    reason_category: str = Field(
        pattern="^(ACADEMIC_MALPRACTICE|DATA_ENTRY_ERROR|DISCIPLINARY_ACTION|ADMINISTRATIVE_OVERRIDE)$"
    )
    detailed_reason: str = Field(min_length=10, max_length=2000)


class CertificateApprovalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    certificate_id: uuid.UUID
    approver_id: uuid.UUID
    approver_name: Optional[str] = None
    approver_email: Optional[str] = None
    stage: str
    decision: str
    decision_notes: Optional[str] = None
    decided_at_utc: datetime


class CertificateRevocationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    certificate_id: uuid.UUID
    revoked_by_id: uuid.UUID
    revoker_name: Optional[str] = None
    revoker_email: Optional[str] = None
    reason_category: str
    detailed_reason: str
    revoked_at_utc: datetime


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_display_name: str
    track_id: uuid.UUID
    course_display_title: str
    internship_record_id: Optional[uuid.UUID] = None
    serial_number: str
    certificate_type: str
    milestone_level: Optional[int] = None
    accredited_duration_months: int
    issue_date: date
    verification_hash: str
    verification_qr_url: str
    status: str
    pdf_file_asset_id: Optional[uuid.UUID] = None
    requested_by_id: uuid.UUID
    requested_at: datetime
    stage1_reviewer_id: Optional[uuid.UUID] = None
    stage1_reviewed_at: Optional[datetime] = None
    stage1_notes: Optional[str] = None
    stage2_approver_id: Optional[uuid.UUID] = None
    stage2_approved_at: Optional[datetime] = None
    stage2_notes: Optional[str] = None
    issued_at_utc: Optional[datetime] = None
    revoked_by_id: Optional[uuid.UUID] = None
    revoked_at: Optional[datetime] = None
    revocation_category: Optional[str] = None
    revocation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    approvals: List[CertificateApprovalItem] = []
    revocations: List[CertificateRevocationItem] = []

    # Learnova Integration Compatibility Fields
    candidate_name: Optional[str] = None
    candidate_number: Optional[str] = None
    course_or_track_title: Optional[str] = None
    stage1_approved: bool = False
    stage2_approved: bool = False
    verification_url: Optional[str] = None
    qr_code_available: bool = False


class CertificatePublicVerifyResponse(BaseModel):
    """Public credential verification response. Contains zero PII/sensitive internal state."""
    model_config = ConfigDict(from_attributes=True)

    is_valid: bool
    status: str
    serial_number: str
    candidate_name: str
    track_title: str
    accredited_duration_months: int
    issue_date: date
    verification_hash: str
    issued_at_utc: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revocation_category: Optional[str] = None
    verification_qr_url: str


class CertificateListResponse(BaseModel):
    items: List[CertificateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int = 1
