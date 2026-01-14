"""Integration tests for Agent API endpoints.

TAG: [SPEC-009] [TESTS] [API] [AGENT]
REQ: REQ-001 - Agent CRUD Endpoint Tests
REQ: REQ-002 - Agent Tool Association Tests
REQ: REQ-003 - Agent Filtering Tests
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient


# =============================================================================
# Agent Endpoint Tests
# =============================================================================


class TestAgentEndpoints:
    """Test suite for agent API endpoints."""

    @pytest.fixture
    def sample_agent_data(self) -> dict:
        """Sample agent creation data."""
        return {
            "name": "Test Agent",
            "description": "A test AI agent",
            "model_provider": "anthropic",
            "model_name": "claude-3-5-sonnet-20241022",
            "system_prompt": "You are a helpful assistant.",
            "config": {"temperature": 0.7, "max_tokens": 2000},
            "tools": [],
            "memory_config": {"max_turns": 10},
            "is_active": True,
            "is_public": False,
        }

    @pytest.fixture
    async def sample_tool_id(self, async_client: AsyncClient) -> str:
        """Create a sample tool and return its ID."""
        tool_data = {
            "name": "Test Tool",
            "tool_type": "http",
            "config": {"url": "https://api.example.com"},
            "input_schema": {},
        }
        response = await async_client.post("/api/v1/tools/", json=tool_data)
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, async_client: AsyncClient):
        """Test listing agents when none exist."""
        response = await async_client.get("/api/v1/agents/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_agent_success(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test successful agent creation."""
        response = await async_client.post("/api/v1/agents/", json=sample_agent_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test Agent"
        assert data["model_provider"] == "anthropic"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_agent_invalid_data(self, async_client: AsyncClient):
        """Test agent creation with invalid data."""
        response = await async_client.post(
            "/api/v1/agents/",
            json={"name": "", "model_provider": "anthropic", "model_name": "test"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_agent_success(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test successful agent retrieval."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Get agent
        response = await async_client.get(f"/api/v1/agents/{agent_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, async_client: AsyncClient):
        """Test getting non-existent agent returns 404."""
        response = await async_client.get(f"/api/v1/agents/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_agent_success(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test successful agent update."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Update agent
        update_data = {"name": "Updated Agent", "is_active": False}
        response = await async_client.put(f"/api/v1/agents/{agent_id}", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Agent"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_agent_success(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test successful agent deletion."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Delete agent
        response = await async_client.delete(f"/api/v1/agents/{agent_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent agent returns 404."""
        response = await async_client.delete(f"/api/v1/agents/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_success(
        self,
        async_client: AsyncClient,
        sample_agent_data: dict,
        sample_tool_id: str,
    ):
        """Test successfully adding a tool to an agent."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Add tool to agent
        response = await async_client.post(
            f"/api/v1/agents/{agent_id}/tools", json={"tool_id": sample_tool_id}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert sample_tool_id in data["tools"]

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_not_found(self, async_client: AsyncClient):
        """Test adding tool to non-existent agent returns 404."""
        response = await async_client.post(
            f"/api/v1/agents/{uuid4()}/tools", json={"tool_id": str(uuid4())}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_duplicate(
        self,
        async_client: AsyncClient,
        sample_agent_data: dict,
        sample_tool_id: str,
    ):
        """Test adding duplicate tool returns 409."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Add tool first time
        await async_client.post(
            f"/api/v1/agents/{agent_id}/tools", json={"tool_id": sample_tool_id}
        )

        # Try to add again
        response = await async_client.post(
            f"/api/v1/agents/{agent_id}/tools", json={"tool_id": sample_tool_id}
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_remove_tool_from_agent_success(
        self,
        async_client: AsyncClient,
        sample_agent_data: dict,
        sample_tool_id: str,
    ):
        """Test successfully removing a tool from an agent."""
        # Create agent
        create_response = await async_client.post("/api/v1/agents/", json=sample_agent_data)
        agent_id = create_response.json()["id"]

        # Add tool
        await async_client.post(
            f"/api/v1/agents/{agent_id}/tools", json={"tool_id": sample_tool_id}
        )

        # Remove tool
        response = await async_client.delete(
            f"/api/v1/agents/{agent_id}/tools/{sample_tool_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert sample_tool_id not in data["tools"]

    @pytest.mark.asyncio
    async def test_remove_tool_from_agent_not_found(self, async_client: AsyncClient):
        """Test removing tool from non-existent agent returns 404."""
        response = await async_client.delete(
            f"/api/v1/agents/{uuid4()}/tools/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_agents_with_filters(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test agent listing with provider filter."""
        # Create agents
        await async_client.post("/api/v1/agents/", json=sample_agent_data)
        await async_client.post(
            "/api/v1/agents/",
            json={
                **sample_agent_data,
                "name": "OpenAI Agent",
                "model_provider": "openai",
                "model_name": "gpt-4",
            },
        )

        # Filter by provider
        response = await async_client.get("/api/v1/agents/?model_provider=anthropic")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(a["model_provider"] == "anthropic" for a in data["items"])

    @pytest.mark.asyncio
    async def test_list_agents_with_pagination(self, async_client: AsyncClient):
        """Test agent listing with pagination."""
        # Create multiple agents
        for i in range(5):
            await async_client.post(
                "/api/v1/agents/",
                json={
                    "name": f"Agent {i}",
                    "model_provider": "anthropic",
                    "model_name": "claude-3-5-sonnet-20241022",
                    "config": {},
                },
            )

        # List with pagination
        response = await async_client.get("/api/v1/agents/?skip=0&limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
