"""Integration tests for Workflow API endpoints.

TAG: [SPEC-007] [TESTS] [API] [WORKFLOW]
REQ: REQ-001 - Workflow CRUD Endpoint Tests
REQ: REQ-002 - Node CRUD Endpoint Tests
REQ: REQ-003 - Edge CRUD Endpoint Tests
REQ: REQ-004 - Graph Update Endpoint Tests
REQ: REQ-005 - Edge CRUD Error Path Mock Tests (Categories 9-12)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.services.workflow_service import (
    DAGValidationError,
    InvalidNodeReferenceError,
)

# =============================================================================
# Workflow Endpoint Tests
# =============================================================================


class TestWorkflowEndpoints:
    """Test suite for workflow API endpoints."""

    @pytest.mark.asyncio
    async def test_list_workflows_empty(self, async_client: AsyncClient):
        """Test listing workflows when none exist."""
        response = await async_client.get("/api/v1/workflows/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_workflow_success(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test successful workflow creation."""
        response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test Workflow"
        assert data["is_active"] is True
        assert data["version"] == 1

    @pytest.mark.asyncio
    async def test_create_workflow_invalid_data(self, async_client: AsyncClient):
        """Test workflow creation with invalid data."""
        response = await async_client.post(
            "/api/v1/workflows/", json={"name": "", "description": "Test"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_workflow_success(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test successful workflow retrieval."""
        # First create a workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]

        # Then get it
        response = await async_client.get(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == workflow_id
        assert data["name"] == "Test Workflow"

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, async_client: AsyncClient):
        """Test getting non-existent workflow returns 404."""
        response = await async_client.get(f"/api/v1/workflows/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_workflow_full(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test getting workflow with full details including nodes and edges."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]

        # Get full workflow
        response = await async_client.get(f"/api/v1/workflows/{workflow_id}/full")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["id"] == workflow_id

    @pytest.mark.asyncio
    async def test_update_workflow_success(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test successful workflow update."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Update workflow
        update_data = {
            "name": "Updated Workflow",
            "description": "Updated description",
            "version": version,
        }
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Workflow"
        assert data["version"] == version + 1

    @pytest.mark.asyncio
    async def test_update_workflow_version_conflict(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test update with wrong version returns 409."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]

        # Update with wrong version
        update_data = {"name": "Updated", "version": 999}
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}", json=update_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_delete_workflow_success(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test successful workflow deletion."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]

        # Delete workflow
        response = await async_client.delete(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_duplicate_workflow_success(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test successful workflow duplication."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]

        # Duplicate workflow
        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/duplicate",
            params={"name": "Duplicate Workflow"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] != workflow_id
        assert data["name"] == "Duplicate Workflow"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_list_workflows_with_pagination(self, async_client: AsyncClient):
        """Test workflow listing with pagination."""
        # Create multiple workflows
        for i in range(5):
            await async_client.post(
                "/api/v1/workflows/",
                json={"name": f"Workflow {i}", "description": f"Test {i}"},
            )

        # List with pagination
        response = await async_client.get("/api/v1/workflows/?skip=0&limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["size"] == 2

    @pytest.mark.asyncio
    async def test_list_workflows_with_filter(self, async_client: AsyncClient):
        """Test workflow listing with active filter."""
        # Create active and inactive workflows
        await async_client.post(
            "/api/v1/workflows/", json={"name": "Active", "is_active": True}
        )
        await async_client.post(
            "/api/v1/workflows/", json={"name": "Inactive", "is_active": False}
        )

        # Filter by active status
        response = await async_client.get("/api/v1/workflows/?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(w["is_active"] for w in data["items"])


# =============================================================================
# Node Endpoint Tests
# =============================================================================


class TestNodeEndpoints:
    """Test suite for node API endpoints."""

    @pytest.fixture
    async def workflow_id(self, async_client: AsyncClient, sample_workflow_data):
        """Create a workflow and return its ID."""
        response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_create_node_success(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test successful node creation."""
        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["name"] == "Test Node"
        assert data["workflow_id"] == workflow_id

    @pytest.mark.asyncio
    async def test_create_node_invalid_workflow(
        self, async_client: AsyncClient, sample_node_data
    ):
        """Test node creation with invalid workflow ID."""
        response = await async_client.post(
            f"/api/v1/workflows/{uuid4()}/nodes", json=sample_node_data
        )

        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        )

    @pytest.mark.asyncio
    async def test_list_nodes_empty(self, async_client: AsyncClient, workflow_id: str):
        """Test listing nodes when none exist."""
        response = await async_client.get(f"/api/v1/workflows/{workflow_id}/nodes")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_batch_create_nodes(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test batch creating nodes."""
        batch_data = {
            "nodes": [
                {**sample_node_data, "name": "Node 1"},
                {**sample_node_data, "name": "Node 2"},
                {**sample_node_data, "name": "Node 3"},
            ]
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes/batch", json=batch_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_get_node_success(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test successful node retrieval."""
        # Create node
        create_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
        )
        node_id = create_response.json()["id"]

        # Get node
        response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == node_id

    @pytest.mark.asyncio
    async def test_update_node_success(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test successful node update."""
        # Create node
        create_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
        )
        node_id = create_response.json()["id"]

        # Update node
        update_data = {"name": "Updated Node", "position_x": 500.0}
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/nodes/{node_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Node"
        assert data["position_x"] == 500.0

    @pytest.mark.asyncio
    async def test_delete_node_success(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test successful node deletion."""
        # Create node
        create_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
        )
        node_id = create_response.json()["id"]

        # Delete node
        response = await async_client.delete(
            f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# Edge Endpoint Tests
# =============================================================================


class TestEdgeEndpoints:
    """Test suite for edge API endpoints."""

    @pytest.fixture
    async def workflow_with_nodes(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Create a workflow with nodes and return IDs."""
        # Create workflow
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        # Create nodes (using trigger type which doesn't require tool_id)
        node_data = {
            "name": "Test Node",
            "node_type": "trigger",
            "position_x": 100.0,
            "position_y": 200.0,
        }

        node1_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=node_data
        )
        node1_id = node1_response.json()["id"]

        node2_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=node_data
        )
        node2_id = node2_response.json()["id"]

        return workflow_id, node1_id, node2_id

    @pytest.mark.asyncio
    async def test_create_edge_success(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test successful edge creation."""
        workflow_id, node1_id, node2_id = workflow_with_nodes

        edge_data = {
            "source_node_id": node1_id,
            "target_node_id": node2_id,
            "source_handle": "output",
            "target_handle": "input",
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["source_node_id"] == node1_id
        assert data["target_node_id"] == node2_id

    @pytest.mark.asyncio
    async def test_create_edge_self_loop(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test edge creation with self-loop fails validation."""
        workflow_id, node1_id, _ = workflow_with_nodes

        edge_data = {
            "source_node_id": node1_id,
            "target_node_id": node1_id,  # Same node
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_edges_empty(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test listing edges when none exist."""
        workflow_id, _, _ = workflow_with_nodes

        response = await async_client.get(f"/api/v1/workflows/{workflow_id}/edges")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_batch_create_edges(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test batch creating edges."""
        workflow_id, node1_id, node2_id = workflow_with_nodes

        # Create third node
        node_data = {
            "name": "Node 3",
            "node_type": "tool",
            "position_x": 300.0,
            "position_y": 400.0,
            "tool_id": str(uuid4()),
        }
        node3_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=node_data
        )
        node3_id = node3_response.json()["id"]

        batch_data = {
            "edges": [
                {"source_node_id": node1_id, "target_node_id": node2_id},
                {"source_node_id": node2_id, "target_node_id": node3_id},
            ]
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges/batch", json=batch_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_delete_edge_success(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test successful edge deletion."""
        workflow_id, node1_id, node2_id = workflow_with_nodes

        # Create edge
        edge_data = {"source_node_id": node1_id, "target_node_id": node2_id}
        create_response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )
        edge_id = create_response.json()["id"]

        # Delete edge
        response = await async_client.delete(
            f"/api/v1/workflows/{workflow_id}/edges/{edge_id}"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# Graph Update Endpoint Tests
# =============================================================================


class TestGraphUpdateEndpoint:
    """Test suite for workflow graph update endpoint."""

    @pytest.mark.asyncio
    async def test_update_workflow_graph(
        self, async_client: AsyncClient, sample_workflow_data, sample_node_data
    ):
        """Test updating entire workflow graph."""
        # Create workflow
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]
        version = workflow_response.json()["version"]

        # Create nodes for graph
        node1_id = str(uuid4())
        node2_id = str(uuid4())

        graph_data = {
            "version": version,
            "nodes": [
                {
                    **sample_node_data,
                    "id": node1_id,
                    "name": "Node 1",
                    "tool_id": str(uuid4()),
                },
                {
                    **sample_node_data,
                    "id": node2_id,
                    "name": "Node 2",
                    "tool_id": str(uuid4()),
                },
            ],
            "edges": [
                {
                    "source_node_id": node1_id,
                    "target_node_id": node2_id,
                }
            ],
        }

        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph", json=graph_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    @pytest.mark.asyncio
    async def test_update_graph_version_conflict(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test graph update with version conflict."""
        # Create workflow
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        graph_data = {
            "version": 999,  # Wrong version
            "nodes": [],
            "edges": [],
        }

        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph", json=graph_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# Mock-Based Node CRUD Error Tests (Uncovered Paths - Categories 5-8)
# =============================================================================


class TestNodeEndpointsMock:
    """Mock-based tests for Node API endpoint error paths.

    These tests cover uncovered code paths in workflows.py by mocking
    service layer responses to trigger specific error conditions.
    """

    @pytest.mark.asyncio
    async def test_batch_create_nodes_workflow_not_found_mock(
        self, async_client: AsyncClient
    ):
        """Test batch create nodes returns 404 when workflow not found (mock).

        Tests lines 518-528 in workflows.py where WorkflowNotFoundError
        is raised during batch node creation.
        """
        workflow_id = uuid4()
        batch_data = {
            "nodes": [
                {
                    "name": "Node 1",
                    "node_type": "trigger",
                    "position_x": 100.0,
                    "position_y": 200.0,
                }
            ]
        }

        # Import and mock the NodeService in the router module
        with patch("app.api.v1.workflows.NodeService") as mock_node_service_class:
            from app.services.workflow_service import WorkflowNotFoundError

            mock_service_instance = MagicMock()
            mock_service_instance.batch_create = AsyncMock(
                side_effect=WorkflowNotFoundError(str(workflow_id))
            )
            mock_node_service_class.return_value = mock_service_instance

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/nodes/batch", json=batch_data
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert str(workflow_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_node_workflow_not_found_mock(self, async_client: AsyncClient):
        """Test get node returns 404 when workflow not found (mock).

        Tests lines 555-563 in workflows.py where workflow check fails
        before attempting to get the node.
        """
        workflow_id = uuid4()
        node_id = uuid4()

        # Mock WorkflowService.get() to return None (workflow not found)
        with patch(
            "app.api.v1.workflows.WorkflowService"
        ) as mock_workflow_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.get = AsyncMock(return_value=None)
            mock_workflow_service_class.return_value = mock_service_instance

            response = await async_client.get(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Workflow" in response.json()["detail"]
            assert str(workflow_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_node_not_found_mock(self, async_client: AsyncClient):
        """Test get node returns 404 when node not found (mock).

        Tests lines 566-571 in workflows.py where NodeService.get()
        returns None.
        """
        workflow_id = uuid4()
        node_id = uuid4()

        # Mock WorkflowService to return a workflow, but NodeService returns None
        with patch(
            "app.api.v1.workflows.WorkflowService"
        ) as mock_workflow_service_class, patch(
            "app.api.v1.workflows.NodeService"
        ) as mock_node_service_class:
            # Workflow exists
            mock_workflow = MagicMock()
            mock_workflow.id = workflow_id
            mock_workflow_service = MagicMock()
            mock_workflow_service.get = AsyncMock(return_value=mock_workflow)
            mock_workflow_service_class.return_value = mock_workflow_service

            # Node does not exist
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=None)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.get(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Node" in response.json()["detail"]
            assert str(node_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_node_wrong_workflow_mock(self, async_client: AsyncClient):
        """Test get node returns 404 when node belongs to different workflow (mock).

        Tests lines 567-571 in workflows.py where node.workflow_id != workflow_id.
        """
        workflow_id = uuid4()
        other_workflow_id = uuid4()
        node_id = uuid4()

        with patch(
            "app.api.v1.workflows.WorkflowService"
        ) as mock_workflow_service_class, patch(
            "app.api.v1.workflows.NodeService"
        ) as mock_node_service_class:
            # Workflow exists
            mock_workflow = MagicMock()
            mock_workflow.id = workflow_id
            mock_workflow_service = MagicMock()
            mock_workflow_service.get = AsyncMock(return_value=mock_workflow)
            mock_workflow_service_class.return_value = mock_workflow_service

            # Node exists but belongs to different workflow
            mock_node = MagicMock()
            mock_node.id = node_id
            mock_node.workflow_id = other_workflow_id  # Different workflow
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=mock_node)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.get(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found in workflow" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_node_not_found_mock(self, async_client: AsyncClient):
        """Test update node returns 404 when node not found (mock).

        Tests lines 612-617 in workflows.py where NodeService.get()
        returns None before update.
        """
        workflow_id = uuid4()
        node_id = uuid4()
        update_data = {"name": "Updated Node", "position_x": 500.0}

        with patch("app.api.v1.workflows.NodeService") as mock_node_service_class:
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=None)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}", json=update_data
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Node" in response.json()["detail"]
            assert str(node_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_node_wrong_workflow_mock(self, async_client: AsyncClient):
        """Test update node returns 404 when node belongs to different workflow (mock).

        Tests lines 613-617 in workflows.py where node.workflow_id != workflow_id.
        """
        workflow_id = uuid4()
        other_workflow_id = uuid4()
        node_id = uuid4()
        update_data = {"name": "Updated Node", "position_x": 500.0}

        with patch("app.api.v1.workflows.NodeService") as mock_node_service_class:
            # Node exists but belongs to different workflow
            mock_node = MagicMock()
            mock_node.id = node_id
            mock_node.workflow_id = other_workflow_id  # Different workflow
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=mock_node)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}", json=update_data
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found in workflow" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_node_not_found_mock(self, async_client: AsyncClient):
        """Test delete node returns 404 when node not found (mock).

        Tests lines 661-666 in workflows.py where NodeService.get()
        returns None before delete.
        """
        workflow_id = uuid4()
        node_id = uuid4()

        with patch("app.api.v1.workflows.NodeService") as mock_node_service_class:
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=None)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.delete(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Node" in response.json()["detail"]
            assert str(node_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_node_wrong_workflow_mock(self, async_client: AsyncClient):
        """Test delete node returns 404 when node belongs to different workflow (mock).

        Tests lines 662-666 in workflows.py where node.workflow_id != workflow_id.
        """
        workflow_id = uuid4()
        other_workflow_id = uuid4()
        node_id = uuid4()

        with patch("app.api.v1.workflows.NodeService") as mock_node_service_class:
            # Node exists but belongs to different workflow
            mock_node = MagicMock()
            mock_node.id = node_id
            mock_node.workflow_id = other_workflow_id  # Different workflow
            mock_node_service = MagicMock()
            mock_node_service.get = AsyncMock(return_value=mock_node)
            mock_node_service_class.return_value = mock_node_service

            response = await async_client.delete(
                f"/api/v1/workflows/{workflow_id}/nodes/{node_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found in workflow" in response.json()["detail"]


# =============================================================================
# Mock-Based Edge CRUD Error Tests (Uncovered Paths - Categories 9-12)
# =============================================================================


class TestEdgeEndpointsMock:
    """Mock-based tests for Edge API endpoint error paths.

    These tests cover uncovered code paths in workflows.py by mocking
    service layer responses to trigger specific error conditions.

    Category 9: List Edges - Workflow Not Found (lines 714-729)
    Category 10: Create Edge Errors (lines 762-788)
    Category 11: Batch Create Edges Errors (lines 820-846)
    Category 12: Delete Edge Errors (lines 874-892)
    """

    # =========================================================================
    # Category 9: List Edges - Workflow Not Found (lines 714-729)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_edges_workflow_not_found_mock(self, async_client: AsyncClient):
        """Test list edges returns 404 when workflow not found (mock).

        Tests lines 712-718 in workflows.py where workflow_service.get()
        returns None before listing edges.
        """
        workflow_id = uuid4()

        with patch(
            "app.api.v1.workflows.WorkflowService"
        ) as mock_workflow_service_class:
            mock_workflow_service = MagicMock()
            mock_workflow_service.get = AsyncMock(return_value=None)
            mock_workflow_service_class.return_value = mock_workflow_service

            response = await async_client.get(f"/api/v1/workflows/{workflow_id}/edges")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert f"Workflow {workflow_id} not found" in response.json()["detail"]

    # =========================================================================
    # Category 10: Create Edge Errors (lines 762-788)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_edge_duplicate_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test create edge returns 409 on duplicate edge (IntegrityError).

        Tests lines 778-784 in workflows.py where Exception with
        'duplicate' in message triggers HTTP 409.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        node1_id = str(uuid4())
        node2_id = str(uuid4())

        edge_data = {
            "source_node_id": node1_id,
            "target_node_id": node2_id,
            "source_handle": "output",
            "target_handle": "input",
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.create = AsyncMock(
                side_effect=Exception("duplicate key value violates unique constraint")
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "duplicate" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_edge_cycle_detected_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test create edge returns 400 on DAGValidationError (cycle detected).

        Tests lines 773-777 in workflows.py where DAGValidationError
        is caught and converted to HTTP 400.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        node1_id = str(uuid4())
        node2_id = str(uuid4())

        edge_data = {
            "source_node_id": node1_id,
            "target_node_id": node2_id,
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.create = AsyncMock(
                side_effect=DAGValidationError(
                    "Adding this edge would create a cycle in the workflow graph"
                )
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "cycle" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_edge_invalid_node_reference_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test create edge returns 400 on InvalidNodeReferenceError.

        Tests lines 768-772 in workflows.py where InvalidNodeReferenceError
        is caught and converted to HTTP 400.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        node1_id = str(uuid4())
        node2_id = str(uuid4())

        edge_data = {
            "source_node_id": node1_id,
            "target_node_id": node2_id,
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.create = AsyncMock(
                side_effect=InvalidNodeReferenceError(
                    f"Nodes not found in workflow: source={node1_id}, target={node2_id}"
                )
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "not found" in response.json()["detail"].lower()

    # =========================================================================
    # Category 11: Batch Create Edges Errors (lines 820-846)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_batch_create_edges_duplicate_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test batch create edges returns 409 on duplicate edge.

        Tests lines 836-842 in workflows.py where Exception with
        'duplicate' in message triggers HTTP 409.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        batch_data = {
            "edges": [
                {
                    "source_node_id": str(uuid4()),
                    "target_node_id": str(uuid4()),
                },
            ]
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.batch_create = AsyncMock(
                side_effect=Exception("duplicate key value violates unique constraint")
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges/batch", json=batch_data
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "duplicate" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_batch_create_edges_dag_error_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test batch create edges returns 400 on DAGValidationError.

        Tests lines 831-835 in workflows.py where DAGValidationError
        is caught and converted to HTTP 400.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        batch_data = {
            "edges": [
                {
                    "source_node_id": str(uuid4()),
                    "target_node_id": str(uuid4()),
                },
            ]
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.batch_create = AsyncMock(
                side_effect=DAGValidationError(
                    "Adding this edge would create a cycle in the workflow graph"
                )
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges/batch", json=batch_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "cycle" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_batch_create_edges_invalid_reference_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test batch create edges returns 400 on InvalidNodeReferenceError.

        Tests lines 826-830 in workflows.py where InvalidNodeReferenceError
        is caught and converted to HTTP 400.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]

        batch_data = {
            "edges": [
                {
                    "source_node_id": str(uuid4()),
                    "target_node_id": str(uuid4()),
                },
            ]
        }

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.batch_create = AsyncMock(
                side_effect=InvalidNodeReferenceError("Nodes not found in workflow")
            )
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/edges/batch", json=batch_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "not found" in response.json()["detail"].lower()

    # =========================================================================
    # Category 12: Delete Edge Errors (lines 874-892)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_edge_not_found_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test delete edge returns 404 when edge not found (mock).

        Tests lines 872-878 in workflows.py where edge_service.get()
        returns None.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]
        edge_id = uuid4()

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            mock_edge_service.get = AsyncMock(return_value=None)
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.delete(
                f"/api/v1/workflows/{workflow_id}/edges/{edge_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert f"Edge {edge_id} not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_edge_wrong_workflow_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test delete edge returns 404 when edge belongs to different workflow (mock).

        Tests line 874 in workflows.py where edge.workflow_id != workflow_id
        condition is true.
        """
        # Create a real workflow first
        workflow_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = workflow_response.json()["id"]
        edge_id = uuid4()
        different_workflow_id = uuid4()

        with patch("app.api.v1.workflows.EdgeService") as mock_edge_service_class:
            mock_edge_service = MagicMock()
            # Create a mock edge that belongs to a different workflow
            mock_edge = MagicMock()
            mock_edge.id = edge_id
            mock_edge.workflow_id = different_workflow_id  # Different workflow
            mock_edge_service.get = AsyncMock(return_value=mock_edge)
            mock_edge_service_class.return_value = mock_edge_service

            response = await async_client.delete(
                f"/api/v1/workflows/{workflow_id}/edges/{edge_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert (
                f"Edge {edge_id} not found in workflow {workflow_id}"
                in response.json()["detail"]
            )


# =============================================================================
# Mock-Based Workflow CRUD Error Path Tests (Categories 1-4)
# =============================================================================


class TestWorkflowCRUDErrorsMocked:
    """Mock-based tests for Workflow CRUD error paths.

    These tests use unittest.mock to inject exceptions into the service layer,
    testing error handling paths that are difficult to trigger through
    normal integration tests.

    TAG: [SPEC-007] [TESTS] [API] [WORKFLOW] [MOCK]
    REQ: Category 1-4 - Workflow CRUD error paths

    Category 1: List Workflows database error (lines 117-133)
    Category 2: Version Conflict on update (lines 279-294)
    Category 3: Get Full Workflow errors (lines 238-248)
    Category 4: Create Node errors (lines 471-486)
    """

    # =========================================================================
    # Category 1: List Workflows Database Error (lines 117-133)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_workflows_database_error_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test list workflows returns 500 on database error.

        Tests lines 129-133 in workflows.py where generic Exception
        is caught and converted to HTTP 500.
        """
        mock_service = AsyncMock()
        mock_service.list.side_effect = Exception("Database connection failed")

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            response = await async_client.get("/api/v1/workflows/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database connection failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_workflows_count_error_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test list workflows returns 500 when count() fails.

        Tests lines 129-133 in workflows.py where Exception during
        count() is caught and converted to HTTP 500.
        """
        mock_service = AsyncMock()
        mock_service.list.return_value = []  # List succeeds
        mock_service.count.side_effect = Exception("Count query failed")

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            response = await async_client.get("/api/v1/workflows/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Count query failed" in response.json()["detail"]

    # =========================================================================
    # Category 2: Update Workflow Version Conflict (lines 279-294)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_workflow_version_conflict_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test update workflow returns 409 on VersionConflictError.

        Tests lines 285-289 in workflows.py where VersionConflictError
        is caught and converted to HTTP 409.
        """
        from app.services.workflow_service import VersionConflictError

        mock_service = AsyncMock()
        mock_service.update.side_effect = VersionConflictError(
            "Version conflict: expected 1, got 5"
        )

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            workflow_id = uuid4()
            update_data = {"name": "Updated", "version": 5}
            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}", json=update_data
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "Version conflict" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_workflow_not_found_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test update workflow returns 404 on WorkflowNotFoundError.

        Tests lines 280-284 in workflows.py where WorkflowNotFoundError
        is caught and converted to HTTP 404.
        """
        from app.services.workflow_service import WorkflowNotFoundError

        mock_service = AsyncMock()
        mock_service.update.side_effect = WorkflowNotFoundError("Workflow not found")

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            workflow_id = uuid4()
            update_data = {"name": "Updated", "version": 1}
            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}", json=update_data
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Workflow not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_workflow_internal_error_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test update workflow returns 500 on unexpected error.

        Tests lines 290-294 in workflows.py where generic Exception
        is caught and converted to HTTP 500.
        """
        mock_service = AsyncMock()
        mock_service.update.side_effect = Exception("Unexpected database error")

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            workflow_id = uuid4()
            update_data = {"name": "Updated", "version": 1}
            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}", json=update_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to update workflow" in response.json()["detail"]

    # =========================================================================
    # Category 3: Get Workflow Full Errors (lines 238-248)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_workflow_full_not_found_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test get workflow full returns 404 on WorkflowNotFoundError.

        Tests lines 239-243 in workflows.py where WorkflowNotFoundError
        is caught and converted to HTTP 404.
        """
        from app.services.workflow_service import WorkflowNotFoundError

        mock_service = AsyncMock()
        mock_service.get_with_nodes.side_effect = WorkflowNotFoundError(
            "Workflow not found"
        )

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            workflow_id = uuid4()
            response = await async_client.get(f"/api/v1/workflows/{workflow_id}/full")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Workflow not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_workflow_full_internal_error_mock(
        self, async_client: AsyncClient, db_session
    ):
        """Test get workflow full returns 500 on unexpected error.

        Tests lines 244-248 in workflows.py where generic Exception
        is caught and converted to HTTP 500.
        """
        mock_service = AsyncMock()
        mock_service.get_with_nodes.side_effect = Exception("Unexpected database error")

        with patch("app.api.v1.workflows.WorkflowService", return_value=mock_service):
            workflow_id = uuid4()
            response = await async_client.get(f"/api/v1/workflows/{workflow_id}/full")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Unexpected database error" in response.json()["detail"]

    # =========================================================================
    # Category 4: Create Node Errors (lines 471-486)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_node_workflow_not_found_mock(
        self, async_client: AsyncClient, db_session, sample_node_data
    ):
        """Test create node returns 404 when workflow not found.

        Tests lines 472-476 in workflows.py where WorkflowNotFoundError
        is caught and converted to HTTP 404.
        """
        from app.services.workflow_service import WorkflowNotFoundError

        mock_service = AsyncMock()
        mock_service.create.side_effect = WorkflowNotFoundError("Workflow not found")

        with patch("app.api.v1.workflows.NodeService", return_value=mock_service):
            workflow_id = uuid4()
            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Workflow not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_node_invalid_reference_mock(
        self, async_client: AsyncClient, db_session, sample_node_data
    ):
        """Test create node returns 400 on InvalidNodeReferenceError.

        Tests lines 477-481 in workflows.py where InvalidNodeReferenceError
        is caught and converted to HTTP 400.
        """
        mock_service = AsyncMock()
        mock_service.create.side_effect = InvalidNodeReferenceError(
            "Invalid tool_id reference"
        )

        with patch("app.api.v1.workflows.NodeService", return_value=mock_service):
            workflow_id = uuid4()
            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid tool_id reference" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_node_internal_error_mock(
        self, async_client: AsyncClient, db_session, sample_node_data
    ):
        """Test create node returns 500 on unexpected error.

        Tests lines 482-486 in workflows.py where generic Exception
        is caught and converted to HTTP 500.
        """
        mock_service = AsyncMock()
        mock_service.create.side_effect = Exception("Database error")

        with patch("app.api.v1.workflows.NodeService", return_value=mock_service):
            workflow_id = uuid4()
            response = await async_client.post(
                f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create node" in response.json()["detail"]


# =============================================================================
# Mock-based Graph Update Tests (Category 13 - Complex Paths)
# =============================================================================


class TestGraphUpdateMockBased:
    """Mock-based tests for workflow graph update endpoint to cover complex paths.

    These tests use mocking to cover exception handling paths that are difficult
    to trigger through integration tests, including:
    - Workflow not found scenarios
    - Version conflict scenarios
    - DAG validation errors
    - Invalid node reference errors
    - Generic exception handling
    - HTTPException re-raise path

    TAG: [SPEC-007] [TESTS] [API] [WORKFLOW] [GRAPH] [MOCK]
    REQ: REQ-004 - Graph Update Endpoint Exception Path Tests
    """

    @pytest.mark.asyncio
    async def test_update_workflow_graph_not_found_mock(
        self, async_client: AsyncClient
    ):
        """Test graph update when workflow not found returns 404.

        Mocks WorkflowService.get to return None to trigger 404 path.
        Covers lines 932-937 in workflows.py.
        """
        workflow_id = uuid4()

        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(return_value=None)

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={"nodes": [], "edges": [], "version": 1},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_version_conflict_mock(
        self, async_client: AsyncClient
    ):
        """Test graph update with version conflict returns 409.

        Mocks workflow with version 5, but request sends version 4.
        Covers lines 939-944 in workflows.py.
        """
        workflow_id = uuid4()

        # Mock workflow with version 5
        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.version = 5
        mock_workflow.nodes = []
        mock_workflow.edges = []

        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(return_value=mock_workflow)

            # Send request with version 4 (mismatch)
            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={"nodes": [], "edges": [], "version": 4},
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            detail = response.json()["detail"]
            assert "conflict" in detail.lower() or "version" in detail.lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_dag_error_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test graph update with DAG validation error returns 400.

        Mocks get_with_nodes to raise DAGValidationError.
        Covers lines 1031-1035 in workflows.py.
        """
        # Create a workflow first to get a real ID
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Mock workflow with matching version
        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.version = version
        mock_workflow.nodes = []
        mock_workflow.edges = []

        node1_id = str(uuid4())
        node2_id = str(uuid4())

        # Patch to raise DAGValidationError during processing
        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(return_value=mock_workflow)
            mock_instance.get_with_nodes = AsyncMock(
                side_effect=DAGValidationError("Cycle detected in graph")
            )

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={
                    "nodes": [
                        {
                            "name": "Node 1",
                            "node_type": "trigger",
                            "position_x": 100.0,
                            "position_y": 100.0,
                            "tool_id": node1_id,
                        }
                    ],
                    "edges": [
                        {
                            "source_node_id": node1_id,
                            "target_node_id": node2_id,
                        }
                    ],
                    "version": version,
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "cycle" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_invalid_reference_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test graph update with invalid node reference returns 400.

        Mocks get_with_nodes to raise InvalidNodeReferenceError.
        Covers lines 1036-1040 in workflows.py.
        """
        # Create a workflow first
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Mock workflow with matching version
        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.version = version
        mock_workflow.nodes = []
        mock_workflow.edges = []

        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(return_value=mock_workflow)
            mock_instance.get_with_nodes = AsyncMock(
                side_effect=InvalidNodeReferenceError("Invalid tool_id reference")
            )

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={
                    "nodes": [
                        {
                            "name": "Invalid Node",
                            "node_type": "tool",
                            "position_x": 100.0,
                            "position_y": 100.0,
                            "tool_id": str(uuid4()),
                        }
                    ],
                    "edges": [],
                    "version": version,
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_generic_error_mock(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test graph update with generic exception returns 500.

        Mocks WorkflowService.get to raise a generic Exception.
        Covers lines 1041-1045 in workflows.py.
        """
        # Create a workflow first
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(
                side_effect=Exception("Unexpected database error")
            )

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={"nodes": [], "edges": [], "version": version},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "failed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_httpexception_reraise(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test that HTTPException is properly re-raised in graph update.

        Mocks get_with_nodes to raise HTTPException which should be re-raised.
        Covers lines 1029-1030 in workflows.py.
        """
        from fastapi import HTTPException

        # Create a workflow first
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Mock workflow
        mock_workflow = MagicMock()
        mock_workflow.id = workflow_id
        mock_workflow.version = version

        with patch("app.api.v1.workflows.WorkflowService") as MockService:
            mock_instance = MockService.return_value
            mock_instance.get = AsyncMock(return_value=mock_workflow)
            # Simulate HTTPException being raised in get_with_nodes
            mock_instance.get_with_nodes = AsyncMock(
                side_effect=HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to workflow",
                )
            )

            response = await async_client.put(
                f"/api/v1/workflows/{workflow_id}/graph",
                json={"nodes": [], "edges": [], "version": version},
            )

            # HTTPException should be re-raised with original status code
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "access denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_workflow_graph_empty_nodes_edges(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test graph update with empty nodes and edges succeeds."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Update with empty graph
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph",
            json={"nodes": [], "edges": [], "version": version},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    @pytest.mark.asyncio
    async def test_update_workflow_graph_replaces_existing(
        self, async_client: AsyncClient, sample_workflow_data, sample_node_data
    ):
        """Test that graph update replaces all existing nodes and edges."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # Add initial node
        await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes",
            json={**sample_node_data, "name": "Initial Node"},
        )

        # Get fresh version after node creation (version doesn't change for nodes)
        get_response = await async_client.get(f"/api/v1/workflows/{workflow_id}")
        current_version = get_response.json()["version"]

        # Create new nodes for graph update
        new_node1_id = str(uuid4())
        new_node2_id = str(uuid4())

        # Update graph with new nodes (replaces initial)
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph",
            json={
                "nodes": [
                    {
                        "id": new_node1_id,
                        "name": "New Node 1",
                        "node_type": "trigger",
                        "position_x": 0.0,
                        "position_y": 0.0,
                    },
                    {
                        "id": new_node2_id,
                        "name": "New Node 2",
                        "node_type": "trigger",
                        "position_x": 200.0,
                        "position_y": 0.0,
                    },
                ],
                "edges": [
                    {
                        "source_node_id": new_node1_id,
                        "target_node_id": new_node2_id,
                    }
                ],
                "version": current_version,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Initial node should be replaced
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        node_names = [n["name"] for n in data["nodes"]]
        assert "Initial Node" not in node_names
        assert "New Node 1" in node_names
        assert "New Node 2" in node_names

    @pytest.mark.asyncio
    async def test_update_workflow_graph_version_increments(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test that graph update increments workflow version."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        initial_version = create_response.json()["version"]

        # Update graph
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph",
            json={"nodes": [], "edges": [], "version": initial_version},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["version"] == initial_version + 1

    @pytest.mark.asyncio
    async def test_update_workflow_graph_multiple_sequential_updates(
        self, async_client: AsyncClient, sample_workflow_data
    ):
        """Test multiple sequential graph updates with correct versions."""
        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow_id = create_response.json()["id"]
        version = create_response.json()["version"]

        # First update
        response1 = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph",
            json={
                "nodes": [
                    {
                        "name": "First Update Node",
                        "node_type": "trigger",
                        "position_x": 0.0,
                        "position_y": 0.0,
                    }
                ],
                "edges": [],
                "version": version,
            },
        )
        assert response1.status_code == status.HTTP_200_OK
        version = response1.json()["version"]

        # Second update with new version
        response2 = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph",
            json={
                "nodes": [
                    {
                        "name": "Second Update Node",
                        "node_type": "trigger",
                        "position_x": 100.0,
                        "position_y": 100.0,
                    }
                ],
                "edges": [],
                "version": version,
            },
        )
        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "Second Update Node"
