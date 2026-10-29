"""
ExcelR Track360 - Assignment Management Schemas
Pydantic v2 schemas for assignment templates, rubrics, and allocations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RubricCriterion(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=150)
    max_points: float = Field(..., gt=0)
    description: Optional[str] = None


class AssignmentCreateRequest(BaseModel):
    track_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=3, max_length=200)
    instructions_markdown: str = Field(..., min_length=10)
    sequence_order: int = Field(default=1, ge=1)
    is_mandatory: bool = True
    max_score: float = Field(default=100.0, gt=0)
    passing_score: float = Field(default=60.0, gt=0)
    rubric_template: List[Dict[str, Any]] = Field(default_factory=list)
    allowed_file_types: List[str] = Field(default_factory=lambda: ["pdf", "zip", "ipynb"])
    max_file_size_mb: int = Field(default=25, ge=1, le=100)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("passing_score")
    @classmethod
    def validate_scores(cls, v: float, info) -> float:
        max_s = info.data.get("max_score", 100.0)
        if v > max_s:
            raise ValueError("passing_score cannot exceed max_score")
        return v


class AssignmentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    instructions_markdown: Optional[str] = Field(None, min_length=10)
    sequence_order: Optional[int] = Field(None, ge=1)
    is_mandatory: Optional[bool] = None
    max_score: Optional[float] = Field(None, gt=0)
    passing_score: Optional[float] = Field(None, gt=0)
    rubric_template: Optional[List[Dict[str, Any]]] = None
    allowed_file_types: Optional[List[str]] = None
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=100)
    is_active: Optional[bool] = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    code: str
    title: str
    instructions_markdown: str
    sequence_order: int
    is_mandatory: bool
    max_score: float
    passing_score: float
    rubric_template: List[Dict[str, Any]]
    allowed_file_types: List[str]
    max_file_size_mb: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    track_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentPaginatedResponse(BaseModel):
    items: List[AssignmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AllocationCreateRequest(BaseModel):
    assignment_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    candidate_id: Optional[uuid.UUID] = None
    due_date_utc: datetime
    grace_period_end_utc: Optional[datetime] = None

    @field_validator("grace_period_end_utc")
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info) -> Optional[datetime]:
        due = info.data.get("due_date_utc")
        if v and due and v < due:
            raise ValueError("grace_period_end_utc cannot precede due_date_utc")
        return v


class AllocationResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    assignment_code: str
    assignment_title: str
    batch_id: Optional[uuid.UUID] = None
    batch_code: Optional[str] = None
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None
    due_date_utc: datetime
    grace_period_end_utc: Optional[datetime] = None
    allocation_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AllocationPaginatedResponse(BaseModel):
    items: List[AllocationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReviewRubricScoreItem(BaseModel):
    criterion_key: str = Field(..., min_length=2, max_length=64)
    criterion_title: str = Field(..., min_length=2, max_length=150)
    max_points: float = Field(..., gt=0)
    awarded_points: float = Field(..., ge=0)
    criterion_comments: Optional[str] = None

    @field_validator("awarded_points")
    @classmethod
    def validate_awarded(cls, v: float, info) -> float:
        max_p = info.data.get("max_points")
        if max_p is not None and v > max_p:
            raise ValueError(f"Awarded points ({v}) cannot exceed criterion max points ({max_p})")
        return v


class SubmissionReviewCreateRequest(BaseModel):
    review_outcome: str = Field(..., pattern="^(APPROVED|CORRECTIONS_REQUESTED|REJECTED)$")
    qualitative_feedback: str = Field(..., min_length=5)
    internal_evaluator_notes: Optional[str] = None
    rubric_scores: List[ReviewRubricScoreItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_corrections_note(self) -> "SubmissionReviewCreateRequest":
        if self.review_outcome == "CORRECTIONS_REQUESTED":
            feedback = (self.qualitative_feedback or "").strip()
            if not feedback or len(feedback) < 5:
                raise ValueError(
                    "When requesting corrections (Redo), a meaningful correction note with at least 5 non-whitespace characters is mandatory."
                )
        return self


class SubmissionReviewResponse(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewer_name: Optional[str] = None
    review_outcome: str
    total_score: float
    qualitative_feedback: str
    internal_evaluator_notes: Optional[str] = None
    review_completed_at_utc: datetime
    rubric_scores: List[ReviewRubricScoreItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SubmissionAttemptResponse(BaseModel):
    id: uuid.UUID
    attempt_number: int
    file_asset_id: Optional[uuid.UUID] = None
    original_filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    repository_url: Optional[str] = None
    student_notes: Optional[str] = None
    submitted_at_utc: datetime
    is_late: bool
    lateness_minutes: int
    reviews: List[SubmissionReviewResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionDetailResponse(BaseModel):
    id: uuid.UUID
    allocation_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_number: str
    assignment_code: str
    assignment_title: str
    current_submission_status: str
    current_completion_status: str
    total_attempts: int
    latest_score: Optional[float] = None
    first_submitted_at_utc: Optional[datetime] = None
    latest_submitted_at_utc: Optional[datetime] = None
    due_date_utc: datetime
    grace_period_end_utc: Optional[datetime] = None
    attempts: List[SubmissionAttemptResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionListItem(BaseModel):
    id: uuid.UUID
    allocation_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_number: str
    assignment_code: str
    assignment_title: str
    batch_code: Optional[str] = None
    current_submission_status: str
    current_completion_status: str
    total_attempts: int
    latest_score: Optional[float] = None
    due_date_utc: datetime
    latest_submitted_at_utc: Optional[datetime] = None
    evaluator_name: Optional[str] = None
    evaluator_notes: Optional[str] = None
    is_late: bool = False

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmissionPaginated(BaseModel):
    items: List[AssignmentSubmissionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkAssignmentStatusItem(BaseModel):
    submission_id: uuid.UUID
    status: str = Field(..., description="Target status: NOT_SUBMITTED, SUBMITTED, CORRECTIONS_REQUESTED, APPROVED or Not submitted, Submitted, Redo, Done")
    correction_note: Optional[str] = Field(None, description="Mandatory when status is Redo / CORRECTIONS_REQUESTED")
    awarded_score: Optional[float] = None
    evaluator_notes: Optional[str] = None


class BulkAssignmentStatusUpdateRequest(BaseModel):
    items: List[BulkAssignmentStatusItem] = Field(..., min_length=1, max_length=500)


class BulkAssignmentStatusItemResult(BaseModel):
    submission_id: uuid.UUID
    success: bool
    status: Optional[str] = None
    error: Optional[str] = None


class BulkAssignmentStatusUpdateResponse(BaseModel):
    total_processed: int
    successful_count: int
    failed_count: int
    results: List[BulkAssignmentStatusItemResult]

