"""
ExcelR Track360 - Immutable Audit Logs ORM Model
Domain 6: Cross-cutting Audit and Security Operations
"""
import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.security import utc_now


class AuditLog(Base):
    """
    Immutable, append-only security and operational audit trail.
    Strictly forbids DELETE and UPDATE operations.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    actor_user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    pre_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    post_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
