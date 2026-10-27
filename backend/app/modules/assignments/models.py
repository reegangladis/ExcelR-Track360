"""
ExcelR Track360 - Assignment & Evaluation Domain Models
Implements authoritative assignment catalog, rubric scoring definitions,
cohort/candidate allocations, attempts versioning, and evaluation lifecycle.
Adheres strictly to DBS-TRK360-V1.0 (Domain 3).
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship

from app.core.database import Base
from app.core.security import utc_now


class FileAsset(Base):
    __tablename__ = "file_assets"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_backend: Mapped[str] = Column(
        String(32),
        nullable=False,
        default="local",
    )
    storage_key: Mapped[str] = Column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = Column(String(255), nullable=False)
    file_extension: Mapped[str] = Column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = Column(BigInteger, nullable=False)
    mime_type: Mapped[str] = Column(String(128), nullable=False)
    checksum_sha256: Mapped[str] = Column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("storage_backend IN ('local', 's3')", name="chk_file_assets_backend"),
    )

    uploader = relationship("User", lazy="selectin")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("course_tracks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = Column(String(64), nullable=False, unique=True, index=True)
    title: Mapped[str] = Column(String(200), nullable=False)
    instructions_markdown: Mapped[str] = Column(Text, nullable=False)
    sequence_order: Mapped[int] = Column(Integer, nullable=False, default=1)
    is_mandatory: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    max_score: Mapped[float] = Column(Numeric(5, 2), nullable=False, default=100.00)
    passing_score: Mapped[float] = Column(Numeric(5, 2), nullable=False, default=60.00)
    rubric_template: Mapped[list] = Column(JSONB, nullable=False, default=list)
    allowed_file_types: Mapped[list] = Column(
        JSONB,
        nullable=False,
        default=lambda: ["pdf", "zip", "ipynb"],
    )
    max_file_size_mb: Mapped[int] = Column(Integer, nullable=False, default=25)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    track = relationship("CourseTrack", lazy="selectin")
    allocations = relationship(
        "AssignmentAllocation",
        back_populates="assignment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AssignmentAllocation(Base):
    __tablename__ = "assignment_allocations"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=True,
    )
    candidate_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=True,
    )
    due_date_utc: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    grace_period_end_utc: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    allocation_status: Mapped[str] = Column(
        String(32),
        nullable=False,
        default="PENDING",
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "batch_id IS NOT NULL OR candidate_id IS NOT NULL",
            name="chk_allocations_target",
        ),
        CheckConstraint(
            "allocation_status IN ('PENDING', 'SUBMITTED', 'COMPLETED', 'EXPIRED')",
            name="chk_allocations_status",
        ),
        Index(
            "uq_allocations_candidate_assignment",
            "candidate_id",
            "assignment_id",
            unique=True,
            postgresql_where=Column("candidate_id").isnot(None),
        ),
    )

    assignment = relationship("Assignment", back_populates="allocations", lazy="selectin")
    batch = relationship("Batch", lazy="selectin")
    candidate = relationship("Candidate", lazy="selectin")
    submissions = relationship(
        "AssignmentSubmission",
        back_populates="allocation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("assignment_allocations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    current_submission_status: Mapped[str] = Column(
        String(32),
        nullable=False,
        default="PENDING",
    )
    current_completion_status: Mapped[str] = Column(
        String(32),
        nullable=False,
        default="INCOMPLETE",
    )
    total_attempts: Mapped[int] = Column(Integer, nullable=False, default=0)
    latest_score: Mapped[Optional[float]] = Column(Numeric(5, 2), nullable=True)
    first_submitted_at_utc: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_submitted_at_utc: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "current_submission_status IN ('PENDING', 'SUBMITTED', 'LATE_SUBMITTED', 'UNDER_REVIEW', 'CORRECTIONS_REQUESTED', 'APPROVED', 'REJECTED')",
            name="chk_submission_status",
        ),
        CheckConstraint(
            "current_completion_status IN ('INCOMPLETE', 'PASSED_COMPLETED', 'FAILED')",
            name="chk_completion_status",
        ),
        UniqueConstraint("allocation_id", "candidate_id", name="uq_submission_allocation_candidate"),
    )

    allocation = relationship("AssignmentAllocation", back_populates="submissions", lazy="selectin")
    candidate = relationship("Candidate", lazy="selectin")
    attempts = relationship(
        "SubmissionAttempt",
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SubmissionAttempt(Base):
    __tablename__ = "submission_attempts"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("assignment_submissions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = Column(Integer, nullable=False)
    file_asset_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    repository_url: Mapped[Optional[str]] = Column(String(500), nullable=True)
    student_notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    submitted_at_utc: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    is_late: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    lateness_minutes: Mapped[int] = Column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("submission_id", "attempt_number", name="uq_attempt_submission_round"),
    )

    submission = relationship("AssignmentSubmission", back_populates="attempts", lazy="selectin")
    file_asset = relationship("FileAsset", lazy="selectin")
    reviews = relationship(
        "SubmissionReview",
        back_populates="attempt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SubmissionReview(Base):
    __tablename__ = "submission_reviews"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("submission_attempts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    review_outcome: Mapped[str] = Column(
        String(32),
        nullable=False,
    )
    total_score: Mapped[float] = Column(Numeric(5, 2), nullable=False)
    qualitative_feedback: Mapped[str] = Column(Text, nullable=False)
    internal_evaluator_notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    review_completed_at_utc: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "review_outcome IN ('APPROVED', 'CORRECTIONS_REQUESTED', 'REJECTED')",
            name="chk_review_outcome",
        ),
    )

    attempt = relationship("SubmissionAttempt", back_populates="reviews", lazy="selectin")
    reviewer = relationship("User", lazy="selectin")
    rubric_scores = relationship(
        "ReviewRubricScore",
        back_populates="review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReviewRubricScore(Base):
    __tablename__ = "review_rubric_scores"

    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey("submission_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion_key: Mapped[str] = Column(String(64), nullable=False)
    criterion_title: Mapped[str] = Column(String(150), nullable=False)
    max_points: Mapped[float] = Column(Numeric(5, 2), nullable=False)
    awarded_points: Mapped[float] = Column(Numeric(5, 2), nullable=False)
    criterion_comments: Mapped[Optional[str]] = Column(Text, nullable=True)

    review = relationship("SubmissionReview", back_populates="rubric_scores")
