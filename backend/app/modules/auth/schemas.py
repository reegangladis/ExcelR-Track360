"""
ExcelR Track360 - Authentication & Access Control Pydantic Schemas
Strictly validates all inbound and outbound payloads.
"""
from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LoginRequest(BaseModel):
    """User credentials for establishing a server-managed session."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class PermissionSchema(BaseModel):
    """Fine-grained permission representation."""
    id: uuid.UUID
    code: str
    module: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RoleSchema(BaseModel):
    """Role definition representation."""
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    is_system_role: bool

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Authenticated user profile with assigned roles and permissions."""
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    status: str
    is_verified: bool
    last_login_at: Optional[datetime] = None
    roles: List[str] = Field(default_factory=list, description="Assigned role codes")
    permissions: List[str] = Field(default_factory=list, description="Calculated permission codes")

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """Response returned upon successful authentication."""
    user: UserResponse
    csrf_token: str
    session_token: Optional[str] = None
    message: str = "Login successful"


class SessionItem(BaseModel):
    """Details of an active server-managed session."""
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    last_activity_at: datetime
    created_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequest(BaseModel):
    """Request payload to initiate a password reset."""
    email: EmailStr


class PasswordResetResponse(BaseModel):
    """Generic response to prevent account enumeration."""
    message: str = "If the email is registered, instructions to reset your password have been issued."
    reset_token: Optional[str] = None  # Returned exclusively in development/test mode


class PasswordResetConfirmRequest(BaseModel):
    """Payload to confirm and complete a password reset."""
    token: str = Field(..., min_length=10, description="Password reset verification token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New strong password")


class BootstrapAdminRequest(BaseModel):
    """Development bootstrap payload for first-time setup."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(default="Platform Administrator")
