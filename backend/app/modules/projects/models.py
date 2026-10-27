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
    
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    batch = relationship("Batch")
    project = relationship("Project")
    members = relationship(
        "ProjectGroupMember",
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

