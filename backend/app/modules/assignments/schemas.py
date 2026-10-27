"""
ExcelR Track360 - Assignment Management Schemas
Pydantic v2 schemas for assignment templates, rubrics, and allocations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
