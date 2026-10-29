"""
ExcelR Track360 - Pytest Fixtures & Test Setup
Configures AsyncClient, test settings, and database mocking fixtures.
"""
import os
import sys
import asyncio
import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient

# Enforce test environment variables before settings/engine are loaded
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_NAME"] = "track360_test"
os.environ["DATABASE_PORT"] = "5433"

from app.core.config import Settings, get_settings
from app.main import create_application
from app.core.database import get_session_factory, close_database_connections
from app.modules.auth.seed import seed_bootstrap_admin


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Returns dedicated test configuration."""
    s = Settings(
        APP_ENV="test",
        DEBUG=True,
        DATABASE_PORT=5433,
        DATABASE_NAME="track360_test",
        DATABASE_TIMEOUT_SECONDS=3.0,
        SECRET_KEY="test-secret-key-for-automated-suites",
    )
    get_settings.cache_clear()
    return s


@pytest.fixture
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient bound to the FastAPI application instance."""
    app = create_application()
    app.dependency_overrides[get_settings] = lambda: test_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Seeds default admin before every test and cleans connections cleanly on the active loop."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_bootstrap_admin(
            db=session,
            email="admin@excelr.com",
            password="Admin@Track360_2026!",
            full_name="Master Administrator",
        )
    yield
    await close_database_connections()
