"""Integration tests for Agent API endpoints.

TAG: [SPEC-009] [TESTS] [API] [AGENT]
REQ: REQ-001 - Agent CRUD Endpoint Tests
REQ: REQ-002 - Agent Tool Association Tests
REQ: REQ-003 - Agent Filtering Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch
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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
        agent_id = create_response.json()["id"]

        # Update agent
        update_data = {"name": "Updated Agent", "is_active": False}
        response = await async_client.put(
            f"/api/v1/agents/{agent_id}", json=update_data
        )

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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
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
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
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


# =============================================================================
# Mock-Based Exception Handling Tests (Uncovered Paths)
# =============================================================================


class TestAgentAPIExceptionHandling:
    """Mock-based tests for Agent API exception handling paths.

    These tests use unittest.mock to inject exceptions into the service layer,
    testing error handling paths that are difficult to trigger through
    normal integration tests.

    Covers lines:
    - list_agents generic exception (122-126)
    - create_agent service error (152-160)
    - get_agent generic exception (188-200)
    - update_agent generic exception (230-240)
    - delete_agent generic exception (265-274)
    - add_tool_to_agent generic exception (310-325)
    - remove_tool_from_agent generic exception (355-365)
    """

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

    @pytest.mark.asyncio
    async def test_list_agents_generic_exception(self, async_client: AsyncClient):
        """Test list agents returns 500 on unexpected exception.

        Tests lines 122-126 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        from unittest.mock import MagicMock, patch

        mock_service = MagicMock()
        mock_service.list.side_effect = Exception("Database connection failed")

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.get("/api/v1/agents/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database connection failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_agents_count_exception(self, async_client: AsyncClient):
        """Test list agents returns 500 when count() fails.

        Tests lines 122-126 in agents.py where Exception during count()
        is caught and converted to HTTP 500.
        """
        mock_service = MagicMock()
        mock_service.list = AsyncMock(return_value=[])  # List succeeds
        mock_service.count = AsyncMock(side_effect=Exception("Count query failed"))

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.get("/api/v1/agents/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            # The error message may vary depending on implementation
            assert "Count query failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_agent_service_error(self, async_client: AsyncClient):
        """Test create agent returns 400 on AgentServiceError.

        Tests lines 152-160 in agents.py where AgentServiceError
        is caught and converted to HTTP 400.
        """
        from app.services.agent_service import AgentServiceError

        mock_service = MagicMock()
        mock_service.create = AsyncMock(
            side_effect=AgentServiceError("Invalid agent configuration")
        )

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            agent_data = {
                "name": "Test Agent",
                "model_provider": "anthropic",
                "model_name": "claude-3-5-sonnet-20241022",
            }
            response = await async_client.post("/api/v1/agents/", json=agent_data)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid agent configuration" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_agent_generic_exception(self, async_client: AsyncClient):
        """Test get agent returns 500 on unexpected exception.

        Tests lines 188-200 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        agent_id = uuid4()

        mock_service = MagicMock()
        mock_service.get = AsyncMock(side_effect=Exception("Unexpected database error"))

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.get(f"/api/v1/agents/{agent_id}")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Unexpected database error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_agent_generic_exception(self, async_client: AsyncClient):
        """Test update agent returns 500 on unexpected exception.

        Tests lines 230-240 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        agent_id = uuid4()
        update_data = {"name": "Updated Agent"}

        mock_service = MagicMock()
        mock_service.update = AsyncMock(side_effect=Exception("Database update failed"))

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.put(
                f"/api/v1/agents/{agent_id}", json=update_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database update failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_agent_generic_exception(self, async_client: AsyncClient):
        """Test delete agent returns 500 on unexpected exception.

        Tests lines 265-274 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        agent_id = uuid4()

        mock_service = MagicMock()
        mock_service.delete = AsyncMock(
            side_effect=Exception("Database deletion failed")
        )

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.delete(f"/api/v1/agents/{agent_id}")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database deletion failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_generic_exception(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test add tool to agent returns 500 on unexpected exception.

        Tests lines 310-325 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        # Create agent first
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
        agent_id = create_response.json()["id"]
        tool_id = uuid4()

        mock_service = MagicMock()
        mock_service.add_tool = AsyncMock(
            side_effect=Exception("Tool association failed")
        )

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.post(
                f"/api/v1/agents/{agent_id}/tools", json={"tool_id": str(tool_id)}
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Tool association failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_tool_from_agent_generic_exception(
        self, async_client: AsyncClient, sample_agent_data: dict
    ):
        """Test remove tool from agent returns 500 on unexpected exception.

        Tests lines 355-365 in agents.py where generic Exception
        is caught and converted to HTTP 500.
        """
        # Create agent first
        create_response = await async_client.post(
            "/api/v1/agents/", json=sample_agent_data
        )
        agent_id = create_response.json()["id"]
        tool_id = uuid4()

        mock_service = MagicMock()
        mock_service.remove_tool = AsyncMock(
            side_effect=Exception("Tool removal failed")
        )

        with patch("app.api.v1.agents.AgentService", return_value=mock_service):
            response = await async_client.delete(
                f"/api/v1/agents/{agent_id}/tools/{tool_id}"
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Tool removal failed" in response.json()["detail"]
