"""Integration tests for Tool API endpoints.

TAG: [SPEC-009] [TESTS] [API] [TOOL]
REQ: REQ-001 - Tool CRUD Endpoint Tests
REQ: REQ-002 - Tool Test Execution Tests
REQ: REQ-003 - Tool Filtering Tests
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient


# =============================================================================
# Tool Endpoint Tests
# =============================================================================


class TestToolEndpoints:
    """Test suite for tool API endpoints."""

    @pytest.fixture
    def sample_tool_data(self) -> dict:
        """Sample tool creation data."""
        return {
            "name": "Test HTTP Tool",
            "description": "A test HTTP API tool",
            "tool_type": "http",
            "config": {
                "url": "https://api.example.com/endpoint",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                },
            },
            "auth_config": {"api_key": "test_key"},
            "rate_limit": {"max_calls": 100, "period": "hour"},
            "is_active": True,
            "is_public": False,
        }

    @pytest.mark.asyncio
    async def test_list_tools_empty(self, async_client: AsyncClient):
        """Test listing tools when none exist."""
        response = await async_client.get("/api/v1/tools/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_tool_success(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test successful tool creation."""
        response = await async_client.post("/api/v1/tools/", json=sample_tool_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test HTTP Tool"
        assert data["tool_type"] == "http"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_tool_invalid_data(self, async_client: AsyncClient):
        """Test tool creation with invalid data."""
        response = await async_client.post(
            "/api/v1/tools/", json={"name": "", "tool_type": "http", "config": {}}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_tool_success(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test successful tool retrieval."""
        # Create tool
        create_response = await async_client.post("/api/v1/tools/", json=sample_tool_data)
        tool_id = create_response.json()["id"]

        # Get tool
        response = await async_client.get(f"/api/v1/tools/{tool_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == tool_id
        assert data["name"] == "Test HTTP Tool"

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, async_client: AsyncClient):
        """Test getting non-existent tool returns 404."""
        response = await async_client.get(f"/api/v1/tools/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_tool_success(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test successful tool update."""
        # Create tool
        create_response = await async_client.post("/api/v1/tools/", json=sample_tool_data)
        tool_id = create_response.json()["id"]

        # Update tool
        update_data = {"name": "Updated Tool", "is_active": False}
        response = await async_client.put(f"/api/v1/tools/{tool_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Tool"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_tool_success(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test successful tool deletion."""
        # Create tool
        create_response = await async_client.post("/api/v1/tools/", json=sample_tool_data)
        tool_id = create_response.json()["id"]

        # Delete tool
        response = await async_client.delete(f"/api/v1/tools/{tool_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_tool_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent tool returns 404."""
        response = await async_client.delete(f"/api/v1/tools/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_test_tool_execution_success(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test successful tool test execution."""
        # Create tool
        create_response = await async_client.post("/api/v1/tools/", json=sample_tool_data)
        tool_id = create_response.json()["id"]

        # Test tool
        test_request = {"input_data": {"query": "test"}}
        response = await async_client.post(
            f"/api/v1/tools/{tool_id}/test", json=test_request
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success" in data
        assert "execution_time_ms" in data

    @pytest.mark.asyncio
    async def test_test_tool_not_found(self, async_client: AsyncClient):
        """Test testing non-existent tool returns 404."""
        test_request = {"input_data": {"query": "test"}}
        response = await async_client.post(
            f"/api/v1/tools/{uuid4()}/test", json=test_request
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_tools_with_filters(
        self, async_client: AsyncClient, sample_tool_data: dict
    ):
        """Test tool listing with type filter."""
        # Create tools
        await async_client.post("/api/v1/tools/", json=sample_tool_data)
        await async_client.post(
            "/api/v1/tools/",
            json={
                **sample_tool_data,
                "name": "Python Tool",
                "tool_type": "python",
                "config": {"code": "print('test')"},
            },
        )

        # Filter by tool type
        response = await async_client.get("/api/v1/tools/?tool_type=http")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(t["tool_type"] == "http" for t in data["items"])

    @pytest.mark.asyncio
    async def test_list_tools_with_pagination(self, async_client: AsyncClient):
        """Test tool listing with pagination."""
        # Create multiple tools
        for i in range(5):
            await async_client.post(
                "/api/v1/tools/",
                json={
                    "name": f"Tool {i}",
                    "tool_type": "http",
                    "config": {},
                    "input_schema": {},
                },
            )

        # List with pagination
        response = await async_client.get("/api/v1/tools/?skip=0&limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
