"""
ExcelR Track360 - Audit Trail Pydantic Schemas
Domain 6: Immutable Operational & Security Audit Trail Schemas
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    actor_ip_address: Optional[str] = None
    actor_user_agent: Optional[str] = None
    action_type: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    pre_state: Optional[Dict[str, Any]] = None
    post_state: Optional[Dict[str, Any]] = None
    justification: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: int
    page_size: int
