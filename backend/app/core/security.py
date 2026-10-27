"""
ExcelR Track360 - Cryptographic & Security Utilities
Implements Argon2id password hashing, high-entropy token generation,
SHA-256 token hashing for server-managed sessions, and CSRF token handling.
Strictly adheres to SEC-TRK360-V1.0 specifications.
"""
from datetime import datetime, timezone
import hashlib
import secrets
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.core.logging import logger

# Initialize Argon2id password hasher with parameters aligned with SEC-TRK360-V1.0
# time_cost: 3 iterations, memory_cost: 65536 KiB (64 MB), parallelism: 4 threads
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against an Argon2id hash.
    Returns False on verification failure or invalid hash format without leaking timing info.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.warning(f"Unexpected error during password verification: {exc}")
        return False


def generate_secure_token(nbytes: int = 32) -> str:
    """Generates a high-entropy URL-safe token for session identifiers and reset tokens."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """Returns SHA-256 hex digest of a token for secure database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generates a cryptographically random hexadecimal CSRF token."""
    return secrets.token_hex(32)


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
