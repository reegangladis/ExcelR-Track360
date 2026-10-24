"""
ExcelR Track360 - System Health & Readiness Endpoints
Provides infrastructure probes for application liveness and dependency readiness.
"""
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.database import check_db_connectivity
from app.core.logging import logger

router = APIRouter(tags=["System"])
settings = get_settings()

START_TIME = datetime.now(timezone.utc)


@router.get("/health", status_code=status.HTTP_200_OK)
async def get_health() -> Dict[str, Any]:
    """
    Liveness probe: Reports application process health, uptime, and metadata.
    Returns HTTP 200 as long as the FastAPI process is responsive.
    """
    now = datetime.now(timezone.utc)
    uptime_seconds = int((now - START_TIME).total_seconds())
    
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "0.1.0",
        "uptime_seconds": uptime_seconds,
        "timestamp": now.isoformat(),
    }


@router.get("/ready")
async def get_readiness(response: Response) -> Dict[str, Any]:
    """
    Readiness probe: Verifies critical dependencies (specifically PostgreSQL connectivity).
    Returns HTTP 200 if dependencies are ready to accept traffic.
    Returns HTTP 503 Service Unavailable if any critical dependency is unreachable.
    NEVER returns a successful readiness result if the database check has failed.
    """
    now = datetime.now(timezone.utc)
    db_result = await check_db_connectivity()
    
    if db_result["connected"]:
        return {
            "status": "ready",
            "environment": settings.APP_ENV,
            "database": {
                "status": "connected",
                "latency_ms": db_result["latency_ms"],
                "target": f"{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}",
            },
            "dependencies": {
                "database": "healthy",
            },
            "timestamp": now.isoformat(),
        }
    else:
        # Mark response as 503 Service Unavailable
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning(f"Readiness probe failed: database unreachable ({db_result.get('error')})")
        
        return {
            "status": "not_ready",
            "environment": settings.APP_ENV,
            "database": {
                "status": "unavailable",
                "error": db_result["error"],
                "target": f"{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}",
            },
            "dependencies": {
                "database": "unhealthy",
            },
            "detail": "Database connectivity check failed. Service is not ready to handle operational traffic.",
            "timestamp": now.isoformat(),
        }
