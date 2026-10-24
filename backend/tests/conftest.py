"""
ExcelR Track360 - Pytest Fixtures & Test Setup
Configures AsyncClient, test settings, and database mocking fixtures.
"""
import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_application


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Returns dedicated test configuration."""
    return Settings(
        APP_ENV="test",
        DEBUG=True,
        DATABASE_TIMEOUT_SECONDS=1.0,
        SECRET_KEY="test-secret-key-for-automated-suites",
    )


@pytest.fixture
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Provides an AsyncClient bound to the FastAPI application instance."""
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
