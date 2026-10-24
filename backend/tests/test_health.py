"""
Unit and Integration tests for Application Health & Root Endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_success(async_client: AsyncClient):
    """Verifies that /api/v1/health returns 200 OK and expected liveness attributes."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ExcelR Track360"
    assert "version" in data
    assert "environment" in data
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint_success(async_client: AsyncClient):
    """Verifies that root '/' returns platform metadata and documentation URLs."""
    response = await async_client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["platform"] == "ExcelR Track360"
    assert data["status"] == "online"
    assert data["docs_url"] == "/api/v1/docs"
    assert data["health_url"] == "/api/v1/health"
    assert data["readiness_url"] == "/api/v1/ready"
