"""
ExcelR Track360 - Audit Trail Service
Provides standardized audit log creation and query utilities.
"""
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.modules.audit.models import AuditLog


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
