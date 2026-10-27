"""
ExcelR Track360 - Certificate Management & Verification Engine Models
Domain 6: Credentials, Two-Stage Approvals, Cryptographic Verification & Revocations.
Strictly adheres to DBS-TRK360-V1.0, BR-CERT-01, BR-CERT-02, and SEC-CERT-01 specifications.
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


class CertificateRecord(Base):
    """
    Master certificate issuance record.
    Embeds cryptographic verification hash, serial number, and two-stage approval trail.
    """
    __tablename__ = "certificates"

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
    internship_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("internship_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Serial Number (e.g., EXCELR-2026-FSD-7D2A1B8C)
    serial_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    # Type & Scope
    certificate_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="FINAL_COMPREHENSIVE",  # FINAL_COMPREHENSIVE, MILESTONE
    )
    milestone_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    accredited_duration_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Snapshot Display Attributes (Tamper-evident snapshot at issuance time)
    candidate_display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    course_display_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Cryptographic Verification & QR
    verification_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    verification_qr_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    # State Machine: PENDING_APPROVAL, REVIEWED, ISSUED, REJECTED, REVOKED
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING_APPROVAL",
        index=True,
    )

    # PDF File Asset Link
    pdf_file_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Requester / Stage 0
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Stage 1: Coordinator Review
    stage1_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage1_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stage1_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Stage 2: Approver / Director Sign-off
    stage2_approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage2_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stage2_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    issued_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Revocation Details (if revoked)
    revoked_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revocation_category: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

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

    # Relationships
    candidate = relationship("Candidate", lazy="selectin")
    track = relationship("CourseTrack", lazy="selectin")
    internship_record = relationship("InternshipRecord", lazy="selectin")
    requested_by = relationship("User", foreign_keys=[requested_by_id], lazy="selectin")
    stage1_reviewer = relationship("User", foreign_keys=[stage1_reviewer_id], lazy="selectin")
    stage2_approver = relationship("User", foreign_keys=[stage2_approver_id], lazy="selectin")
    revoked_by = relationship("User", foreign_keys=[revoked_by_id], lazy="selectin")
    pdf_file_asset = relationship("FileAsset", foreign_keys=[pdf_file_asset_id], lazy="selectin")

    approvals: Mapped[List["CertificateApproval"]] = relationship(
        "CertificateApproval",
        back_populates="certificate",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CertificateApproval.decided_at_utc",
    )
    revocations: Mapped[List["CertificateRevocation"]] = relationship(
        "CertificateRevocation",
        back_populates="certificate",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CertificateRevocation.revoked_at_utc.desc()",
    )


class CertificateApproval(Base):
    """
    Immutable audit record for multi-tier certificate reviews and approvals.
    Enforces Separation of Duties (SoD) tracking.
    """
    __tablename__ = "certificate_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,  # STAGE_1_REVIEW, STAGE_2_APPROVAL
    )
    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,  # APPROVED, REJECTED
    )
    decision_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    decided_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relationships
    approver = relationship("User", lazy="selectin")
    certificate = relationship("CertificateRecord", back_populates="approvals")


class CertificateRevocation(Base):
    """
    Immutable audit record for certificate revocations.
    Captures reason category, mandatory detailed rationale, and revoking authority.
    """
    __tablename__ = "certificate_revocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revoked_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,  # ACADEMIC_MALPRACTICE, DATA_ENTRY_ERROR, DISCIPLINARY_ACTION, ADMINISTRATIVE_OVERRIDE
    )
    detailed_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    revoked_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relationships
    revoker = relationship("User", lazy="selectin")
    certificate = relationship("CertificateRecord", back_populates="revocations")
