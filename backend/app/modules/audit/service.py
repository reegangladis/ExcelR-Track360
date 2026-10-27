"""
ExcelR Track360 - Audit Trail Service
Provides standardized audit log creation, query, and CSV export utilities.
"""
import csv
import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogItem
from app.modules.auth.models import User


async def write_audit_log(
    db: AsyncSession,
    action: str,
    actor_id: Optional[uuid.UUID] = None,
    resource_type: str = "",
    resource_id: Optional[str] = None,
    pre_state: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    justification: Optional[str] = None,
    request_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Helper to append an immutable audit log record to the active transaction."""
    entity_uuid: Optional[uuid.UUID] = None
    if resource_id:
        try:
            entity_uuid = uuid.UUID(str(resource_id))
        except (ValueError, TypeError):
            entity_uuid = None

    log = AuditLog(
        id=uuid.uuid4(),
        actor_user_id=actor_id,
        actor_ip_address=request_ip,
        actor_user_agent=user_agent,
        action_type=action,
        entity_type=resource_type,
        entity_id=entity_uuid,
        pre_state=pre_state,
        post_state=details,
        justification=justification,
        created_at=utc_now(),
    )
    db.add(log)
    return log


class AuditService:
    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        action_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[AuditLogItem], int]:
        """Queries immutable audit logs with multi-dimensional filtering and actor hydration."""
        base_query = (
            select(
                AuditLog,
                User.email.label("actor_email"),
                User.full_name.label("actor_name"),
            )
            .outerjoin(User, AuditLog.actor_user_id == User.id)
        )

        if actor_id:
            base_query = base_query.where(AuditLog.actor_user_id == actor_id)
        if entity_type:
            base_query = base_query.where(AuditLog.entity_type == entity_type)
        if action_type:
            base_query = base_query.where(AuditLog.action_type == action_type)
        if date_from:
            base_query = base_query.where(AuditLog.created_at >= date_from)
        if date_to:
            base_query = base_query.where(AuditLog.created_at <= date_to)
        if search:
            search_pattern = f"%{search.strip()}%"
            base_query = base_query.where(
                (AuditLog.action_type.ilike(search_pattern))
                | (AuditLog.entity_type.ilike(search_pattern))
                | (AuditLog.justification.ilike(search_pattern))
                | (User.email.ilike(search_pattern))
                | (User.full_name.ilike(search_pattern))
            )

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await db.scalar(count_stmt)) or 0

        # Paginated fetch
        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.all()

        items = []
        for log, actor_email, actor_name in rows:
            items.append(
                AuditLogItem(
                    id=log.id,
                    actor_user_id=log.actor_user_id,
                    actor_email=actor_email,
                    actor_name=actor_name,
                    actor_ip_address=log.actor_ip_address,
                    actor_user_agent=log.actor_user_agent,
                    action_type=log.action_type,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    pre_state=log.pre_state,
                    post_state=log.post_state,
                    justification=log.justification,
                    created_at=log.created_at,
                )
            )

        return items, total

    @staticmethod
    async def generate_audit_csv(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        action_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generates RFC 4180 CSV export of filtered audit records."""
        base_query = (
            select(
                AuditLog,
                User.email.label("actor_email"),
                User.full_name.label("actor_name"),
            )
            .outerjoin(User, AuditLog.actor_user_id == User.id)
            .order_by(AuditLog.created_at.desc())
            .limit(5000)
        )

        if actor_id:
            base_query = base_query.where(AuditLog.actor_user_id == actor_id)
        if entity_type:
            base_query = base_query.where(AuditLog.entity_type == entity_type)
        if action_type:
            base_query = base_query.where(AuditLog.action_type == action_type)
        if date_from:
            base_query = base_query.where(AuditLog.created_at >= date_from)
        if date_to:
            base_query = base_query.where(AuditLog.created_at <= date_to)

        result = await db.execute(base_query)
        rows = result.all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Audit ID",
            "Timestamp (UTC)",
            "Action Type",
            "Entity Type",
            "Entity ID",
            "Actor Email",
            "Actor Name",
            "Actor IP",
            "Justification",
        ])

        for log, actor_email, actor_name in rows:
            writer.writerow([
                str(log.id),
                log.created_at.isoformat() if log.created_at else "",
                log.action_type,
                log.entity_type,
                str(log.entity_id) if log.entity_id else "",
                actor_email or "SYSTEM",
                actor_name or "System Daemon",
                log.actor_ip_address or "",
                log.justification or "",
            ])

        return output.getvalue()
