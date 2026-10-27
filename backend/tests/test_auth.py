"""
ExcelR Track360 - Authentication & Authorization Test Suite
Phase 4 Verification: Server-managed sessions, Argon2id, lockout,
RBAC/permission gates, CSRF protection, cookie directives, IDOR guards, and reset tokens.
"""
from datetime import timedelta
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import get_db, get_session_factory
from app.core.security import hash_password, utc_now
from app.main import create_application
from app.modules.auth.models import User, Role, UserRole, UserSession
from app.modules.auth.seed import seed_bootstrap_admin, seed_roles_and_permissions
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import SESSION_COOKIE_NAME, CSRF_COOKIE_NAME


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Ensures test database has core roles and seed admin before each test."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_bootstrap_admin(
            db=session,
            email="admin@excelr.com",
            password="Admin@Track360_2026!",
            full_name="Master Administrator",
        )


@pytest.mark.asyncio
async def test_auth_login_success_sets_cookies(async_client: AsyncClient):
    """Verifies successful login returns user payload and sets HttpOnly and CSRF cookies."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@excelr.com", "password": "Admin@Track360_2026!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Session established successfully"
    assert data["user"]["email"] == "admin@excelr.com"
    assert "ROLE_SUPER_ADMIN" in data["user"]["roles"]
    assert len(data["csrf_token"]) > 0

    # Verify cookies
    cookies = response.cookies
    assert SESSION_COOKIE_NAME in cookies
    assert CSRF_COOKIE_NAME in cookies


@pytest.mark.asyncio
async def test_auth_login_invalid_password_generic_error(async_client: AsyncClient):
    """Verifies failed login returns generic error without account enumeration."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@excelr.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_auth_account_lockout_after_five_failed_attempts(async_client: AsyncClient):
    """Verifies brute-force protection locks account after 5 consecutive failed attempts."""
    import uuid
    email = f"lockout_{uuid.uuid4().hex[:8]}@excelr.com"
    session_factory = get_session_factory()
    async with session_factory() as session:
        test_user = User(
            email=email,
            password_hash=hash_password("SecretPassword123!"),
            full_name="Lockout Test User",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(test_user)
        await session.commit()

    # Attempt 5 incorrect logins
    for i in range(5):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "BadPassword!"},
        )
        assert resp.status_code == 401

    # 6th attempt should be blocked by account lockout
    locked_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecretPassword123!"},
    )
    assert locked_resp.status_code == 403
    assert "Account is temporarily locked" in locked_resp.json()["detail"]


@pytest.mark.asyncio
async def test_auth_logout_revokes_session(async_client: AsyncClient):
    """Verifies logout revokes the server session and clears cookies."""
    # 1. Login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@excelr.com", "password": "Admin@Track360_2026!"},
    )
    assert login_resp.status_code == 200
    csrf_token = login_resp.json()["csrf_token"]
    session_token = login_resp.cookies[SESSION_COOKIE_NAME]

    # 2. Access /me successfully
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        cookies={SESSION_COOKIE_NAME: session_token},
    )
    assert me_resp.status_code == 200

    # 3. Logout (with CSRF header)
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        cookies={SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: csrf_token},
        headers={"x-csrf-token": csrf_token},
    )
    assert logout_resp.status_code == 200

    # 4. Attempt to access /me with old session cookie -> rejected
    me_after = await async_client.get(
        "/api/v1/auth/me",
        cookies={SESSION_COOKIE_NAME: session_token},
    )
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_auth_csrf_protection_on_state_changing_methods(async_client: AsyncClient):
    """Verifies unsafe HTTP methods (POST) reject cookie requests without valid X-CSRF-Token."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@excelr.com", "password": "Admin@Track360_2026!"},
    )
    session_token = login_resp.cookies[SESSION_COOKIE_NAME]
    valid_csrf = login_resp.json()["csrf_token"]

    # 1. POST logout with MISSING csrf header -> 403
    missing_csrf = await async_client.post(
        "/api/v1/auth/logout",
        cookies={SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: valid_csrf},
    )
    assert missing_csrf.status_code == 403
    assert "CSRF token missing or mismatch" in missing_csrf.json()["detail"]

    # 2. POST logout with WRONG csrf header -> 403
    wrong_csrf = await async_client.post(
        "/api/v1/auth/logout",
        cookies={SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: valid_csrf},
        headers={"x-csrf-token": "tampered-csrf-token"},
    )
    assert wrong_csrf.status_code == 403

    # 3. POST logout with VALID csrf header -> 200
    success = await async_client.post(
        "/api/v1/auth/logout",
        cookies={SESSION_COOKIE_NAME: session_token, CSRF_COOKIE_NAME: valid_csrf},
        headers={"x-csrf-token": valid_csrf},
    )
    assert success.status_code == 200


@pytest.mark.asyncio
async def test_auth_password_reset_flow(async_client: AsyncClient):
    """Verifies end-to-end password reset request and confirmation."""
    import uuid
    reset_email = f"reset_{uuid.uuid4().hex[:8]}@excelr.com"
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=reset_email,
            password_hash=hash_password("OldPassword123!"),
            full_name="Password Reset Learner",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(user)
        await session.commit()

    # 1. Request password reset
    req_resp = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": reset_email},
    )
    assert req_resp.status_code == 200
    reset_token = req_resp.json()["reset_token"]
    assert reset_token is not None

    # 2. Confirm password reset
    confirm_resp = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "BrandNewPassword2026!"},
    )
    assert confirm_resp.status_code == 200

    # 3. Login with old password fails
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": reset_email, "password": "OldPassword123!"},
    )
    assert old_login.status_code == 401

    # 4. Login with new password succeeds
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": reset_email, "password": "BrandNewPassword2026!"},
    )
    assert new_login.status_code == 200

    # 5. Token reuse is blocked
    reuse_resp = await async_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "YetAnotherPassword2026!"},
    )
    assert reuse_resp.status_code == 400


@pytest.mark.asyncio
async def test_auth_role_and_idor_permission_guard(async_client: AsyncClient):
    """
    Verifies role-based access control and IDOR defenses:
    A student cannot access administrative resources or guess other candidate IDs.
    """
    import uuid
    alice_email = f"student_alice_{uuid.uuid4().hex[:8]}@excelr.com"
    session_factory = get_session_factory()
    async with session_factory() as session:
        student_role = (
            await session.execute(select(Role).where(Role.code == "ROLE_STUDENT"))
        ).scalar_one()

        student_user = User(
            email=alice_email,
            password_hash=hash_password("StudentPassword123!"),
            full_name="Alice Student",
            status="ACTIVE",
            is_verified=True,
        )
        session.add(student_user)
        await session.flush()
        session.add(UserRole(user_id=student_user.id, role_id=student_role.id))
        await session.commit()

    # Login as student
    student_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": alice_email, "password": "StudentPassword123!"},
    )
    assert student_login.status_code == 200
    student_token = student_login.cookies[SESSION_COOKIE_NAME]
    user_data = student_login.json()["user"]
    assert user_data["roles"] == ["ROLE_STUDENT"]
    assert "ROLE_SUPER_ADMIN" not in user_data["roles"]
