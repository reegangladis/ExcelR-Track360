"""
ExcelR Track360 - Authentication & Identity API Endpoints
Provides login, logout, session management, identity bootstrap, and password reset flows.
Adheres strictly to SEC-TRK360-V1.0 specifications.
"""
from typing import List, Tuple
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.auth.dependencies import (
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    get_current_session_and_user,
    get_current_user,
)
from app.modules.auth.models import User, UserSession
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    UserResponse,
    SessionItem,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirmRequest,
    BootstrapAdminRequest,
)
from app.modules.auth.service import AuthService
from app.modules.auth.seed import seed_bootstrap_admin

router = APIRouter()
settings = get_settings()


def _set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    """Sets secure HttpOnly session cookie and accessible CSRF cookie."""
    is_prod = settings.APP_ENV == "production"
    
    # 1. Server-managed HttpOnly session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
        max_age=14 * 86400,  # 14 days maximum cookie lifetime
    )
    # 2. CSRF cookie readable by frontend JavaScript
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        path="/",
        max_age=14 * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clears authentication and CSRF cookies."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


@router.post("/login", response_model=LoginResponse, summary="Establish Authenticated Session")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates user, creates a server-managed session, and sets HttpOnly cookies.
    Enforces account lockout (5 failed attempts -> 15 min lock).
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = AuthService(db)
    user = await service.authenticate_user(
        email=payload.email,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    token, session_record, csrf_token = await service.create_session(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    _set_auth_cookies(response, token, csrf_token)

    roles, permissions = AuthService.extract_permissions_and_roles(user)
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        status=user.status,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        roles=roles,
        permissions=permissions,
    )

    return LoginResponse(
        user=user_response,
        csrf_token=csrf_token,
        session_token=token,
        message="Session established successfully",
    )


@router.post("/logout", summary="Revoke Session & Clear Cookies")
async def logout(
    request: Request,
    response: Response,
    session_user: Tuple[UserSession, User] = Depends(get_current_session_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Revokes the current server session in database and clears authentication cookies."""
    session, user = session_user
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = AuthService(db)
    await service.revoke_session(
        session_id=session.id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    _clear_auth_cookies(response)
    return {"message": "Logged out successfully", "status": "revoked"}


@router.get("/me", response_model=UserResponse, summary="Get Current Authenticated Identity")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns profile, roles, and granular permissions for the active session."""
    roles, permissions = AuthService.extract_permissions_and_roles(current_user)
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        status=current_user.status,
        is_verified=current_user.is_verified,
        last_login_at=current_user.last_login_at,
        roles=roles,
        permissions=permissions,
    )


@router.get("/sessions", response_model=List[SessionItem], summary="List Active Sessions")
async def list_active_sessions(
    session_user: Tuple[UserSession, User] = Depends(get_current_session_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all active concurrent sessions for the authenticated user."""
    current_session, user = session_user
    service = AuthService(db)
    sessions = await service.list_user_sessions(user.id)

    return [
        SessionItem(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            expires_at=s.expires_at,
            last_activity_at=s.last_activity_at,
            created_at=s.created_at,
            is_current=(s.id == current_session.id),
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", summary="Revoke Specific Session")
async def revoke_session_endpoint(
    session_id: uuid.UUID,
    session_user: Tuple[UserSession, User] = Depends(get_current_session_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Revokes a specific session belonging to the user."""
    _, user = session_user
    service = AuthService(db)
    revoked = await service.revoke_session(session_id=session_id, user_id=user.id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked",
        )
    return {"message": "Session revoked successfully"}


@router.post("/password-reset/request", response_model=PasswordResetResponse, summary="Initiate Password Reset")
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates a password reset flow. Returns generic message to prevent account enumeration.
    In development and test environments, the reset token is returned in the response for automated testing.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = AuthService(db)
    raw_token = await service.request_password_reset(
        email=payload.email,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Only include token in dev/test
    show_token = (settings.APP_ENV in ("development", "test")) and raw_token is not None
    return PasswordResetResponse(
        message="If the email is registered, instructions to reset your password have been issued.",
        reset_token=raw_token if show_token else None,
    )


@router.post("/password-reset/confirm", summary="Confirm & Complete Password Reset")
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validates the reset token and updates the user's password using Argon2id."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = AuthService(db)
    await service.confirm_password_reset(
        raw_token=payload.token,
        new_password=payload.new_password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"message": "Password has been successfully updated. Please log in with your new password."}


@router.post("/bootstrap-admin", summary="Bootstrap Local Development Administrator")
async def bootstrap_admin(
    payload: BootstrapAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Safe developer bootstrap endpoint. Only operable in development and test environments.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap endpoint is strictly disabled in production environments.",
        )

    admin = await seed_bootstrap_admin(
        db=db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return {
        "message": "Bootstrap completed successfully",
        "admin_email": admin.email,
        "admin_id": str(admin.id),
    }
