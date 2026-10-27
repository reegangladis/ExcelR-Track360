"""
ExcelR Track360 - Projects Domain Pydantic Schemas
Phase 8: Project Catalog, Milestones, and Capstone Deliverables
Strictly complies with URP-TRK360-V1.0 specifications.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliverableSpecItem(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=150)
    deliverable_type: str = Field(..., pattern="^(GIT_REPO|FILE_UPLOAD|DEMO_URL|DOCUMENTATION)$")
    is_required: bool = True
    description: Optional[str] = None


class RubricCriterionItem(BaseModel):
    key: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=150)
    max_points: float = Field(..., gt=0)
    description: Optional[str] = None


class MilestoneCreateItem(BaseModel):
    sequence_order: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    weight_percentage: float = Field(..., gt=0, le=100)
    max_score: float = Field(default=100.0, gt=0)
    is_mandatory: bool = True
    required_deliverables: List[Dict[str, Any]] = Field(default_factory=list)


class MilestoneUpdateItem(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    weight_percentage: Optional[float] = Field(None, gt=0, le=100)
    max_score: Optional[float] = Field(None, gt=0)
    is_mandatory: Optional[bool] = None
    required_deliverables: Optional[List[Dict[str, Any]]] = None


class MilestoneResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    sequence_order: int
    title: str
    description: Optional[str] = None
    weight_percentage: float
    max_score: float
    is_mandatory: bool
    required_deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateRequest(BaseModel):
    track_id: uuid.UUID
    code: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    tier: str = Field(..., pattern="^(TIER_1_FOUNDATIONAL|TIER_2_INTERMEDIATE|TIER_3_CAPSTONE)$")
    complexity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    min_team_size: int = Field(default=2, ge=1, le=10)
    max_team_size: int = Field(default=5, ge=1, le=10)
    passing_score: float = Field(default=60.0, ge=0, le=100)
    deliverable_specs: List[DeliverableSpecItem] = Field(default_factory=list)
    rubric_template: List[RubricCriterionItem] = Field(default_factory=list)
    milestones: List[MilestoneCreateItem] = Field(default_factory=list)

    @field_validator("max_team_size")
    @classmethod
    def validate_team_bounds(cls, v: int, info) -> int:
        min_size = info.data.get("min_team_size")
        if min_size is not None and v < min_size:
            raise ValueError("max_team_size cannot be smaller than min_team_size.")
        return v

    @field_validator("milestones")
    @classmethod
    def validate_milestone_weights(cls, milestones: List[MilestoneCreateItem]) -> List[MilestoneCreateItem]:
        if milestones:
            total_weight = sum(m.weight_percentage for m in milestones)
            if round(total_weight, 2) != 100.0:
                raise ValueError(
                    f"Milestone weight percentages must sum exactly to 100.0% (current sum: {total_weight:.2f}%)."
                )
            # Ensure unique sequence orders
            seqs = [m.sequence_order for m in milestones]
            if len(seqs) != len(set(seqs)):
                raise ValueError("Milestone sequence_order values must be distinct.")
        return milestones


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    complexity: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    min_team_size: Optional[int] = Field(None, ge=1, le=10)
    max_team_size: Optional[int] = Field(None, ge=1, le=10)
    passing_score: Optional[float] = Field(None, ge=0, le=100)
    deliverable_specs: Optional[List[DeliverableSpecItem]] = None
    rubric_template: Optional[List[RubricCriterionItem]] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    track_title: Optional[str] = None
    code: str
    title: str
    description: Optional[str] = None
    tier: str
    complexity: str
    min_team_size: int
    max_team_size: int
    passing_score: float
    deliverable_specs: List[Dict[str, Any]] = Field(default_factory=list)
    rubric_template: List[Dict[str, Any]] = Field(default_factory=list)
    is_active: bool
    milestones: List[MilestoneResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListItem(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    track_title: Optional[str] = None
    code: str
    title: str
    tier: str
    complexity: str
    min_team_size: int
    max_team_size: int
    passing_score: float
    milestone_count: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectPaginatedResponse(BaseModel):
    items: List[ProjectListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==========================================
# Phase 9: Project Groups & Dynamic Sizing
# ==========================================

class GroupMemberItem(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_number: str
    candidate_email: str
    role: str
    status: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMemberAddRequest(BaseModel):
    candidate_id: uuid.UUID
    role: str = Field(default="MEMBER", pattern="^(LEADER|MEMBER)$")


class ProjectGroupCreateRequest(BaseModel):
    batch_id: uuid.UUID
    group_name: str = Field(..., min_length=3, max_length=100)
    project_id: Optional[uuid.UUID] = None
    min_size: int = Field(default=2, ge=1, le=10)
    target_size: int = Field(default=4, ge=1, le=10)
    max_size: int = Field(default=5, ge=1, le=10)
    initial_candidate_ids: List[uuid.UUID] = Field(default_factory=list)
    leader_candidate_id: Optional[uuid.UUID] = None

    @field_validator("max_size")
    @classmethod
    def validate_group_bounds(cls, v: int, info) -> int:
        min_s = info.data.get("min_size", 2)
        if v < min_s:
            raise ValueError("max_size cannot be smaller than min_size.")
        return v


class ProjectGroupUpdateRequest(BaseModel):
    group_name: Optional[str] = Field(None, min_length=3, max_length=100)
    project_id: Optional[uuid.UUID] = None
    group_status: Optional[str] = Field(None, pattern="^(FORMING|ACTIVE|LOCKED|COMPLETED|DISSOLVED)$")


class ProjectGroupResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    batch_code: Optional[str] = None
    batch_title: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    project_code: Optional[str] = None
    project_title: Optional[str] = None
    group_name: str
    group_status: str
    min_size: int
    target_size: int
    max_size: int
    member_count: int
    members: List[GroupMemberItem] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectGroupListItem(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    batch_code: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    project_code: Optional[str] = None
    group_name: str
    group_status: str
    member_count: int
    min_size: int
    target_size: int
    max_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectGroupPaginatedResponse(BaseModel):
    items: List[ProjectGroupListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

