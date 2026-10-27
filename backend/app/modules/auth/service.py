"""
ExcelR Track360 - Authentication & Session Service
Implements server-managed session lifecycle, Argon2id verification,
brute-force account lockout, concurrent session limits, and password resets.
Adheres strictly to SEC-TRK360-V1.0 and URP-TRK360-V1.0.
"""
from datetime import timedelta
from typing import List, Optional, Tuple, Set
import uuid
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.logging import logger
from app.core.security import (
    hash_password,
    verify_password,
    generate_secure_token,
    hash_token,
    generate_csrf_token,
    utc_now,
)
from app.modules.auth.models import User, UserSession, PasswordResetToken, Role, Permission
from app.modules.audit.models import AuditLog

# Session lifetime constants
STAFF_SESSION_DURATION = timedelta(hours=24)
STUDENT_SESSION_DURATION = timedelta(days=14)
IDLE_SESSION_TIMEOUT = timedelta(hours=8)
MAX_CONCURRENT_SESSIONS = 3
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
RESET_TOKEN_LIFETIME = timedelta(hours=1)


class AuthService:
    """Core Authentication and Session Management Service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """
        Authenticates user with email and password.
        Enforces account lockout policy (5 failed attempts -> 15 min lock).
        Uses generic error messages to eliminate account enumeration vectors.
        """
        normalized_email = email.lower().strip()
        now = utc_now()

        # Fetch user
        stmt = select(User).where(User.email == normalized_email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            # Constant-time dummy verify to prevent timing enumeration
            verify_password("dummy_password", "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check account lockout
        if user.locked_until and user.locked_until > now:
            minutes_remaining = max(1, int((user.locked_until - now).total_seconds() / 60))
            logger.warning(f"Blocked login attempt on locked account: {normalized_email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is temporarily locked. Please try again in {minutes_remaining} minutes.",
            )

        # Check account status
        if user.status != "ACTIVE":
            logger.warning(f"Login attempted on inactive account: {normalized_email} (status: {user.status})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive or suspended. Please contact platform administration.",
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = now + LOCKOUT_DURATION
                logger.warning(f"Account locked due to {user.failed_login_attempts} failed attempts: {normalized_email}")
                # Audit log for lockout
                self.db.add(AuditLog(
                    actor_user_id=user.id,
                    actor_ip_address=ip_address,
                    actor_user_agent=user_agent,
                    action_type="AUTH_ACCOUNT_LOCKED",
                    entity_type="users",
                    entity_id=user.id,
                    justification=f"Brute-force lockout triggered after {user.failed_login_attempts} failed attempts",
                ))

            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Successful authentication: reset failed attempts & update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, UserSession, str]:
        """
        Creates a new server-managed session.
        Enforces concurrent session limit (max 3 concurrent active sessions).
        Returns (raw_session_token, user_session_model, csrf_token).
        """
        now = utc_now()
        role_codes = [r.code for r in user.roles]
        is_student = "ROLE_STUDENT" in role_codes and len(role_codes) == 1
        duration = STUDENT_SESSION_DURATION if is_student else STAFF_SESSION_DURATION

        # Query existing active sessions
        active_sessions_stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.is_revoked == False,
                UserSession.expires_at > now,
            )
            .order_by(UserSession.created_at.asc())
        )
        active_sessions = (await self.db.execute(active_sessions_stmt)).scalars().all()

        # Invalidate oldest session if at concurrent limit
        if len(active_sessions) >= MAX_CONCURRENT_SESSIONS:
            oldest = active_sessions[0]
            oldest.is_revoked = True
            logger.info(f"Revoked oldest session {oldest.id} for user {user.id} due to concurrent limit")

        # Generate tokens
        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)
        csrf_token = generate_csrf_token()

        new_session = UserSession(
            user_id=user.id,
            session_token_hash=token_hash,
            csrf_token=csrf_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + duration,
            last_activity_at=now,
            is_revoked=False,
        )
        self.db.add(new_session)

        # Audit log login event
        self.db.add(AuditLog(
            actor_user_id=user.id,
            actor_ip_address=ip_address,
            actor_user_agent=user_agent,
            action_type="AUTH_LOGIN_SUCCESS",
            entity_type="user_sessions",
            entity_id=new_session.id,
            justification="User authenticated and session established",
        ))

        await self.db.commit()
        await self.db.refresh(new_session)

        return raw_token, new_session, csrf_token

    async def get_session_by_token(self, raw_token: str) -> Optional[Tuple[UserSession, User]]:
        """
        Retrieves active session and associated user by raw session token.
        Enforces expiration, revocation, and idle timeouts.
        Updates last_activity_at on valid requests.
        """
        if not raw_token:
            return None

        token_hash = hash_token(raw_token)
        now = utc_now()

        stmt = select(UserSession).where(
            UserSession.session_token_hash == token_hash,
            UserSession.is_revoked == False,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session is None:
            return None

        # Check hard expiration
        if session.expires_at <= now:
            session.is_revoked = True
            await self.db.commit()
            return None

        # Check idle timeout (8 hours)
        if session.last_activity_at + IDLE_SESSION_TIMEOUT <= now:
            session.is_revoked = True
            await self.db.commit()
            return None

        # Fetch associated user
        user_stmt = select(User).where(User.id == session.user_id)
        user = (await self.db.execute(user_stmt)).scalar_one_or_none()

        if user is None or user.status != "ACTIVE":
            session.is_revoked = True
            await self.db.commit()
            return None

        # Bump activity timestamp
        session.last_activity_at = now
        await self.db.commit()

        return session, user

    async def revoke_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Revokes a specific session owned by the user."""
        stmt = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if session and not session.is_revoked:
            session.is_revoked = True
            self.db.add(AuditLog(
                actor_user_id=user_id,
                actor_ip_address=ip_address,
                actor_user_agent=user_agent,
                action_type="AUTH_LOGOUT",
                entity_type="user_sessions",
                entity_id=session.id,
                justification="User logged out or revoked session",
            ))
            await self.db.commit()
            return True
        return False

    async def list_user_sessions(self, user_id: uuid.UUID) -> List[UserSession]:
        """Returns all non-revoked active sessions for the user."""
        now = utc_now()
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False,
                UserSession.expires_at > now,
            )
            .order_by(desc(UserSession.created_at))
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def request_password_reset(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Creates a time-limited password reset token.
        Always returns generic message to prevent account enumeration.
        Returns raw token for dev/testing.
        """
        normalized_email = email.lower().strip()
        user = (
            await self.db.execute(select(User).where(User.email == normalized_email))
        ).scalar_one_or_none()

        if user is None:
            return None

        # Invalidate prior unused tokens
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.is_used == False)
            .values(is_used=True)
        )

        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)
        now = utc_now()

        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + RESET_TOKEN_LIFETIME,
            is_used=False,
        )
        self.db.add(reset_record)

        self.db.add(AuditLog(
            actor_user_id=user.id,
            actor_ip_address=ip_address,
            actor_user_agent=user_agent,
            action_type="AUTH_PASSWORD_RESET_REQUESTED",
            entity_type="users",
            entity_id=user.id,
            justification="Password reset token generated",
        ))

        await self.db.commit()
        return raw_token

    async def confirm_password_reset(
        self,
        raw_token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Validates reset token, updates password with Argon2id, and revokes all active sessions.
        """
        token_hash = hash_token(raw_token)
        now = utc_now()

        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used == False,
        )
        record = (await self.db.execute(stmt)).scalar_one_or_none()

        if record is None or record.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        # Mark token used
        record.is_used = True

        # Update user password
        user = (await self.db.execute(select(User).where(User.id == record.user_id))).scalar_one()
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = now

        # Revoke all active sessions for security
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.is_revoked == False)
            .values(is_revoked=True)
        )

        self.db.add(AuditLog(
            actor_user_id=user.id,
            actor_ip_address=ip_address,
            actor_user_agent=user_agent,
            action_type="AUTH_PASSWORD_RESET_CONFIRMED",
            entity_type="users",
            entity_id=user.id,
            justification="Password successfully updated; active sessions revoked",
        ))

        await self.db.commit()

    @staticmethod
    def extract_permissions_and_roles(user: User) -> Tuple[List[str], List[str]]:
        """Calculates deduplicated role codes and permission codes for a user."""
        roles = [r.code for r in user.roles]
        permissions: Set[str] = set()
        for r in user.roles:
            for p in r.permissions:
                permissions.add(p.code)
        return roles, sorted(list(permissions))
