"""
ExcelR Track360 - Candidate & Cohort Pydantic Schemas
Validates all incoming payloads and provides tailored responses for staff vs students.
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==========================================
# Course & Track Schemas
# ==========================================

class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None


class CourseResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseTrackCreate(BaseModel):
    course_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=200)
    total_mandatory_assignments: int = Field(default=0, ge=0)
    total_required_projects: int = Field(default=3, ge=1, le=5)
    duration_policy_config: Dict[str, Any] = Field(default_factory=lambda: {"1": 3, "2": 6, "3": 9})


class CourseTrackResponse(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    code: str
    title: str
    total_mandatory_assignments: int
    total_required_projects: int
    duration_policy_config: Dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Batch / Cohort Schemas
# ==========================================

class BatchCreate(BaseModel):
    track_id: uuid.UUID
    batch_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=200)
    start_date: date
    expected_end_date: Optional[date] = None
    status: str = Field(default="ACTIVE")


class BatchResponse(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    batch_code: str
    title: str
    start_date: date
    expected_end_date: Optional[date] = None
    status: str
    coordinator_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Candidate Schemas
# ==========================================

class CandidateCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=32)
    alternate_phone: Optional[str] = Field(None, max_length=32)
    academic_qualification: Optional[str] = Field(None, max_length=150)
    batch_id: Optional[uuid.UUID] = None  # If provided, creates initial enrollment


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[None | str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=32)
    alternate_phone: Optional[str] = Field(None, max_length=32)
    academic_qualification: Optional[str] = Field(None, max_length=150)


class CandidateStatusTransitionRequest(BaseModel):
    to_status: str = Field(..., description="Target status: ENROLLED, ACTIVE, ON_HOLD, DROPPED, COMPLETED, ALUMNI")
    reason: str = Field(..., min_length=5, description="Mandatory audit justification for status modification")


class CandidateResponse(BaseModel):
    """Full candidate representation for authorized staff members."""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    candidate_number: str
    first_name: str
    last_name: str
    email: str
    phone: str
    alternate_phone: Optional[str] = None
    academic_qualification: Optional[str] = None
    lifecycle_status: str
    project_eligible: bool
    completed_projects_count: int
    created_at: datetime
    updated_at: datetime
    batch_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateMaskedResponse(BaseModel):
    """Peer-safe candidate view without contact information or PII."""
    id: uuid.UUID
    candidate_number: str
    first_name: str
    last_name: str
    lifecycle_status: str
    project_eligible: bool
    completed_projects_count: int

    model_config = ConfigDict(from_attributes=True)


class CandidatePaginatedResponse(BaseModel):
    items: List[CandidateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==========================================
# Bulk Import Schemas
# ==========================================

class ImportRowItem(BaseModel):
    row_number: int
    first_name: str
    last_name: str
    email: str
    phone: str
    batch_code: Optional[str] = None
    academic_qualification: Optional[str] = None
    is_valid: bool = True
    error_field: Optional[str] = None
    error_message: Optional[str] = None


class ImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    error_rows_count: int
    rows: List[ImportRowItem]


class ImportCommitRequest(BaseModel):
    rows: List[ImportRowItem]
    default_batch_id: Optional[uuid.UUID] = None


class ImportCommitResponse(BaseModel):
    inserted_count: int
    skipped_count: int
    message: str
