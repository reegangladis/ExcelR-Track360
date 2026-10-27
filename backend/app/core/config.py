"""
ExcelR Track360 - Centralized Configuration Module
Validates environment settings at startup via Pydantic Settings.
"""
from functools import lru_cache
from typing import List, Union
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration schema with strict environment validation."""
    
    # Application Metadata
    APP_ENV: str = Field(default="development", description="Environment: development, test, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    APP_NAME: str = Field(default="ExcelR Track360", description="Application display name")
    API_V1_PREFIX: str = Field(default="/api/v1", description="Global prefix for v1 API routes")
    HOST: str = Field(default="0.0.0.0", description="Bind host")
    PORT: int = Field(default=8000, description="Bind port")
    
    # Security
    SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production-min-32-chars",
        description="Session encryption and token signing key"
    )
    
    # Database Settings
    DATABASE_HOST: str = Field(default="localhost", description="PostgreSQL host")
    DATABASE_PORT: int = Field(default=5433, description="PostgreSQL port")
    DATABASE_USER: str = Field(default="track360_user", description="PostgreSQL username")
    DATABASE_PASSWORD: str = Field(default="track360_secure_pass", description="PostgreSQL password")
    DATABASE_NAME: str = Field(default="track360_dev", description="PostgreSQL database name")
    DATABASE_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=5, description="Database pool max overflow")
    DATABASE_TIMEOUT_SECONDS: float = Field(default=3.0, description="Connection timeout in seconds")
    
    # CORS Settings
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins"
    )
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    @property
    def async_database_url(self) -> str:
        """Constructs asynchronous PostgreSQL URL for SQLAlchemy 2.0 with asyncpg."""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Constructs synchronous PostgreSQL URL for Alembic migrations."""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def masked_database_url(self) -> str:
        """Returns safe connection string for logging with password masked."""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:******@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
        
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns cached application settings instance."""
    return Settings()
