"""
ExcelR Track360 - Internship Lifecycle & Accredited Milestone Progression Models
Domain 5: Internship Tracking, Decoupled Calendar Dates & Accredited Duration Policy.
Strictly adheres to DBS-TRK360-V1.0 and BR-INT-01, BR-INT-02 specifications.
"""
import uuid
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import utc_now


class InternshipRecord(Base):
    """
    Master operational tracking of a candidate's formal internship.
    Strictly decouples real-world calendar duration from accredited milestone duration (BR-INT-01).
    """
    __tablename__ = "internship_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("course_tracks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Operational Calendar Dates (Decoupled from Accredited Duration)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Accredited Duration (Computed via BR-INT-02 Policy Matrix: 1 PRJ=3m, 2 PRJ=6m, 3 PRJ=9m)
    accredited_duration_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    # State Machine: ELIGIBLE, ACTIVE, COMPLETED, TERMINATED
    internship_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    # Company / Enterprise Placement Mapping
    company_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        default="ExcelR Technology Labs",
    )
    coordinator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "track_id", name="uq_internship_candidate_track"),
        Index("ix_internship_status_track", "internship_status", "track_id"),
    )

    # Relationships
    candidate = relationship("Candidate", foreign_keys=[candidate_id], lazy="joined")
    track = relationship("CourseTrack", foreign_keys=[track_id], lazy="joined")
    milestones: Mapped[List["InternshipMilestone"]] = relationship(
        "InternshipMilestone",
        back_populates="internship_record",
        cascade="all, delete-orphan",
        order_by="InternshipMilestone.milestone_tier",
        lazy="selectin",
    )


class InternshipMilestone(Base):
    """
    Accredited progression milestones tracking candidate advancement (Tiers 1, 2, and 3).
    Decoupled from calendar hours, anchored to verified project achievements (BR-INT-02).
    """
    __tablename__ = "internship_milestones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    internship_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    milestone_tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    accredited_months: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Status: PENDING, IN_PROGRESS, ACHIEVED, WAIVED
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    achieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        UniqueConstraint("internship_record_id", "milestone_tier", name="uq_internship_milestone_tier"),
    )

    # Relationships
    internship_record = relationship("InternshipRecord", back_populates="milestones")
    project = relationship("Project", foreign_keys=[project_id], lazy="joined")
    verified_by = relationship("User", foreign_keys=[verified_by_id], lazy="joined")
