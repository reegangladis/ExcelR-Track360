"""
ExcelR Track360 - Projects Domain ORM Models
Phase 8: Project Catalog, Milestone Tiers 1-3, and Capstone Deliverables
Strictly complies with URP-TRK360-V1.0 specifications.
"""
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import utc_now


class Project(Base):
    """
    Authoritative Project Template / Specification.
    Classified into Tier 1 (Foundational), Tier 2 (Intermediate), and Tier 3 (Capstone).
    """
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey("course_tracks.id", ondelete="RESTRICT"), nullable=False, index=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Tier classification: TIER_1_FOUNDATIONAL | TIER_2_INTERMEDIATE | TIER_3_CAPSTONE
    tier = Column(String(32), nullable=False, index=True)
    
    # Complexity level: LOW | MEDIUM | HIGH | CRITICAL
    complexity = Column(String(32), nullable=False, default="MEDIUM")
    
    # Team size guidelines
    min_team_size = Column(Integer, nullable=False, default=2)
    max_team_size = Column(Integer, nullable=False, default=5)
    
    # Capstone & Deliverable Specifications (e.g. required git repo, documentation, architecture diagram, deployment URL)
    deliverable_specs = Column(JSONB, nullable=False, default=list)
    
    # Rubric Criteria for Grading & Evaluation
    rubric_template = Column(JSONB, nullable=False, default=list)
    
    # Passing threshold score (0 - 100)
    passing_score = Column(Numeric(5, 2), nullable=False, default=60.00)
    
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    track = relationship("CourseTrack", lazy="selectin")
    milestones = relationship(
        "ProjectMilestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.sequence_order",
        lazy="selectin",
    )


class ProjectMilestone(Base):
    """
    Sequential Milestone stages within a Project (e.g., Milestone 1: Design & Schema, Milestone 2: Core ETL, Milestone 3: Presentation).
    Weight percentages across milestones for a project should sum to 100%.
    """
    __tablename__ = "project_milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Percentage weight of this milestone relative to the overall project (e.g. 30.00 for 30%)
    weight_percentage = Column(Numeric(5, 2), nullable=False, default=25.00)
    
    # Maximum score obtainable for this milestone
    max_score = Column(Numeric(5, 2), nullable=False, default=100.00)
    
    is_mandatory = Column(Boolean, nullable=False, default=True)
    required_deliverables = Column(JSONB, nullable=False, default=list)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="milestones")

    __table_args__ = (
        UniqueConstraint("project_id", "sequence_order", name="uq_project_milestone_sequence"),
    )


class ProjectGroup(Base):
    """
    Project Collaboration Group formed within a cohort Batch.
    Strictly enforces dynamic capacity constraints: min 2, target 4, max 5 members.
    """
    __tablename__ = "project_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    group_name = Column(String(100), nullable=False)
    
    # Status: FORMING | ACTIVE | LOCKED | COMPLETED | DISSOLVED
    group_status = Column(String(32), nullable=False, default="FORMING", index=True)
    
    # Dynamic capacity constraints (Business Rule: min 2, target 4, max 5)
    min_size = Column(Integer, nullable=False, default=2)
    target_size = Column(Integer, nullable=False, default=4)
    max_size = Column(Integer, nullable=False, default=5)
    
    # Mentor Assignment
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Milestone & Readiness Tracking
    current_milestone_id = Column(UUID(as_uuid=True), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Readiness Status: NOT_READY | AWAITING_SUBMISSION | SUBMITTED | UNDER_REVIEW | CORRECTIONS_REQUESTED | APPROVED | BLOCKED_PENDING_MEMBERS | READY_FOR_NEXT_PROJECT | COMPLETED
    readiness_status = Column(String(32), nullable=False, default="NOT_READY", index=True)
    
    allocated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    batch = relationship("Batch")
    project = relationship("Project")
    mentor = relationship("User", foreign_keys=[mentor_id])
    current_milestone = relationship("ProjectMilestone", foreign_keys=[current_milestone_id])
    members = relationship(
        "ProjectGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    allocations = relationship(
        "ProjectAllocation",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="ProjectAllocation.allocated_at.desc()",
    )
    submissions = relationship(
        "ProjectGroupSubmission",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="ProjectGroupSubmission.submitted_at.desc()",
    )
    progression_requests = relationship(
        "ProjectProgressionRequest",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class ProjectGroupMember(Base):
    """
    Candidate membership record within a ProjectGroup.
    Enforces role (LEADER | MEMBER) and status (ACTIVE | REMOVED | TRANSFERRED).
    """
    __tablename__ = "project_group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Role within group: LEADER | MEMBER
    role = Column(String(32), nullable=False, default="MEMBER")
    
    # Membership status: ACTIVE | REMOVED | TRANSFERRED
    status = Column(String(32), nullable=False, default="ACTIVE")
    
    joined_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    group = relationship("ProjectGroup", back_populates="members")
    candidate = relationship("Candidate")

    __table_args__ = (
        UniqueConstraint("group_id", "candidate_id", name="uq_project_group_candidate"),
    )


class ProjectAllocation(Base):
    """
    Formal Project Allocation Record linking a ProjectGroup to a specific Project Tier.
    Tracks progression through Tier 1 (Foundational), Tier 2 (Intermediate), and Tier 3 (Capstone).
    """
    __tablename__ = "project_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Tier: TIER_1_FOUNDATIONAL | TIER_2_INTERMEDIATE | TIER_3_CAPSTONE
    tier = Column(String(32), nullable=False, index=True)
    
    # Allocation status: ALLOCATED | IN_PROGRESS | SUBMITTED | UNDER_REVIEW | APPROVED | COMPLETED
    status = Column(String(32), nullable=False, default="ALLOCATED", index=True)
    
    final_score = Column(Numeric(5, 2), nullable=True)
    allocated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    allocated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    group = relationship("ProjectGroup", back_populates="allocations")
    project = relationship("Project")
    allocated_by = relationship("User", foreign_keys=[allocated_by_id])


class ProjectGroupSubmission(Base):
    """
    Group Project Deliverable Submissions per milestone / project tier.
    Preserves full multi-attempt revision history.
    """
    __tablename__ = "project_group_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    
    submitted_by_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    
    # Deliverables
    repo_url = Column(String(500), nullable=True)
    live_demo_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    file_asset_id = Column(UUID(as_uuid=True), ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Review & Grading Status: SUBMITTED | UNDER_REVIEW | APPROVED | CORRECTIONS_REQUESTED
    status = Column(String(32), nullable=False, default="SUBMITTED", index=True)
    
    score = Column(Numeric(5, 2), nullable=True)
    rubric_scores = Column(JSONB, nullable=False, default=list)
    feedback = Column(Text, nullable=True)
    
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    group = relationship("ProjectGroup", back_populates="submissions")
    project = relationship("Project")
    milestone = relationship("ProjectMilestone")
    submitted_by = relationship("Candidate")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    file_asset = relationship("FileAsset")


class ProjectProgressionRequest(Base):
    """
    Individual candidate readiness sign-off / progression request (BR-GRP-01).
    All active members must submit before group progresses to READY_FOR_NEXT_PROJECT.
    """
    __tablename__ = "project_progression_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("project_milestones.id", ondelete="SET NULL"), nullable=True)
    
    # Status: REQUESTED | OVERRIDDEN | WAIVED
    status = Column(String(32), nullable=False, default="REQUESTED", index=True)
    notes = Column(Text, nullable=True)
    
    overridden_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    group = relationship("ProjectGroup", back_populates="progression_requests")
    project = relationship("Project")
    candidate = relationship("Candidate")
    overridden_by = relationship("User", foreign_keys=[overridden_by_id])

    __table_args__ = (
        UniqueConstraint("group_id", "project_id", "candidate_id", name="uq_group_project_candidate_request"),
    )


