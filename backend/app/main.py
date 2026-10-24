"""
ExcelR Track360 - Backend Application Entry Point
Initializes FastAPI, configures CORS, mounts routers, and registers RFC 7807 error handlers.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import check_db_connectivity, close_database_connections
from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import logger, setup_logging

settings = get_settings()
setup_logging(debug=settings.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Safely probes infrastructure at startup and tears down connections at shutdown.
    Startup NEVER crashes if DB is unreachable; logs status for readiness probing.
    """
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    logger.info(f"API v1 prefix: {settings.API_V1_PREFIX}")
    logger.info(f"Target Database: {settings.masked_database_url}")
    
    # Safe startup probe
    db_status = await check_db_connectivity()
    if db_status["connected"]:
        logger.info(f"Database connection verified successfully (Latency: {db_status['latency_ms']}ms)")
    else:
        logger.warning(
            f"Database currently unreachable ({db_status['error']}). "
            "Application startup proceeding; /api/v1/ready will report 503 until database is available."
        )
        
    yield
    
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_database_connections()
    logger.info("Shutdown cleanup complete.")


def create_application() -> FastAPI:
    """Factory function creating and configuring the FastAPI application instance."""
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description="Student Lifecycle & Operations Management Platform API",
        version="0.1.0",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )
    
    # Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register RFC 7807 Error Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    # Mount API v1 Master Router
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
    
    # Root Landing Route
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "platform": settings.APP_NAME,
            "status": "online",
            "version": "0.1.0",
            "docs_url": f"{settings.API_V1_PREFIX}/docs",
            "health_url": f"{settings.API_V1_PREFIX}/health",
            "readiness_url": f"{settings.API_V1_PREFIX}/ready",
        }
        
    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
