"""
ExcelR Track360 - Database Connection & Session Infrastructure
Provides asynchronous PostgreSQL connectivity via SQLAlchemy 2.0 and asyncpg.
Includes safe health probes and connection lifecycle management.
"""
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


# Global engine instance
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Returns or initializes the global async SQLAlchemy engine."""
    global _engine, _session_factory
    if _engine is None:
        logger.info(f"Initializing async database engine: {settings.masked_database_url}")
        _engine = create_async_engine(
            settings.async_database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_TIMEOUT_SECONDS,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns the async session factory."""
    global _session_factory
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session within a transaction scope."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connectivity() -> Dict[str, Any]:
    """
    Safely verifies database connectivity by executing 'SELECT 1'.
    Measures query latency and captures errors without crashing the caller.
    """
    engine = get_engine()
    start_time = time.perf_counter()
    try:
        # Wrap connection attempt with a strict timeout
        async with asyncio.timeout(settings.DATABASE_TIMEOUT_SECONDS):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": True,
            "latency_ms": elapsed_ms,
            "error": None,
        }
    except asyncio.TimeoutError:
        logger.warning(f"Database connectivity check timed out after {settings.DATABASE_TIMEOUT_SECONDS}s")
        return {
            "connected": False,
            "latency_ms": None,
            "error": f"Connection timed out after {settings.DATABASE_TIMEOUT_SECONDS}s",
        }
    except Exception as exc:
        logger.warning(f"Database connectivity check failed: {str(exc)}")
        return {
            "connected": False,
            "latency_ms": None,
            "error": str(exc),
        }


async def close_database_connections() -> None:
    """Closes all active database pool connections on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Disposing database connection pool...")
        await _engine.dispose()
        _engine = None
        _session_factory = None
