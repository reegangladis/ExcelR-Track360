"""
ExcelR Track360 - Audit Trail Router
Domain 6: Immutable Operational & Security Audit Trail Endpoints (FR-REP-002, FR-REP-003)
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.audit.schemas import AuditLogListResponse
from app.modules.audit.service import AuditService, write_audit_log
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    dependencies=[
        Depends(
            require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_READ_ONLY")
        )
    ],
)
async def list_audit_logs(
    actor_id: Optional[uuid.UUID] = Query(None, description="Filter by actor user UUID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity domain (e.g. CERTIFICATE, ASSIGNMENT)"),
    action_type: Optional[str] = Query(None, description="Filter by action type (e.g. CERTIFICATE_ISSUED)"),
    date_from: Optional[datetime] = Query(None, description="ISO timestamp start filter"),
    date_to: Optional[datetime] = Query(None, description="ISO timestamp end filter"),
    search: Optional[str] = Query(None, description="Free text search across action, entity, user, justification"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Administrative exploration of immutable security and operational audit records."""
    items, total = await AuditService.get_audit_logs(
        db,
        actor_id=actor_id,
        entity_type=entity_type,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/logs/export",
    dependencies=[
        Depends(
            require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_READ_ONLY")
        )
    ],
)
async def export_audit_logs(
    request: Request,
    actor_id: Optional[uuid.UUID] = Query(None),
    entity_type: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports filtered audit records as RFC 4180 CSV.
    Enforces FR-REP-003: Every export operation is self-recorded in the audit trail.
    """
    csv_content = await AuditService.generate_audit_csv(
        db,
        actor_id=actor_id,
        entity_type=entity_type,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
    )

    # Immutably record export event
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await write_audit_log(
        db=db,
        action="AUDIT_LOG_EXPORTED",
        actor_id=current_user.id,
        resource_type="AUDIT_LOGS",
        resource_id=None,
        details={
            "filters": {
                "actor_id": str(actor_id) if actor_id else None,
                "entity_type": entity_type,
                "action_type": action_type,
            }
        },
        justification="Administrative governed CSV export of audit events",
        request_ip=client_ip,
        user_agent=user_agent,
    )
    await db.commit()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="audit_trail_export.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
