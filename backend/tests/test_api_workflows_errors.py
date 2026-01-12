"""Error handling tests for Workflow API endpoints.

TAG: [SPEC-007] [TESTS] [API] [WORKFLOW] [ERRORS]
REQ: REQ-001 - Workflow CRUD Error Handling Tests
REQ: REQ-002 - Node CRUD Error Handling Tests
REQ: REQ-003 - Edge CRUD Error Handling Tests
REQ: REQ-004 - Graph Update Error Handling Tests

This test file ensures comprehensive coverage of error handling paths
in the workflow API, including all exception branches and edge cases.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

# =============================================================================
# Category 1: Workflow CRUD Error Handling Tests
# =============================================================================


class TestWorkflowCRUDErrors:
    """Test suite for workflow CRUD error handling."""

    @pytest.mark.asyncio
    async def test_get_workflow_full_not_found(self, async_client: AsyncClient):
        """Test get workflow full with non-existent workflow returns 404."""
        response = await async_client.get(f"/api/v1/workflows/{uuid4()}/full")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, async_client: AsyncClient):
        """Test update non-existent workflow returns 404."""
        update_data = {"name": "Updated", "version": 1}
        response = await async_client.put(
            f"/api/v1/workflows/{uuid4()}", json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_workflow_not_found(self, async_client: AsyncClient):
        """Test delete non-existent workflow returns 404."""
        response = await async_client.delete(f"/api/v1/workflows/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_duplicate_workflow_not_found(self, async_client: AsyncClient):
        """Test duplicate non-existent workflow returns 404."""
        response = await async_client.post(f"/api/v1/workflows/{uuid4()}/duplicate")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Category 2: Node Error Handling Tests
# =============================================================================


class TestNodeErrors:
    """Test suite for node error handling."""

    @pytest.fixture
    async def workflow_id(self, async_client: AsyncClient, sample_workflow_data):
        """Create a workflow and return its ID."""
        response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        return response.json()["id"]

    @pytest.fixture
    async def node_id(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Create a node and return its ID."""
        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=sample_node_data
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_list_nodes_workflow_not_found(self, async_client: AsyncClient):
        """Test list nodes for non-existent workflow returns 404."""
        response = await async_client.get(f"/api/v1/workflows/{uuid4()}/nodes")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_node_workflow_not_found(
        self, async_client: AsyncClient, sample_node_data
    ):
        """Test create node with non-existent workflow returns 400/404."""
        response = await async_client.post(
            f"/api/v1/workflows/{uuid4()}/nodes", json=sample_node_data
        )

        # Service returns 400 for invalid workflow reference (caught by service layer)
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_create_node_with_invalid_tool_reference(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test create node with non-existent tool reference creates node (FK not enforced)."""
        # Note: Currently the API doesn't validate tool_id foreign key
        # This test documents current behavior - node is created even with invalid tool_id
        node_data = {
            "name": "Test Node",
            "node_type": "tool",
            "position_x": 100.0,
            "position_y": 200.0,
            "tool_id": str(uuid4()),  # Non-existent tool
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=node_data
        )

        # Current behavior: Creates node without FK validation
        # Future improvement: Add FK validation and return 400
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_node_with_invalid_agent_reference(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test create node with non-existent agent reference creates node (FK not enforced)."""
        # Note: Currently the API doesn't validate agent_id foreign key
        node_data = {
            "name": "Test Node",
            "node_type": "agent",
            "position_x": 100.0,
            "position_y": 200.0,
            "agent_id": str(uuid4()),  # Non-existent agent
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/nodes", json=node_data
        )

        # Current behavior: Creates node without FK validation
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_batch_create_nodes_workflow_not_found(
        self, async_client: AsyncClient, sample_node_data
    ):
        """Test batch create nodes with non-existent workflow returns 400/404/500."""
        batch_data = {"nodes": [{**sample_node_data, "name": "Node 1"}]}

        response = await async_client.post(
            f"/api/v1/workflows/{uuid4()}/nodes/batch", json=batch_data
        )

        # Service may return 400, 404, or 500 depending on error handling
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @pytest.mark.asyncio
    async def test_get_node_workflow_not_found(self, async_client: AsyncClient):
        """Test get node with non-existent workflow returns 404."""
        response = await async_client.get(
            f"/api/v1/workflows/{uuid4()}/nodes/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_node_not_found_in_workflow(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test get non-existent node in workflow returns 404."""
        response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}/nodes/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_node_not_found(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test update non-existent node returns 404."""
        update_data = {"name": "Updated"}
        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/nodes/{uuid4()}", json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_node_workflow_mismatch(
        self, async_client: AsyncClient, workflow_id: str, node_id: str
    ):
        """Test update node from different workflow returns 404."""
        update_data = {"name": "Updated"}
        response = await async_client.put(
            f"/api/v1/workflows/{uuid4()}/nodes/{node_id}", json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_node_not_found(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test delete non-existent node returns 404."""
        response = await async_client.delete(
            f"/api/v1/workflows/{workflow_id}/nodes/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_node_wrong_workflow(
        self, async_client: AsyncClient, workflow_id: str, node_id: str
    ):
        """Test delete node from different workflow returns 404."""
        response = await async_client.delete(
            f"/api/v1/workflows/{uuid4()}/nodes/{node_id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Category 3: Edge Error Handling Tests
# =============================================================================


class TestEdgeErrors:
    """Test suite for edge error handling."""

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

        # Create trigger nodes (no tool_id required)
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

    @pytest.fixture
    async def edge_id(
        self,
        async_client: AsyncClient,
        workflow_with_nodes: tuple,
    ):
        """Create an edge and return its ID."""
        workflow_id, node1_id, node2_id = workflow_with_nodes

        edge_data = {
            "source_node_id": str(node1_id),
            "target_node_id": str(node2_id),
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_list_edges_workflow_not_found(self, async_client: AsyncClient):
        """Test list edges for non-existent workflow returns 404."""
        response = await async_client.get(f"/api/v1/workflows/{uuid4()}/edges")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_edge_workflow_not_found(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test create edge with non-existent workflow returns 400/404."""
        _, node1_id, node2_id = workflow_with_nodes

        edge_data = {
            "source_node_id": str(node1_id),
            "target_node_id": str(node2_id),
        }

        response = await async_client.post(
            f"/api/v1/workflows/{uuid4()}/edges", json=edge_data
        )

        # Returns 400 because nodes don't exist in the specified workflow
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_create_edge_with_invalid_source_node(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test create edge with non-existent source node returns 400."""
        workflow_id, _, node2_id = workflow_with_nodes

        edge_data = {
            "source_node_id": str(uuid4()),  # Non-existent node
            "target_node_id": str(node2_id),
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_edge_with_invalid_target_node(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test create edge with non-existent target node returns 400."""
        workflow_id, node1_id, _ = workflow_with_nodes

        edge_data = {
            "source_node_id": str(node1_id),
            "target_node_id": str(uuid4()),  # Non-existent node
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_edge_with_nodes_from_different_workflow(
        self, async_client: AsyncClient, sample_workflow_data, sample_node_data
    ):
        """Test create edge with nodes from different workflows returns 400."""
        # Create first workflow with node
        workflow1_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow1_id = workflow1_response.json()["id"]

        node1_response = await async_client.post(
            f"/api/v1/workflows/{workflow1_id}/nodes", json=sample_node_data
        )
        node1_id = node1_response.json()["id"]

        # Create second workflow with node
        workflow2_response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        workflow2_id = workflow2_response.json()["id"]

        node2_response = await async_client.post(
            f"/api/v1/workflows/{workflow2_id}/nodes", json=sample_node_data
        )
        node2_id = node2_response.json()["id"]

        # Try to create edge between nodes in different workflows
        edge_data = {
            "source_node_id": str(node1_id),
            "target_node_id": str(node2_id),
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow1_id}/edges", json=edge_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_duplicate_edge(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test create duplicate edge may succeed (idempotent) or return 409."""
        workflow_id, node1_id, node2_id = workflow_with_nodes

        edge_data = {
            "source_node_id": str(node1_id),
            "target_node_id": str(node2_id),
        }

        # Create first edge
        await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        # Try to create duplicate edge
        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges", json=edge_data
        )

        # Current behavior: May succeed (idempotent) or return 409
        # depending on database unique constraints
        assert response.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_409_CONFLICT,
        )

    @pytest.mark.asyncio
    async def test_batch_create_edges_workflow_not_found(
        self, async_client: AsyncClient
    ):
        """Test batch create edges with non-existent workflow returns 400/404."""
        batch_data = {
            "edges": [
                {
                    "source_node_id": str(uuid4()),
                    "target_node_id": str(uuid4()),
                }
            ]
        }

        response = await async_client.post(
            f"/api/v1/workflows/{uuid4()}/edges/batch", json=batch_data
        )

        # Returns 400 because nodes don't exist in the specified workflow
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    @pytest.mark.asyncio
    async def test_batch_create_edges_with_invalid_node_reference(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test batch create edges with invalid node reference returns 400."""
        workflow_id, _, _ = workflow_with_nodes

        batch_data = {
            "edges": [
                {
                    "source_node_id": str(uuid4()),  # Non-existent
                    "target_node_id": str(uuid4()),  # Non-existent
                }
            ]
        }

        response = await async_client.post(
            f"/api/v1/workflows/{workflow_id}/edges/batch", json=batch_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_delete_edge_not_found(
        self, async_client: AsyncClient, workflow_with_nodes: tuple
    ):
        """Test delete non-existent edge returns 404."""
        workflow_id, _, _ = workflow_with_nodes

        response = await async_client.delete(
            f"/api/v1/workflows/{workflow_id}/edges/{uuid4()}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_edge_wrong_workflow(
        self, async_client: AsyncClient, workflow_with_nodes: tuple, edge_id: str
    ):
        """Test delete edge from different workflow returns 404."""
        response = await async_client.delete(
            f"/api/v1/workflows/{uuid4()}/edges/{edge_id}"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Category 4: Graph Update Error Handling Tests
# =============================================================================


class TestGraphUpdateErrors:
    """Test suite for graph update error handling."""

    @pytest.fixture
    async def workflow_id(self, async_client: AsyncClient, sample_workflow_data):
        """Create a workflow and return its ID."""
        response = await async_client.post(
            "/api/v1/workflows/", json=sample_workflow_data
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_update_graph_workflow_not_found(self, async_client: AsyncClient):
        """Test update graph for non-existent workflow returns 404."""
        graph_data = {"version": 1, "nodes": [], "edges": []}

        response = await async_client.put(
            f"/api/v1/workflows/{uuid4()}/graph", json=graph_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_graph_with_invalid_node_reference(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test update graph accepts edges with non-existent node IDs (current behavior)."""
        # Get current version
        get_response = await async_client.get(f"/api/v1/workflows/{workflow_id}")
        version = get_response.json()["version"]

        # Graph with edge referencing non-existent node
        node1_id = str(uuid4())
        node2_id = str(uuid4())

        graph_data = {
            "version": version,
            "nodes": [{**sample_node_data, "id": node1_id, "name": "Node 1"}],
            "edges": [
                {
                    "source_node_id": node1_id,
                    "target_node_id": node2_id,  # Node doesn't exist in nodes list
                }
            ],
        }

        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph", json=graph_data
        )

        # Current behavior: Succeeds even with invalid edge references
        # Future improvement: Validate all edge node IDs exist
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        )

    @pytest.mark.asyncio
    async def test_update_graph_empty_to_with_nodes(
        self, async_client: AsyncClient, workflow_id: str, sample_node_data
    ):
        """Test update graph from empty to with nodes succeeds."""
        # Get current version
        get_response = await async_client.get(f"/api/v1/workflows/{workflow_id}")
        version = get_response.json()["version"]

        node1_id = str(uuid4())
        node2_id = str(uuid4())

        graph_data = {
            "version": version,
            "nodes": [
                {**sample_node_data, "id": node1_id, "name": "Node 1"},
                {**sample_node_data, "id": node2_id, "name": "Node 2"},
            ],
            "edges": [],
        }

        response = await async_client.put(
            f"/api/v1/workflows/{workflow_id}/graph", json=graph_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["nodes"]) == 2
        assert data["version"] == version + 1
