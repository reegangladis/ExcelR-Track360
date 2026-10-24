"""
Unit tests for Configuration, Environment Validation & Secret Masking.
"""
from app.core.config import Settings


def test_settings_defaults():
    """Verifies that default settings load with expected values."""
    settings = Settings()
    assert settings.APP_NAME == "ExcelR Track360"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.DATABASE_PORT == 5432
    assert "postgresql+asyncpg://" in settings.async_database_url
    assert "postgresql://" in settings.sync_database_url


def test_settings_masked_database_url():
    """Verifies that the database password is NEVER exposed in the masked URL."""
    settings = Settings(
        DATABASE_USER="test_user",
        DATABASE_PASSWORD="super_secret_password_123",
        DATABASE_HOST="db.internal",
        DATABASE_PORT=5432,
        DATABASE_NAME="track360_test",
    )
    masked = settings.masked_database_url
    assert "super_secret_password_123" not in masked
    assert "******" in masked
    assert "test_user" in masked
    assert "db.internal" in masked


def test_settings_cors_origins_parsing():
    """Verifies that CORS origins properly parse both JSON array strings and lists."""
    settings_json = Settings(CORS_ORIGINS='["http://localhost:3000","http://localhost:5173"]')
    assert "http://localhost:3000" in settings_json.CORS_ORIGINS
    assert "http://localhost:5173" in settings_json.CORS_ORIGINS
    
    settings_comma = Settings(CORS_ORIGINS="http://localhost:3000, http://example.com")
    assert "http://localhost:3000" in settings_comma.CORS_ORIGINS
    assert "http://example.com" in settings_comma.CORS_ORIGINS
