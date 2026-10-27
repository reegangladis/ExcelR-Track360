"""
ExcelR Track360 - Notifications & Email Queue Pydantic Schemas
Domain 6: In-App Alerts, Event Notifications & Email Dispatch Schemas
"""
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_user_id: uuid.UUID
    event_type: str
    title: str
    body: str
    action_url: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationDispatchCreate(BaseModel):
    recipient_user_ids: List[uuid.UUID] = Field(..., min_length=1)
    event_type: str = Field(..., max_length=64)
    title: str = Field(..., max_length=200)
    body: str
    action_url: Optional[str] = None
    queue_email: bool = False
    email_subject: Optional[str] = None
    email_html: Optional[str] = None


class EmailQueueItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_email: str
    subject: str
    body_html: str
    delivery_status: str
    attempt_count: int
    max_attempts: int
    last_error_message: Optional[str] = None
    next_retry_at_utc: Optional[datetime] = None
    sent_at_utc: Optional[datetime] = None
    created_at: datetime


class EmailQueueListResponse(BaseModel):
    items: List[EmailQueueItemSchema]
    total: int
    page: int
    page_size: int


class EmailRetryRequest(BaseModel):
    queue_ids: Optional[List[uuid.UUID]] = None
