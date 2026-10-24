"""
Unit and Integration tests for Application Readiness Probe.
Verifies genuine dependency validation and failure reporting.
"""
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ready_endpoint_healthy(async_client: AsyncClient):
    """Verifies that /api/v1/ready returns 200 when database connectivity succeeds."""
    mock_success = {
        "connected": True,
        "latency_ms": 1.45,
        "error": None,
    }
    with patch("app.api.v1.endpoints.system.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_success
        response = await async_client.get("/api/v1/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"]["status"] == "connected"
        assert data["database"]["latency_ms"] == 1.45
        assert data["dependencies"]["database"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_endpoint_database_failure(async_client: AsyncClient):
    """
    CRITICAL REQUIREMENT:
    Verifies that /api/v1/ready returns 503 Service Unavailable when the database is unreachable.
    Never returns 200 when the database check has failed.
    """
    mock_failure = {
        "connected": False,
        "latency_ms": None,
        "error": "Connection refused to PostgreSQL host",
    }
    with patch("app.api.v1.endpoints.system.check_db_connectivity", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_failure
        response = await async_client.get("/api/v1/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"]["status"] == "unavailable"
        assert data["database"]["error"] == "Connection refused to PostgreSQL host"
        assert data["dependencies"]["database"] == "unhealthy"
        assert "detail" in data
