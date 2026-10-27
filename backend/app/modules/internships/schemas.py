"""
ExcelR Track360 - Internship Pydantic Schemas
Domain 5: Internship Tracking, Decoupled Calendar Dates & Accredited Duration Policies.
Strictly adheres to BR-INT-01 and BR-INT-02 specifications.
"""
import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InternshipCreateRequest(BaseModel):
    """Payload to initiate a formal candidate internship record (WF-07)."""
    candidate_id: uuid.UUID
    track_id: uuid.UUID
    start_date: date
    expected_end_date: Optional[date] = None
    company_name: Optional[str] = Field(default="ExcelR Technology Labs", max_length=150)
    coordinator_notes: Optional[str] = None
    initial_status: Optional[str] = Field(default="ACTIVE", pattern="^(ELIGIBLE|ACTIVE)$")


class InternshipUpdateRequest(BaseModel):
    """Payload to update calendar dates or notes without altering accredited duration policy."""
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    company_name: Optional[str] = Field(default=None, max_length=150)
    coordinator_notes: Optional[str] = None
    internship_status: Optional[str] = Field(default=None, pattern="^(ELIGIBLE|ACTIVE|COMPLETED|TERMINATED)$")


class InternshipCompleteRequest(BaseModel):
    """Payload to confirm verified completion of an internship record."""
    actual_completion_date: Optional[date] = None
    completion_notes: Optional[str] = None


class InternshipTerminateRequest(BaseModel):
    """Payload to terminate an internship with mandatory justification."""
    reason: str = Field(..., min_length=10, description="Mandatory reason for internship termination")


class InternshipMilestoneItem(BaseModel):
    """Accredited project-linked milestone tier."""
    id: uuid.UUID
    milestone_tier: int
    title: str
    project_id: Optional[uuid.UUID] = None
    project_title: Optional[str] = None
    accredited_months: int
    status: str
    achieved_at: Optional[datetime] = None
    verified_by_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InternshipListItem(BaseModel):
    """Summary item for paginated directory view."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_number: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    track_id: uuid.UUID
    track_code: Optional[str] = None
    track_title: Optional[str] = None
    start_date: date
    expected_end_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    accredited_duration_months: int
    internship_status: str
    company_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InternshipResponse(BaseModel):
    """Detailed view of an internship record with milestone breakdown."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_number: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    track_id: uuid.UUID
    track_code: Optional[str] = None
    track_title: Optional[str] = None
    start_date: date
    expected_end_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    accredited_duration_months: int
    internship_status: str
    company_name: Optional[str] = None
    coordinator_notes: Optional[str] = None
    milestones: List[InternshipMilestoneItem] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InternshipPaginatedResponse(BaseModel):
    """Paginated list of internship records."""
    items: List[InternshipListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CandidateInternshipEligibilityResponse(BaseModel):
    """Diagnostic check for candidate internship readiness."""
    candidate_id: uuid.UUID
    candidate_name: str
    is_eligible: bool
    approved_projects_count: int
    mandatory_assignments_passed: bool
    recommended_accredited_months: int
    existing_record_id: Optional[uuid.UUID] = None
    eligible_reason: str
