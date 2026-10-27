"""
ExcelR Track360 - Authentication & RBAC Dependencies
Enforces server-side authentication, CSRF validation, and granular role/permission checks.
Adheres strictly to zero-trust architecture (SEC-TRK360-V1.0).
"""
from typing import List, Optional, Tuple, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import logger
from app.modules.auth.models import User, UserSession
from app.modules.auth.service import AuthService

settings = get_settings()

SESSION_COOKIE_NAME = "track360_session"
CSRF_COOKIE_NAME = "track360_csrf"
CSRF_HEADER_NAME = "x-csrf-token"

# Optional bearer scheme for direct programmatic API calls / test suites
optional_bearer = HTTPBearer(auto_error=False)


async def get_current_session_and_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> Tuple[UserSession, User]:
    """
    Validates the active session from HttpOnly cookie or Authorization Bearer header.
    Validates CSRF tokens on state-changing requests when authenticated via cookie.
    """
    token: Optional[str] = None
    is_cookie_auth = False

    # 1. Prefer HttpOnly session cookie
    if SESSION_COOKIE_NAME in request.cookies:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        is_cookie_auth = True
    elif bearer and bearer.credentials:
        token = bearer.credentials
        is_cookie_auth = False

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or session expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    service = AuthService(db)
    session_pair = await service.get_session_by_token(token)

    if session_pair is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session, user = session_pair

    # 2. Enforce CSRF protection for unsafe HTTP methods when using cookie authentication
    if is_cookie_auth and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        # Check either session csrf token or cookie csrf token
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        
        # Valid if csrf_header matches session's stored csrf_token or csrf_cookie
        expected_token = session.csrf_token or csrf_cookie
        if not csrf_header or not expected_token or csrf_header != expected_token:
            logger.warning(f"CSRF validation failed for user {user.id} on {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or mismatch. State-changing requests must include a valid X-CSRF-Token header.",
            )

    return session, user


async def get_current_user(
    session_user: Tuple[UserSession, User] = Depends(get_current_session_and_user),
) -> User:
    """Dependency yielding the currently authenticated User."""
    return session_user[1]


def require_role(*required_roles: str) -> Callable:
    """
    Dependency factory enforcing that the user has at least one of the specified roles.
    Raises 403 Forbidden on failure.
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role_codes = {r.code for r in current_user.roles}
        # Super admin always has access
        if "ROLE_SUPER_ADMIN" in user_role_codes:
            return current_user

        if not any(role in user_role_codes for role in required_roles):
            logger.warning(
                f"Access denied for user {current_user.id}: lacks required roles {required_roles} (has {user_role_codes})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: this action requires one of the following roles: {', '.join(required_roles)}",
            )
        return current_user

    return role_checker


def require_permission(*required_permissions: str) -> Callable:
    """
    Dependency factory enforcing that the user possesses all specified granular permissions.
    Raises 403 Forbidden on failure.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_role_codes = {r.code for r in current_user.roles}
        if "ROLE_SUPER_ADMIN" in user_role_codes:
            return current_user

        _, user_permissions = AuthService.extract_permissions_and_roles(current_user)
        user_perm_set = set(user_permissions)

        missing = [p for p in required_permissions if p not in user_perm_set]
        if missing:
            logger.warning(
                f"Access denied for user {current_user.id}: missing permissions {missing}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: missing required permission(s): {', '.join(missing)}",
            )
        return current_user

    return permission_checker
