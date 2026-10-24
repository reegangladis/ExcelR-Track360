"""
Unit tests for RFC 7807 Problem Details Error Responses.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_404_problem_details(async_client: AsyncClient):
    """Verifies that accessing an unknown route returns an RFC 7807 Problem Details envelope."""
    response = await async_client.get("/api/v1/non-existent-route-999")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    
    data = response.json()
    assert "type" in data
    assert data["status"] == 404
    assert "title" in data
    assert "detail" in data
    assert data["instance"] == "/api/v1/non-existent-route-999"
    assert data["code"] == "ERR_NOT_FOUND"
    assert "timestamp" in data
