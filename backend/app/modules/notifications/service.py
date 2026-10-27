"""
ExcelR Track360 - Notification & Email Dispatch Service Layer
Domain 6: In-App Alerts, Event Notifications, and Email Queue Management
"""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.modules.auth.models import User
from app.modules.notifications.models import NotificationEvent, EmailQueueItem
from app.modules.notifications.schemas import NotificationDispatchCreate


class NotificationService:
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        recipient_user_id: uuid.UUID,
        event_type: str,
        title: str,
        body: str,
        action_url: Optional[str] = None,
        queue_email: bool = False,
        recipient_email: Optional[str] = None,
        email_subject: Optional[str] = None,
        email_html: Optional[str] = None,
    ) -> NotificationEvent:
        """Emits an in-app notification event and optionally enqueues an asynchronous email."""
        notif = NotificationEvent(
            id=uuid.uuid4(),
            recipient_user_id=recipient_user_id,
            event_type=event_type,
            title=title,
            body=body,
            action_url=action_url,
            is_read=False,
            created_at=utc_now(),
        )
        db.add(notif)

        if queue_email:
            email_to = recipient_email
            if not email_to:
                # Query user email
                user = await db.get(User, recipient_user_id)
                if user:
                    email_to = user.email

            if email_to:
                email_item = EmailQueueItem(
                    id=uuid.uuid4(),
                    recipient_email=email_to,
                    subject=email_subject or title,
                    body_html=email_html or f"<p>{body}</p>",
                    delivery_status="PENDING",
                    attempt_count=0,
                    max_attempts=5,
                    created_at=utc_now(),
                )
                db.add(email_item)

        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def dispatch_batch(
        db: AsyncSession,
        payload: NotificationDispatchCreate,
    ) -> List[NotificationEvent]:
        """Dispatches notification events to a batch of recipient user IDs."""
        created_notifs: List[NotificationEvent] = []
        user_ids = list(set(payload.recipient_user_ids))

        # Pre-fetch user emails if queue_email is enabled
        user_email_map = {}
        if payload.queue_email:
            users_query = await db.execute(
                select(User.id, User.email).where(User.id.in_(user_ids))
            )
            for uid, email in users_query.all():
                user_email_map[uid] = email

        for uid in user_ids:
            notif = NotificationEvent(
                id=uuid.uuid4(),
                recipient_user_id=uid,
                event_type=payload.event_type,
                title=payload.title,
                body=payload.body,
                action_url=payload.action_url,
                is_read=False,
                created_at=utc_now(),
            )
            db.add(notif)
            created_notifs.append(notif)

            if payload.queue_email and uid in user_email_map:
                email_item = EmailQueueItem(
                    id=uuid.uuid4(),
                    recipient_email=user_email_map[uid],
                    subject=payload.email_subject or payload.title,
                    body_html=payload.email_html or f"<p>{payload.body}</p>",
                    delivery_status="PENDING",
                    attempt_count=0,
                    max_attempts=5,
                    created_at=utc_now(),
                )
                db.add(email_item)

        await db.commit()
        for notif in created_notifs:
            await db.refresh(notif)
        return created_notifs

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: uuid.UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[NotificationEvent], int, int]:
        """Retrieves paginated notifications for the specified user and total unread count."""
        base_query = select(NotificationEvent).where(
            NotificationEvent.recipient_user_id == user_id
        )
        if unread_only:
            base_query = base_query.where(NotificationEvent.is_read.is_(False))

        # Total matching
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await db.scalar(count_stmt)) or 0

        # Unread count (across all items for this user)
        unread_stmt = select(func.count()).where(
            NotificationEvent.recipient_user_id == user_id,
            NotificationEvent.is_read.is_(False),
        )
        unread_count = (await db.scalar(unread_stmt)) or 0

        # Paginated fetch
        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(NotificationEvent.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total, unread_count

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Fast count of unread notifications for navbar badge display."""
        unread_stmt = select(func.count()).where(
            NotificationEvent.recipient_user_id == user_id,
            NotificationEvent.is_read.is_(False),
        )
        return (await db.scalar(unread_stmt)) or 0

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> NotificationEvent:
        """Marks an individual notification as read with ownership enforcement."""
        notif = await db.get(NotificationEvent, notification_id)
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification {notification_id} not found",
            )
        if notif.recipient_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot mutate notifications belonging to another user",
            )

        notif.is_read = True
        await db.commit()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        """Marks all unread notifications as read for the specified user."""
        stmt = (
            update(NotificationEvent)
            .where(
                NotificationEvent.recipient_user_id == user_id,
                NotificationEvent.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0

    @staticmethod
    async def get_email_queue(
        db: AsyncSession,
        delivery_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[EmailQueueItem], int]:
        """Admin query for transactional email dispatch queue."""
        base_query = select(EmailQueueItem)
        if delivery_status:
            base_query = base_query.where(
                EmailQueueItem.delivery_status == delivery_status.upper()
            )

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await db.scalar(count_stmt)) or 0

        offset = (page - 1) * page_size
        stmt = (
            base_query.order_by(EmailQueueItem.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    @staticmethod
    async def retry_failed_emails(
        db: AsyncSession,
        queue_ids: Optional[List[uuid.UUID]] = None,
    ) -> int:
        """Resets failed or retrying emails back to RETRYING status for background dispatch."""
        stmt = update(EmailQueueItem).where(
            EmailQueueItem.delivery_status.in_(["FAILED", "RETRYING"])
        )
        if queue_ids:
            stmt = stmt.where(EmailQueueItem.id.in_(queue_ids))

        stmt = stmt.values(
            delivery_status="RETRYING",
            next_retry_at_utc=utc_now(),
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0
