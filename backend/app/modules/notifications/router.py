"""
ExcelR Track360 - Notifications & Email Queue Router
Domain 6: In-App Alerts, Event Notifications, and Outgoing Email Queue Endpoints
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user, require_role
from app.modules.auth.models import User
from app.modules.notifications.schemas import (
    NotificationItem,
    NotificationListResponse,
    NotificationUnreadCountResponse,
    NotificationDispatchCreate,
    EmailQueueListResponse,
    EmailRetryRequest,
)
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves paginated notifications and total unread count for the authenticated user."""
    items, total, unread_count = await NotificationService.get_user_notifications(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fast endpoint returning unread notification badge count."""
    count = await NotificationService.get_unread_count(db, user_id=current_user.id)
    return NotificationUnreadCountResponse(unread_count=count)


@router.patch("/{id}/read", response_model=NotificationItem)
async def mark_notification_read(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks a single notification as read with strict ownership validation."""
    return await NotificationService.mark_as_read(
        db,
        notification_id=id,
        user_id=current_user.id,
    )


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marks all unread notifications as read for the authenticated user."""
    updated = await NotificationService.mark_all_as_read(db, user_id=current_user.id)
    return {"message": "All notifications marked as read", "updated_count": updated}


@router.post(
    "/dispatch",
    response_model=List[NotificationItem],
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN", "ROLE_CAN_COORD", "ROLE_PRJ_COORD")
        )
    ],
)
async def dispatch_notifications(
    payload: NotificationDispatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Administrative endpoint to dispatch notification alerts and enqueue emails."""
    return await NotificationService.dispatch_batch(db, payload)


@router.get(
    "/email-queue",
    response_model=EmailQueueListResponse,
    dependencies=[Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN"))],
)
async def list_email_queue(
    delivery_status: Optional[str] = Query(None, description="PENDING, SENT, FAILED, RETRYING"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Administrative inspection of transactional email queue and delivery states."""
    items, total = await NotificationService.get_email_queue(
        db,
        delivery_status=delivery_status,
        page=page,
        page_size=page_size,
    )
    return EmailQueueListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/email-queue/retry-failed",
    dependencies=[Depends(require_role("ROLE_SUPER_ADMIN", "ROLE_OPS_ADMIN"))],
)
async def retry_failed_emails(
    payload: Optional[EmailRetryRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Administrative command to requeue failed emails for background dispatch."""
    queue_ids = payload.queue_ids if payload else None
    count = await NotificationService.retry_failed_emails(db, queue_ids=queue_ids)
    return {"message": "Failed emails scheduled for retry", "retried_count": count}
