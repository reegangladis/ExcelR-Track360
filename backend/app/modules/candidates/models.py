"""
ExcelR Track360 - Candidate & Academic Cohort ORM Models
Domain 2: Courses, Tracks, Batches, Candidates, Enrollments, and Notes.
Strictly adheres to DBS-TRK360-V1.0 specifications.
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import utc_now


class Course(Base):
    """Academic Course master entity (e.g. Data Analytics, Data Science, Full Stack)."""
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    tracks: Mapped[List["CourseTrack"]] = relationship("CourseTrack", back_populates="course", lazy="selectin")


class CourseTrack(Base):
    """Specialization track under a Course with prerequisite & duration policies."""
    __tablename__ = "course_tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    total_mandatory_assignments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_required_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    duration_policy_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: {"1": 3, "2": 6, "3": 9}
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    course: Mapped["Course"] = relationship("Course", back_populates="tracks")
    batches: Mapped[List["Batch"]] = relationship("Batch", back_populates="track", lazy="selectin")


class Batch(Base):
    """Student Cohort / Batch assigned to a specific Course Track."""
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_tracks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )  # UPCOMING, ACTIVE, PAUSED, COMPLETED, ARCHIVED
    coordinator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    track: Mapped["CourseTrack"] = relationship("CourseTrack", back_populates="batches")
    enrollments: Mapped[List["Enrollment"]] = relationship("Enrollment", back_populates="batch", lazy="selectin")


class Candidate(Base):
    """Authoritative Candidate / Student golden record."""
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    candidate_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    academic_qualification: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )  # ENROLLED, ACTIVE, ON_HOLD, DROPPED, COMPLETED, ALUMNI
    project_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    completed_projects_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="candidate", cascade="all, delete-orphan", lazy="selectin"
    )
    notes: Mapped[List["CandidateNote"]] = relationship(
        "CandidateNote", back_populates="candidate", cascade="all, delete-orphan", lazy="selectin"
    )
    status_history: Mapped[List["CandidateStatusHistory"]] = relationship(
        "CandidateStatusHistory", back_populates="candidate", cascade="all, delete-orphan", lazy="selectin"
    )


class Enrollment(Base):
    """Candidate enrollment into a specific batch."""
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("candidate_id", "batch_id", name="uq_enrollment_candidate_batch"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    enrollment_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    enrollment_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )  # ACTIVE, COMPLETED, DROPPED, TRANSFERRED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="enrollments")
    batch: Mapped["Batch"] = relationship("Batch", back_populates="enrollments", lazy="selectin")


class CandidateNote(Base):
    """Internal staff notes on candidate interactions and lifecycle events."""
    __tablename__ = "candidate_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    note_category: Mapped[str] = mapped_column(String(64), nullable=False, default="GENERAL")
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="notes")


class CandidateStatusHistory(Base):
    """Audit log of candidate lifecycle status transitions."""
    __tablename__ = "candidate_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="status_history")
