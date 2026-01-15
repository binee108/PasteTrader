"""Unit tests for WorkflowService, NodeService, and EdgeService.

TAG: [SPEC-007] [TESTS] [SERVICES] [WORKFLOW]
REQ: REQ-001 - WorkflowService Tests
REQ: REQ-002 - NodeService Tests
REQ: REQ-003 - EdgeService Tests
REQ: REQ-004 - Batch Operations Tests
REQ: REQ-005 - DAG Validation Tests
"""

from uuid import uuid4

import pytest

from app.models.workflow import Edge
from app.schemas.workflow import (
    EdgeBatchCreate,
    EdgeCreate,
    NodeBatchCreate,
    NodeCreate,
    NodeUpdate,
    WorkflowCreate,
    WorkflowUpdate,
)
from app.services.workflow_service import (
    DAGValidationError,
    EdgeNotFoundError,
    EdgeService,
    InvalidNodeReferenceError,
    NodeNotFoundError,
    NodeService,
    VersionConflictError,
    WorkflowNotFoundError,
    WorkflowService,
    WorkflowServiceError,
)

# =============================================================================
# WorkflowService Tests
# =============================================================================


class TestWorkflowService:
    """Test suite for WorkflowService."""

    @pytest.mark.asyncio
    async def test_create_workflow_success(self, db_session, sample_workflow_data):
        """Test successful workflow creation."""
        workflow_data = WorkflowCreate(**sample_workflow_data)
        owner_id = uuid4()

        workflow = await WorkflowService(db_session).create(owner_id, workflow_data)

        assert workflow.id is not None
        assert workflow.name == "Test Workflow"
        assert workflow.owner_id == owner_id
        assert workflow.is_active is True
        assert workflow.version == 1
        assert workflow.created_at is not None

    @pytest.mark.asyncio
    async def test_create_workflow_with_error(self, db_session):
        """Test workflow creation with error."""
        workflow_data = WorkflowCreate(
            name="Test Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
        )

        # Mock flush to raise an exception
        async def mock_flush_error():
            raise Exception("Database error")

        db_session.flush = mock_flush_error

        with pytest.raises(WorkflowServiceError, match="Failed to create workflow"):
            await WorkflowService(db_session).create(uuid4(), workflow_data)

    @pytest.mark.asyncio
    async def test_get_workflow_success(self, db_session, workflow_factory):
        """Test successful workflow retrieval."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        result = await WorkflowService(db_session).get(workflow.id)

        assert result is not None
        assert result.id == workflow.id
        assert result.name == workflow.name

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, db_session):
        """Test getting non-existent workflow returns None."""
        result = await WorkflowService(db_session).get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_workflow_includes_deleted(self, db_session, workflow_factory):
        """Test get with include_deleted=True returns soft-deleted workflows."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        # Soft delete the workflow
        await WorkflowService(db_session).delete(workflow.id)

        # Without include_deleted, should return None
        result_not_deleted = await WorkflowService(db_session).get(
            workflow.id, include_deleted=False
        )
        assert result_not_deleted is None

        # With include_deleted, should return the workflow
        result_deleted = await WorkflowService(db_session).get(
            workflow.id, include_deleted=True
        )
        assert result_deleted is not None
        assert result_deleted.id == workflow.id
        assert result_deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_get_with_nodes_success(
        self, db_session, workflow_factory, node_factory
    ):
        """Test getting workflow with nodes and edges."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)
        edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node1.id,
            target_node_id=node2.id,
        )

        db_session.add_all([workflow, node1, node2, edge])
        await db_session.flush()

        result = await WorkflowService(db_session).get_with_nodes(workflow.id)

        assert result is not None
        assert result.id == workflow.id
        assert len(result.nodes) == 2
        assert len(result.edges) == 1

    @pytest.mark.asyncio
    async def test_get_with_nodes_not_found(self, db_session):
        """Test get_with_nodes raises error for non-existent workflow."""
        with pytest.raises(WorkflowNotFoundError):
            await WorkflowService(db_session).get_with_nodes(uuid4())

    @pytest.mark.asyncio
    async def test_get_with_nodes_includes_deleted(
        self, db_session, workflow_factory, node_factory
    ):
        """Test get_with_nodes with include_deleted=True returns soft-deleted workflows."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        # Soft delete the workflow
        await WorkflowService(db_session).delete(workflow.id)

        # Without include_deleted, should raise error
        with pytest.raises(WorkflowNotFoundError):
            await WorkflowService(db_session).get_with_nodes(
                workflow.id, include_deleted=False
            )

        # With include_deleted, should return the workflow with nodes
        result = await WorkflowService(db_session).get_with_nodes(
            workflow.id, include_deleted=True
        )
        assert result is not None
        assert result.id == workflow.id
        assert result.deleted_at is not None
        assert len(result.nodes) == 2

    @pytest.mark.asyncio
    async def test_list_workflows(self, db_session, workflow_factory):
        """Test listing workflows with pagination."""
        owner_id = uuid4()
        workflow1 = workflow_factory(owner_id=owner_id, is_active=True)
        workflow2 = workflow_factory(owner_id=owner_id, is_active=False)
        workflow3 = workflow_factory(owner_id=uuid4(), is_active=True)

        db_session.add_all([workflow1, workflow2, workflow3])
        await db_session.flush()

        # List all workflows for owner
        workflows = await WorkflowService(db_session).list(owner_id, skip=0, limit=10)
        assert len(workflows) == 2

        # Filter by active status
        active_workflows = await WorkflowService(db_session).list(
            owner_id, skip=0, limit=10, is_active=True
        )
        assert len(active_workflows) == 1

    @pytest.mark.asyncio
    async def test_list_workflows_with_skip_limit(self, db_session, workflow_factory):
        """Test list with skip and limit parameters."""
        owner_id = uuid4()
        workflows = [
            workflow_factory(owner_id=owner_id, name=f"Workflow {i}") for i in range(5)
        ]

        db_session.add_all(workflows)
        await db_session.flush()

        # Test pagination
        page1 = await WorkflowService(db_session).list(owner_id, skip=0, limit=2)
        page2 = await WorkflowService(db_session).list(owner_id, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_list_workflows_includes_deleted(self, db_session, workflow_factory):
        """Test list with include_deleted=True returns soft-deleted workflows."""
        owner_id = uuid4()
        workflow1 = workflow_factory(owner_id=owner_id, deleted_at=None)
        workflow2 = workflow_factory(owner_id=owner_id, deleted_at=None)

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        # Soft delete one workflow
        await WorkflowService(db_session).delete(workflow1.id)

        # Without include_deleted, should only return non-deleted
        active_only = await WorkflowService(db_session).list(
            owner_id, skip=0, limit=10, include_deleted=False
        )
        assert len(active_only) == 1

        # With include_deleted, should return all
        all_workflows = await WorkflowService(db_session).list(
            owner_id, skip=0, limit=10, include_deleted=True
        )
        assert len(all_workflows) == 2

    @pytest.mark.asyncio
    async def test_count_workflows(self, db_session, workflow_factory):
        """Test counting workflows."""
        owner_id = uuid4()
        workflow1 = workflow_factory(owner_id=owner_id, is_active=True)
        workflow2 = workflow_factory(owner_id=owner_id, is_active=False)
        workflow3 = workflow_factory(owner_id=uuid4(), is_active=True)

        db_session.add_all([workflow1, workflow2, workflow3])
        await db_session.flush()

        # Count all
        total = await WorkflowService(db_session).count(owner_id)
        assert total == 2

        # Count active only
        active_count = await WorkflowService(db_session).count(owner_id, is_active=True)
        assert active_count == 1

    @pytest.mark.asyncio
    async def test_count_workflows_includes_deleted(self, db_session, workflow_factory):
        """Test count with include_deleted=True includes soft-deleted workflows."""
        owner_id = uuid4()
        workflow1 = workflow_factory(owner_id=owner_id)
        workflow2 = workflow_factory(owner_id=owner_id)

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        # Soft delete one workflow
        await WorkflowService(db_session).delete(workflow1.id)

        # Without include_deleted, should only count non-deleted
        active_only = await WorkflowService(db_session).count(
            owner_id, include_deleted=False
        )
        assert active_only == 1

        # With include_deleted, should count all
        all_count = await WorkflowService(db_session).count(
            owner_id, include_deleted=True
        )
        assert all_count == 2

    @pytest.mark.asyncio
    async def test_update_workflow_success(self, db_session, workflow_factory):
        """Test successful workflow update with version check."""
        workflow = workflow_factory(version=1)
        db_session.add(workflow)
        await db_session.flush()

        update_data = WorkflowUpdate(
            name="Updated Name",
            description="Updated description",
            version=1,
        )

        updated = await WorkflowService(db_session).update(workflow.id, update_data)

        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.version == 2
        assert updated.updated_at >= workflow.updated_at

    @pytest.mark.asyncio
    async def test_update_workflow_version_conflict(self, db_session, workflow_factory):
        """Test update with version conflict raises error."""
        workflow = workflow_factory(version=2)
        db_session.add(workflow)
        await db_session.flush()

        update_data = WorkflowUpdate(
            name="Updated Name",
            version=1,  # Wrong version
        )

        with pytest.raises(
            VersionConflictError, match="Version conflict: expected 2, got 1"
        ):
            await WorkflowService(db_session).update(workflow.id, update_data)

    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, db_session):
        """Test updating non-existent workflow raises error."""
        update_data = WorkflowUpdate(name="Test", version=1)

        with pytest.raises(WorkflowNotFoundError):
            await WorkflowService(db_session).update(uuid4(), update_data)

    @pytest.mark.asyncio
    async def test_update_ignores_unknown_fields(self, db_session, workflow_factory):
        """Test that update ignores fields not present in workflow model."""
        workflow = workflow_factory(version=1)
        db_session.add(workflow)
        await db_session.flush()

        # Create update data with all fields - hasattr should skip non-existent fields
        update_data = WorkflowUpdate(
            name="Updated Name",
            description="Updated description",  # Valid field
            version=1,
        )

        updated = await WorkflowService(db_session).update(workflow.id, update_data)

        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.version == 2  # Version should increment

    @pytest.mark.asyncio
    async def test_update_with_only_nonexistent_fields(
        self, db_session, workflow_factory
    ):
        """Test update with only non-existent fields (hasattr False branch)."""
        workflow = workflow_factory(version=1, name="Original")
        db_session.add(workflow)
        await db_session.flush()

        # Create mock update data that returns non-existent fields
        # Create mock update data with non-existent fields
        class NonexistentFieldsUpdate:
            version = 1

            def model_dump(
                self,
                *,
                mode: str = "python",
                exclude=None,
                exclude_unset: bool = True,
                **kwargs,
            ):
                return {
                    "non_existent_field": "value",
                    "another_fake_field": 123,
                }

        update_data = NonexistentFieldsUpdate()

        # The update should not raise an error, just skip non-existent fields
        updated = await WorkflowService(db_session).update(workflow.id, update_data)

        # Name should remain unchanged since no valid fields were updated
        assert updated.name == "Original"
        assert updated.version == 2

    @pytest.mark.asyncio
    async def test_delete_workflow_success(self, db_session, workflow_factory):
        """Test successful workflow soft delete."""
        workflow = workflow_factory(deleted_at=None)
        db_session.add(workflow)
        await db_session.flush()

        deleted = await WorkflowService(db_session).delete(workflow.id)

        assert deleted.deleted_at is not None
        assert deleted.is_active is False

    @pytest.mark.asyncio
    async def test_delete_workflow_not_found(self, db_session):
        """Test deleting non-existent workflow raises error."""
        with pytest.raises(WorkflowNotFoundError):
            await WorkflowService(db_session).delete(uuid4())

    @pytest.mark.asyncio
    async def test_duplicate_workflow_success(
        self, db_session, workflow_factory, node_factory
    ):
        """Test successful workflow duplication."""
        workflow = workflow_factory(name="Original")
        node1 = node_factory(workflow_id=workflow.id, name="Node 1")
        node2 = node_factory(workflow_id=workflow.id, name="Node 2")
        edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node1.id,
            target_node_id=node2.id,
        )

        db_session.add_all([workflow, node1, node2, edge])
        await db_session.flush()

        duplicate = await WorkflowService(db_session).duplicate(
            workflow.id, "Duplicate"
        )

        assert duplicate.id != workflow.id
        assert duplicate.name == "Duplicate"
        assert duplicate.owner_id == workflow.owner_id
        assert duplicate.is_active is False

        # Verify nodes were duplicated
        assert len(duplicate.nodes) == 2
        assert len(duplicate.edges) == 1

    @pytest.mark.asyncio
    async def test_duplicate_workflow_not_found(self, db_session):
        """Test duplicating non-existent workflow raises error."""
        with pytest.raises(WorkflowNotFoundError):
            await WorkflowService(db_session).duplicate(uuid4(), "Copy")

    @pytest.mark.asyncio
    async def test_duplicate_skips_invalid_edges(
        self, db_session, workflow_factory, node_factory
    ):
        """Test that duplicate skips edges with invalid node references."""
        workflow = workflow_factory(name="Original")
        node1 = node_factory(workflow_id=workflow.id, name="Node 1")
        node2 = node_factory(workflow_id=workflow.id, name="Node 2")

        # Create an edge with a non-existent node reference
        invalid_edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node1.id,
            target_node_id=uuid4(),  # Invalid target
        )
        valid_edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node1.id,
            target_node_id=node2.id,
        )

        db_session.add_all([workflow, node1, node2, invalid_edge, valid_edge])
        await db_session.flush()

        duplicate = await WorkflowService(db_session).duplicate(
            workflow.id, "Duplicate"
        )

        # Should only duplicate the valid edge
        assert len(duplicate.edges) == 1
        assert duplicate.edges[0].target_node_id != invalid_edge.target_node_id


# =============================================================================
# NodeService Tests
# =============================================================================


class TestNodeService:
    """Test suite for NodeService."""

    @pytest.mark.asyncio
    async def test_create_node_success(
        self, db_session, workflow_factory, sample_node_data
    ):
        """Test successful node creation."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        node_data = NodeCreate(**sample_node_data)
        node = await NodeService(db_session).create(workflow.id, node_data)

        assert node.id is not None
        assert node.workflow_id == workflow.id
        assert node.name == "Test Node"
        assert node.node_type.value == "tool"

    @pytest.mark.asyncio
    async def test_create_node_invalid_workflow(self, db_session, sample_node_data):
        """Test node creation with invalid workflow raises error."""
        node_data = NodeCreate(**sample_node_data)

        with pytest.raises(InvalidNodeReferenceError):
            await NodeService(db_session).create(uuid4(), node_data)

    @pytest.mark.asyncio
    async def test_create_node_integrity_error(
        self, db_session, workflow_factory, sample_node_data
    ):
        """Test node creation with IntegrityError raises InvalidNodeReferenceError."""
        from unittest.mock import patch

        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        node_data = NodeCreate(**sample_node_data)

        # Mock flush to raise IntegrityError
        async def mock_flush_integrity():
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("INSERT INTO nodes", {}, Exception())

        with (
            patch.object(db_session, "flush", side_effect=mock_flush_integrity),
            pytest.raises(InvalidNodeReferenceError, match="Invalid node reference"),
        ):
            await NodeService(db_session).create(workflow.id, node_data)

    @pytest.mark.asyncio
    async def test_get_node_success(self, db_session, node_factory):
        """Test successful node retrieval."""
        node = node_factory()
        db_session.add(node)
        await db_session.flush()

        result = await NodeService(db_session).get(node.id)

        assert result is not None
        assert result.id == node.id
        assert result.name == node.name

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, db_session):
        """Test getting non-existent node returns None."""
        result = await NodeService(db_session).get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_nodes_by_workflow(
        self, db_session, workflow_factory, node_factory
    ):
        """Test listing nodes by workflow."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id, name="Node 1")
        node2 = node_factory(workflow_id=workflow.id, name="Node 2")
        node3 = node_factory(workflow_id=uuid4(), name="Node 3")

        db_session.add_all([workflow, node1, node2, node3])
        await db_session.flush()

        nodes = await NodeService(db_session).list_by_workflow(workflow.id)

        assert len(nodes) == 2
        assert all(n.workflow_id == workflow.id for n in nodes)

    @pytest.mark.asyncio
    async def test_update_node_success(self, db_session, node_factory):
        """Test successful node update."""
        node = node_factory(name="Original Name")
        db_session.add(node)
        await db_session.flush()

        update_data = NodeUpdate(name="Updated Name", position_x=100)
        updated = await NodeService(db_session).update(node.id, update_data)

        assert updated.name == "Updated Name"
        assert updated.position_x == 100
        assert updated.updated_at >= node.updated_at

    @pytest.mark.asyncio
    async def test_update_node_not_found(self, db_session):
        """Test updating non-existent node raises error."""
        update_data = NodeUpdate(name="Test")

        with pytest.raises(NodeNotFoundError):
            await NodeService(db_session).update(uuid4(), update_data)

    @pytest.mark.asyncio
    async def test_update_node_with_nonexistent_field(self, db_session, node_factory):
        """Test node update with non-existent field (hasattr False branch)."""
        node = node_factory(name="Original Name", position_x=50)
        db_session.add(node)
        await db_session.flush()

        # Create mock update data with non-existent fields
        class NonexistentNodeUpdate:
            def model_dump(
                self,
                *,
                mode: str = "python",
                exclude=None,
                exclude_unset: bool = True,
                **kwargs,
            ):
                return {"non_existent_field": "value"}

        update_data = NonexistentNodeUpdate()

        # The update should skip non-existent fields
        updated = await NodeService(db_session).update(node.id, update_data)

        # Original values should remain unchanged
        assert updated.name == "Original Name"
        assert updated.position_x == 50

    @pytest.mark.asyncio
    async def test_delete_node_success(self, db_session, node_factory):
        """Test successful node deletion."""
        node = node_factory()
        db_session.add(node)
        await db_session.flush()

        deleted = await NodeService(db_session).delete(node.id)

        assert deleted.id == node.id

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self, db_session):
        """Test deleting non-existent node raises error."""
        with pytest.raises(NodeNotFoundError):
            await NodeService(db_session).delete(uuid4())

    @pytest.mark.asyncio
    async def test_batch_create_nodes(
        self, db_session, workflow_factory, sample_node_data
    ):
        """Test batch creating nodes."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        # Create node data without name to avoid duplicate argument
        base_node_data = {k: v for k, v in sample_node_data.items() if k != "name"}

        nodes_data = NodeBatchCreate(
            nodes=[
                NodeCreate(**base_node_data, name="Node 1"),
                NodeCreate(**base_node_data, name="Node 2"),
                NodeCreate(**base_node_data, name="Node 3"),
            ]
        )

        created = await NodeService(db_session).batch_create(workflow.id, nodes_data)

        assert len(created) == 3
        assert all(n.workflow_id == workflow.id for n in created)

    @pytest.mark.asyncio
    async def test_batch_create_nodes_invalid_workflow(
        self, db_session, sample_node_data
    ):
        """Test batch creating nodes with invalid workflow raises error."""
        base_node_data = {k: v for k, v in sample_node_data.items() if k != "name"}

        nodes_data = NodeBatchCreate(
            nodes=[
                NodeCreate(**base_node_data, name="Node 1"),
            ]
        )

        with pytest.raises(InvalidNodeReferenceError, match=r"Workflow .* not found"):
            await NodeService(db_session).batch_create(uuid4(), nodes_data)

    @pytest.mark.asyncio
    async def test_batch_create_with_plain_list(
        self, db_session, workflow_factory, sample_node_data
    ):
        """Test batch creating nodes with plain list (not NodeBatchCreate)."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        # Create node data without name to avoid duplicate argument
        base_node_data = {k: v for k, v in sample_node_data.items() if k != "name"}

        # Pass plain list instead of NodeBatchCreate
        nodes_list = [
            NodeCreate(**base_node_data, name="Node A"),
            NodeCreate(**base_node_data, name="Node B"),
        ]

        created = await NodeService(db_session).batch_create(workflow.id, nodes_list)

        assert len(created) == 2
        assert all(n.workflow_id == workflow.id for n in created)

    @pytest.mark.asyncio
    async def test_batch_create_with_fallback(
        self, db_session, workflow_factory, sample_node_data
    ):
        """Test batch creating nodes with fallback to original object."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        # Create node data without name to avoid duplicate argument
        base_node_data = {k: v for k, v in sample_node_data.items() if k != "name"}

        # Create a custom object that doesn't have .nodes attribute and is not a list
        # This should fall through to the else branch (line 354)
        class CustomNodesData:
            def __init__(self, nodes_list):
                self._nodes = nodes_list

            def __iter__(self):
                return iter(self._nodes)

        nodes_list = [
            NodeCreate(**base_node_data, name="Node X"),
            NodeCreate(**base_node_data, name="Node Y"),
        ]
        custom_data = CustomNodesData(nodes_list)

        created = await NodeService(db_session).batch_create(workflow.id, custom_data)

        assert len(created) == 2
        assert all(n.workflow_id == workflow.id for n in created)


# =============================================================================
# EdgeService Tests
# =============================================================================


class TestEdgeService:
    """Test suite for EdgeService."""

    @pytest.mark.asyncio
    async def test_create_edge_success(
        self, db_session, workflow_factory, node_factory
    ):
        """Test successful edge creation."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        edge_data = EdgeCreate(
            source_node_id=node1.id,
            target_node_id=node2.id,
            source_handle="output",
            target_handle="input",
        )

        edge = await EdgeService(db_session).create(workflow.id, edge_data)

        assert edge.id is not None
        assert edge.workflow_id == workflow.id
        assert edge.source_node_id == node1.id
        assert edge.target_node_id == node2.id

    @pytest.mark.asyncio
    async def test_create_edge_integrity_error(
        self, db_session, workflow_factory, node_factory
    ):
        """Test edge creation with IntegrityError raises InvalidNodeReferenceError."""
        from unittest.mock import patch

        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        edge_data = EdgeCreate(
            source_node_id=node1.id,
            target_node_id=node2.id,
        )

        # Mock flush to raise IntegrityError
        async def mock_flush_integrity():
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("INSERT INTO edges", {}, Exception())

        with (
            patch.object(db_session, "flush", side_effect=mock_flush_integrity),
            pytest.raises(InvalidNodeReferenceError, match="Invalid edge reference"),
        ):
            await EdgeService(db_session).create(workflow.id, edge_data)

    @pytest.mark.asyncio
    async def test_create_edge_cycle_detection(
        self, db_session, workflow_factory, node_factory
    ):
        """Test that edge creation detects cycles."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        # Create first edge
        edge1_data = EdgeCreate(
            source_node_id=node1.id,
            target_node_id=node2.id,
        )
        await EdgeService(db_session).create(workflow.id, edge1_data)

        # Try to create edge that would form a cycle
        edge2_data = EdgeCreate(
            source_node_id=node2.id,
            target_node_id=node1.id,
        )

        with pytest.raises(DAGValidationError, match="cycle"):
            await EdgeService(db_session).create(workflow.id, edge2_data)

    @pytest.mark.asyncio
    async def test_create_edge_invalid_nodes(self, db_session, workflow_factory):
        """Test edge creation with invalid node references."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        edge_data = EdgeCreate(
            source_node_id=uuid4(),
            target_node_id=uuid4(),
        )

        with pytest.raises(InvalidNodeReferenceError):
            await EdgeService(db_session).create(workflow.id, edge_data)

    @pytest.mark.asyncio
    async def test_get_edge_success(self, db_session, edge_factory):
        """Test successful edge retrieval."""
        edge = edge_factory()
        db_session.add(edge)
        await db_session.flush()

        result = await EdgeService(db_session).get(edge.id)

        assert result is not None
        assert result.id == edge.id

    @pytest.mark.asyncio
    async def test_get_edge_not_found(self, db_session):
        """Test getting non-existent edge returns None."""
        result = await EdgeService(db_session).get(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_edges_by_workflow(
        self, db_session, workflow_factory, edge_factory
    ):
        """Test listing edges by workflow."""
        workflow = workflow_factory()
        edge1 = edge_factory(workflow_id=workflow.id)
        edge2 = edge_factory(workflow_id=workflow.id)
        edge3 = edge_factory(workflow_id=uuid4())

        db_session.add_all([workflow, edge1, edge2, edge3])
        await db_session.flush()

        edges = await EdgeService(db_session).list_by_workflow(workflow.id)

        assert len(edges) == 2
        assert all(e.workflow_id == workflow.id for e in edges)

    @pytest.mark.asyncio
    async def test_delete_edge_success(self, db_session, edge_factory):
        """Test successful edge deletion."""
        edge = edge_factory()
        db_session.add(edge)
        await db_session.flush()

        deleted = await EdgeService(db_session).delete(edge.id)

        assert deleted.id == edge.id

    @pytest.mark.asyncio
    async def test_delete_edge_not_found(self, db_session):
        """Test deleting non-existent edge raises error."""
        with pytest.raises(EdgeNotFoundError):
            await EdgeService(db_session).delete(uuid4())

    @pytest.mark.asyncio
    async def test_batch_create_edges(self, db_session, workflow_factory, node_factory):
        """Test batch creating edges."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)
        node3 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2, node3])
        await db_session.flush()

        edges_data = EdgeBatchCreate(
            edges=[
                EdgeCreate(source_node_id=node1.id, target_node_id=node2.id),
                EdgeCreate(source_node_id=node2.id, target_node_id=node3.id),
            ]
        )

        created = await EdgeService(db_session).batch_create(workflow.id, edges_data)

        assert len(created) == 2
        assert all(e.workflow_id == workflow.id for e in created)

    @pytest.mark.asyncio
    async def test_batch_create_edges_with_plain_list(
        self, db_session, workflow_factory, node_factory
    ):
        """Test batch creating edges with plain list (not EdgeBatchCreate)."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)
        node3 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2, node3])
        await db_session.flush()

        # Pass plain list instead of EdgeBatchCreate
        edges_list = [
            EdgeCreate(source_node_id=node1.id, target_node_id=node2.id),
            EdgeCreate(source_node_id=node2.id, target_node_id=node3.id),
        ]

        created = await EdgeService(db_session).batch_create(workflow.id, edges_list)

        assert len(created) == 2
        assert all(e.workflow_id == workflow.id for e in created)

    @pytest.mark.asyncio
    async def test_batch_create_edges_with_fallback(
        self, db_session, workflow_factory, node_factory
    ):
        """Test batch creating edges with fallback to original object."""
        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        # Create a custom object that doesn't have .edges attribute and is not a list
        # This should fall through to the else branch (line 452)
        class CustomEdgesData:
            def __init__(self, edges_list):
                self._edges = edges_list

            def __iter__(self):
                return iter(self._edges)

        edges_list = [
            EdgeCreate(source_node_id=node1.id, target_node_id=node2.id),
        ]
        custom_data = CustomEdgesData(edges_list)

        created = await EdgeService(db_session).batch_create(workflow.id, custom_data)

        assert len(created) == 1
        assert created[0].workflow_id == workflow.id

    @pytest.mark.asyncio
    async def test_batch_create_edges_integrity_error(
        self, db_session, workflow_factory, node_factory
    ):
        """Test batch edge creation with IntegrityError raises InvalidNodeReferenceError."""
        from unittest.mock import patch

        workflow = workflow_factory()
        node1 = node_factory(workflow_id=workflow.id)
        node2 = node_factory(workflow_id=workflow.id)

        db_session.add_all([workflow, node1, node2])
        await db_session.flush()

        edges_list = [
            EdgeCreate(source_node_id=node1.id, target_node_id=node2.id),
        ]

        # Mock flush to raise IntegrityError
        async def mock_flush_integrity():
            from sqlalchemy.exc import IntegrityError

            raise IntegrityError("INSERT INTO edges", {}, Exception())

        with (
            patch.object(db_session, "flush", side_effect=mock_flush_integrity),
            pytest.raises(InvalidNodeReferenceError, match="Invalid edge reference"),
        ):
            await EdgeService(db_session).batch_create(workflow.id, edges_list)

    @pytest.mark.asyncio
    async def test_dag_validation_complex_cycle(
        self, db_session, workflow_factory, node_factory
    ):
        """Test DAG validation detects complex cycles (A->B->C->A)."""
        workflow = workflow_factory()
        node_a = node_factory(workflow_id=workflow.id, name="A")
        node_b = node_factory(workflow_id=workflow.id, name="B")
        node_c = node_factory(workflow_id=workflow.id, name="C")

        db_session.add_all([workflow, node_a, node_b, node_c])
        await db_session.flush()

        # Create A->B and B->C
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_b.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b.id, target_node_id=node_c.id),
        )

        # Try to create C->A (completes the cycle)
        with pytest.raises(DAGValidationError, match="cycle"):
            await EdgeService(db_session).create(
                workflow.id,
                EdgeCreate(source_node_id=node_c.id, target_node_id=node_a.id),
            )

    @pytest.mark.asyncio
    async def test_dag_validation_allows_acyclic_graph(
        self, db_session, workflow_factory, node_factory
    ):
        """Test that acyclic graphs are allowed."""
        workflow = workflow_factory()
        node_a = node_factory(workflow_id=workflow.id, name="A")
        node_b = node_factory(workflow_id=workflow.id, name="B")
        node_c = node_factory(workflow_id=workflow.id, name="C")

        db_session.add_all([workflow, node_a, node_b, node_c])
        await db_session.flush()

        # Create A->B, A->C, B->C (all valid, no cycles)
        edge1 = await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_b.id),
        )
        edge2 = await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_c.id),
        )
        edge3 = await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b.id, target_node_id=node_c.id),
        )

        assert edge1.id is not None
        assert edge2.id is not None
        assert edge3.id is not None

    @pytest.mark.asyncio
    async def test_has_cycle_complex_graph(
        self, db_session, workflow_factory, node_factory
    ):
        """Test DFS cycle detection in complex graph with multiple branches."""
        workflow = workflow_factory()
        node_a = node_factory(workflow_id=workflow.id, name="A")
        node_b = node_factory(workflow_id=workflow.id, name="B")
        node_c = node_factory(workflow_id=workflow.id, name="C")
        node_d = node_factory(workflow_id=workflow.id, name="D")
        node_e = node_factory(workflow_id=workflow.id, name="E")

        db_session.add_all([workflow, node_a, node_b, node_c, node_d, node_e])
        await db_session.flush()

        # Create complex graph with multiple paths to test visited tracking
        # A->B, A->C, B->D, C->D, D->E
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_b.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_c.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b.id, target_node_id=node_d.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_c.id, target_node_id=node_d.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_d.id, target_node_id=node_e.id),
        )

        # Try to create E->A (would create cycle through D, which has multiple parents)
        with pytest.raises(DAGValidationError, match="cycle"):
            await EdgeService(db_session).create(
                workflow.id,
                EdgeCreate(source_node_id=node_e.id, target_node_id=node_a.id),
            )

    @pytest.mark.asyncio
    async def test_dag_validation_diamond_pattern(
        self, db_session, workflow_factory, node_factory
    ):
        """Test DAG validation with diamond pattern (A->B, A->C, B->D, C->D).

        This tests the visited tracking in _has_cycle - node D should be
        visited from both B and C paths but not cause a false cycle detection.
        """
        workflow = workflow_factory()
        node_a = node_factory(workflow_id=workflow.id, name="A")
        node_b = node_factory(workflow_id=workflow.id, name="B")
        node_c = node_factory(workflow_id=workflow.id, name="C")
        node_d = node_factory(workflow_id=workflow.id, name="D")

        db_session.add_all([workflow, node_a, node_b, node_c, node_d])
        await db_session.flush()

        # Create diamond pattern: A->B, A->C, B->D, C->D
        # When adding C->D, DFS from D should visit D (already in visited from B path)
        # This tests the "if node in visited: return False" branch
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_b.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a.id, target_node_id=node_c.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b.id, target_node_id=node_d.id),
        )
        # This should not raise an error - diamond pattern is valid
        edge4 = await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_c.id, target_node_id=node_d.id),
        )

        assert edge4.id is not None

        # Now try to create D->A which would create a cycle
        with pytest.raises(DAGValidationError, match="cycle"):
            await EdgeService(db_session).create(
                workflow.id,
                EdgeCreate(source_node_id=node_d.id, target_node_id=node_a.id),
            )

    @pytest.mark.asyncio
    async def test_dag_validation_with_complex_dag(
        self, db_session, workflow_factory, node_factory
    ):
        """Test DAG validation with complex graph that has shared nodes.

        This creates a graph where during DFS traversal, the algorithm encounters
        a node that was already visited, triggering the 'if node in visited' branch.
        """
        workflow = workflow_factory()
        node_start = node_factory(workflow_id=workflow.id, name="Start")
        node_a1 = node_factory(workflow_id=workflow.id, name="A1")
        node_a2 = node_factory(workflow_id=workflow.id, name="A2")
        node_b1 = node_factory(workflow_id=workflow.id, name="B1")
        node_b2 = node_factory(workflow_id=workflow.id, name="B2")
        node_shared = node_factory(workflow_id=workflow.id, name="Shared")
        node_end = node_factory(workflow_id=workflow.id, name="End")

        db_session.add_all(
            [
                workflow,
                node_start,
                node_a1,
                node_a2,
                node_b1,
                node_b2,
                node_shared,
                node_end,
            ]
        )
        await db_session.flush()

        # Create a complex DAG with shared nodes:
        # Start -> A1 -> Shared -> End
        # Start -> A2 -> Shared
        # A1 -> B1 -> Shared
        # A2 -> B2 -> Shared
        # This creates multiple paths to 'Shared' node

        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_start.id, target_node_id=node_a1.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_start.id, target_node_id=node_a2.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a1.id, target_node_id=node_shared.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a2.id, target_node_id=node_shared.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a1.id, target_node_id=node_b1.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_a2.id, target_node_id=node_b2.id),
        )
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b1.id, target_node_id=node_shared.id),
        )

        # Now add B2 -> Shared, which should trigger the visited check
        # since Shared is already reachable through multiple paths
        edge = await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_b2.id, target_node_id=node_shared.id),
        )

        assert edge.id is not None

        # Now create Shared -> End
        await EdgeService(db_session).create(
            workflow.id,
            EdgeCreate(source_node_id=node_shared.id, target_node_id=node_end.id),
        )

        # Try to create a cycle: End -> Start
        with pytest.raises(DAGValidationError, match="cycle"):
            await EdgeService(db_session).create(
                workflow.id,
                EdgeCreate(source_node_id=node_end.id, target_node_id=node_start.id),
            )
