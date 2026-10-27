"""
ExcelR Track360 - Pytest Fixtures & Test Setup
Configures AsyncClient, test settings, and database mocking fixtures.
"""
import sys
import asyncio
import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient


from app.core.config import Settings, get_settings
from app.main import create_application


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
    from app.core.database import close_database_connections
    await close_database_connections()
