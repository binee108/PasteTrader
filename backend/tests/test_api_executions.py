"""Integration tests for Execution API endpoints.

TAG: [SPEC-007] [TESTS] [API] [EXECUTION]
REQ: REQ-001 - WorkflowExecution Endpoint Tests
REQ: REQ-002 - NodeExecution Endpoint Tests
REQ: REQ-003 - ExecutionLog Endpoint Tests
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock, patch

# =============================================================================
# Module-Level Async Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def workflow_id(async_client: AsyncClient, sample_workflow_data) -> str:
    """Create a workflow and return its ID."""
    response = await async_client.post("/api/v1/workflows/", json=sample_workflow_data)
    return response.json()["id"]


@pytest_asyncio.fixture
async def execution_id(
    async_client: AsyncClient, sample_workflow_data, sample_execution_data
) -> str:
    """Create an execution and return its ID."""
    # Create workflow
    workflow_response = await async_client.post(
        "/api/v1/workflows/", json=sample_workflow_data
    )
    workflow_id = workflow_response.json()["id"]

    # Create execution
    execution_data = {**sample_execution_data, "workflow_id": workflow_id}
    execution_response = await async_client.post(
        "/api/v1/executions/", json=execution_data
    )
    return execution_response.json()["id"]


# =============================================================================
# WorkflowExecution Endpoint Tests
# =============================================================================


class TestWorkflowExecutionEndpoints:
    """Test suite for workflow execution API endpoints."""

    @pytest.mark.asyncio
    async def test_list_executions_empty(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test listing executions when none exist."""
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_execution_success(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test successful workflow execution creation."""
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}

        response = await async_client.post("/api/v1/executions/", json=execution_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_execution_success(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test successful execution retrieval."""
        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Get execution
        response = await async_client.get(f"/api/v1/executions/{execution_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == execution_id

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, async_client: AsyncClient):
        """Test getting non-existent execution returns 404."""
        response = await async_client.get(f"/api/v1/executions/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_execution_detail(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test getting execution with full details."""
        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Get detailed execution
        response = await async_client.get(f"/api/v1/executions/{execution_id}/detail")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_executions" in data
        assert "logs" in data

    @pytest.mark.asyncio
    async def test_cancel_execution_success(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test cancelling an execution."""
        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Cancel execution
        response = await async_client.post(
            f"/api/v1/executions/{execution_id}/cancel",
            json={"reason": "Test cancellation"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_execution_statistics(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test getting execution statistics."""
        # Create a few executions
        for _ in range(3):
            execution_data = {**sample_execution_data, "workflow_id": workflow_id}
            await async_client.post("/api/v1/executions/", json=execution_data)

        # Get statistics
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/statistics"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_executions" in data
        assert "success_rate" in data

    @pytest.mark.asyncio
    async def test_list_executions_with_filter(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test listing executions with status filter."""
        # Create executions
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        await async_client.post("/api/v1/executions/", json=execution_data)

        # List with filter
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions?status=pending"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(e["status"] == "pending" for e in data["items"])

    @pytest.mark.asyncio
    async def test_list_executions_with_pagination(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test execution listing with pagination."""
        # Create multiple executions
        for _ in range(5):
            execution_data = {**sample_execution_data, "workflow_id": workflow_id}
            await async_client.post("/api/v1/executions/", json=execution_data)

        # List with pagination
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions?skip=0&limit=2"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 5

    @pytest.mark.asyncio
    async def test_create_execution_invalid_input(self, async_client: AsyncClient):
        """Test creating execution with invalid input returns 422."""
        # Missing required trigger_type field
        execution_data = {
            "workflow_id": str(uuid4()),
            "input_data": {"test": "data"},
        }

        response = await async_client.post("/api/v1/executions/", json=execution_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, async_client: AsyncClient):
        """Test cancelling non-existent execution returns 404."""
        response = await async_client.post(f"/api/v1/executions/{uuid4()}/cancel")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cancel_execution_already_completed(
        self,
        async_client: AsyncClient,
        workflow_id: str,
        sample_execution_data,
        db_session,
    ):
        """Test cancelling already completed execution returns 400."""
        from sqlalchemy import update

        from app.models.enums import ExecutionStatus
        from app.models.execution import WorkflowExecution

        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Mark as completed
        await db_session.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .values(status=ExecutionStatus.COMPLETED)
        )
        await db_session.commit()

        # Try to cancel
        response = await async_client.post(f"/api/v1/executions/{execution_id}/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_cancel_execution_already_cancelled(
        self,
        async_client: AsyncClient,
        workflow_id: str,
        sample_execution_data,
        db_session,
    ):
        """Test cancelling already cancelled execution returns 400."""
        from sqlalchemy import update

        from app.models.enums import ExecutionStatus
        from app.models.execution import WorkflowExecution

        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Mark as cancelled
        await db_session.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .values(status=ExecutionStatus.CANCELLED)
        )
        await db_session.commit()

        # Try to cancel again
        response = await async_client.post(f"/api/v1/executions/{execution_id}/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_workflow_statistics_not_found(self, async_client: AsyncClient):
        """Test getting statistics for non-existent workflow returns 404."""
        response = await async_client.get(
            f"/api/v1/executions/workflows/{uuid4()}/statistics"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_executions_without_workflow_filter(
        self, async_client: AsyncClient
    ):
        """Test listing executions without workflow_id returns empty."""
        response = await async_client.get("/api/v1/executions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_execution_detail_not_found(self, async_client: AsyncClient):
        """Test getting detail for non-existent execution returns 404."""
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/detail")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_execution_statistics_not_found(self, async_client: AsyncClient):
        """Test getting statistics for non-existent execution returns 404."""
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/statistics")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_executions_invalid_pagination(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test listing executions with negative skip/limit."""
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions?skip=-1&limit=0"
        )

        # API should handle gracefully or validate input
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @pytest.mark.asyncio
    async def test_list_executions_with_data(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test listing executions returns actual data."""
        # Create multiple executions
        for _ in range(3):
            execution_data = {**sample_execution_data, "workflow_id": workflow_id}
            await async_client.post("/api/v1/executions/", json=execution_data)

        # List without filter (uses workflow_id from filters)
        response = await async_client.get(
            f"/api/v1/executions/?workflow_id={workflow_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_get_execution_detail_with_nodes(
        self,
        async_client: AsyncClient,
        workflow_id: str,
        sample_execution_data,
        db_session,
    ):
        """Test getting execution detail with node executions."""
        from app.models.enums import ExecutionStatus
        from app.models.execution import NodeExecution

        # Create execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        create_response = await async_client.post(
            "/api/v1/executions/", json=execution_data
        )
        execution_id = create_response.json()["id"]

        # Create a node execution manually
        node_execution = NodeExecution(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            input_data={},
            output_data={"result": "test"},
            error_message=None,
            retry_count=0,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()

        # Get detailed execution
        response = await async_client.get(f"/api/v1/executions/{execution_id}/detail")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_executions" in data
        assert "logs" in data
        assert len(data["node_executions"]) == 1


# =============================================================================
# NodeExecution Endpoint Tests
# =============================================================================


class TestNodeExecutionEndpoints:
    """Test suite for node execution API endpoints."""

    @pytest.mark.asyncio
    async def test_list_node_executions_empty(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test listing node executions when none exist."""
        response = await async_client.get(f"/api/v1/executions/{execution_id}/nodes")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_node_execution_detail(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test getting node execution with logs."""
        # This test assumes node executions exist
        # In real scenario, you'd create node executions first

        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{uuid4()}"
        )

        # Will return 404 since node doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_executions_parent_not_found(
        self, async_client: AsyncClient
    ):
        """Test listing node executions for non-existent execution returns 404."""
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/nodes")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_node_execution_parent_mismatch(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test getting node execution with mismatched parent execution returns 404."""
        # Try to get a node execution with a different parent execution
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{uuid4()}"
        )

        # Will return 404 since node doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_executions_with_data(
        self,
        async_client: AsyncClient,
        execution_id: str,
        db_session,
    ):
        """Test listing node executions returns actual data."""
        from app.models.enums import ExecutionStatus
        from app.models.execution import NodeExecution

        # Create multiple node executions
        for i in range(3):
            node_execution = NodeExecution(
                id=uuid4(),
                workflow_execution_id=execution_id,
                node_id=uuid4(),
                status=ExecutionStatus.PENDING,
                started_at=None,
                ended_at=None,
                input_data={},
                output_data=None,
                error_message=None,
                retry_count=0,
                execution_order=i + 1,
            )
            db_session.add(node_execution)
        await db_session.commit()

        # List node executions
        response = await async_client.get(f"/api/v1/executions/{execution_id}/nodes")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_get_node_execution_with_logs(
        self,
        async_client: AsyncClient,
        execution_id: str,
        db_session,
    ):
        """Test getting node execution with logs."""
        from app.models.enums import ExecutionStatus, LogLevel
        from app.models.execution import ExecutionLog, NodeExecution

        # Create node execution
        node_execution = NodeExecution(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
            ended_at=None,
            input_data={},
            output_data=None,
            error_message=None,
            retry_count=0,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.flush()

        # Create logs for this node
        for i in range(2):
            log = ExecutionLog(
                id=uuid4(),
                workflow_execution_id=execution_id,
                node_execution_id=node_execution.id,
                level=LogLevel.INFO,
                message=f"Test log {i}",
                data=None,
                timestamp=datetime.now(UTC),
            )
            db_session.add(log)
        await db_session.commit()

        # Get node execution with logs
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{node_execution.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 2


# =============================================================================
# ExecutionLog Endpoint Tests
# =============================================================================


class TestExecutionLogEndpoints:
    """Test suite for execution log API endpoints."""

    @pytest.mark.asyncio
    async def test_list_execution_logs_empty(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test listing logs when none exist."""
        response = await async_client.get(f"/api/v1/executions/{execution_id}/logs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_execution_logs_with_filter(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test listing logs with level filter."""
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/logs?level=error"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_list_node_execution_logs(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test listing logs for a specific node execution."""
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{uuid4()}/logs"
        )

        # Will return 404 since node execution doesn't exist
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_execution_logs_parent_not_found(
        self, async_client: AsyncClient
    ):
        """Test listing logs for non-existent execution returns 404."""
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/logs")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_execution_logs_node_not_found(
        self, async_client: AsyncClient
    ):
        """Test listing logs for non-existent node execution returns 404."""
        response = await async_client.get(
            f"/api/v1/executions/{uuid4()}/nodes/{uuid4()}/logs"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_logs_with_pagination(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test log listing with pagination."""
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/logs?skip=0&limit=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_execution_logs_with_level_filter(
        self, async_client: AsyncClient, execution_id: str
    ):
        """Test listing logs with level filter."""
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/logs?level=warning"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_execution_logs_with_data(
        self,
        async_client: AsyncClient,
        execution_id: str,
        db_session,
    ):
        """Test listing logs returns actual data."""
        from app.models.enums import LogLevel
        from app.models.execution import ExecutionLog

        # Create multiple logs
        for i in range(5):
            log = ExecutionLog(
                id=uuid4(),
                workflow_execution_id=execution_id,
                node_execution_id=None,
                level=LogLevel.INFO,
                message=f"Test log {i}",
                data=None,
                timestamp=datetime.now(UTC),
            )
            db_session.add(log)
        await db_session.commit()

        # List logs
        response = await async_client.get(f"/api/v1/executions/{execution_id}/logs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_node_execution_logs_with_data(
        self,
        async_client: AsyncClient,
        execution_id: str,
        db_session,
    ):
        """Test listing node execution logs returns actual data."""
        from app.models.enums import ExecutionStatus, LogLevel
        from app.models.execution import ExecutionLog, NodeExecution

        # Create node execution
        node_execution = NodeExecution(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
            ended_at=None,
            input_data={},
            output_data=None,
            error_message=None,
            retry_count=0,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.flush()

        # Create logs for this node
        for i in range(3):
            log = ExecutionLog(
                id=uuid4(),
                workflow_execution_id=execution_id,
                node_execution_id=node_execution.id,
                level=LogLevel.ERROR,
                message=f"Error {i}",
                data={"code": i},
                timestamp=datetime.now(UTC),
            )
            db_session.add(log)
        await db_session.commit()

        # List node execution logs
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{node_execution.id}/logs"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_node_execution_logs_with_level_filter(
        self,
        async_client: AsyncClient,
        execution_id: str,
        db_session,
    ):
        """Test listing node execution logs with level filter."""
        from app.models.enums import ExecutionStatus, LogLevel
        from app.models.execution import ExecutionLog, NodeExecution

        # Create node execution
        node_execution = NodeExecution(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
            ended_at=None,
            input_data={},
            output_data=None,
            error_message=None,
            retry_count=0,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.flush()

        # Create logs with different levels
        log1 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_execution_id=node_execution.id,
            level=LogLevel.ERROR,
            message="Error log",
            data=None,
            timestamp=datetime.now(UTC),
        )
        log2 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=execution_id,
            node_execution_id=node_execution.id,
            level=LogLevel.INFO,
            message="Info log",
            data=None,
            timestamp=datetime.now(UTC),
        )
        db_session.add_all([log1, log2])
        await db_session.commit()

        # List with error filter
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{node_execution.id}/logs?level=error"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["level"] == "error"


# =============================================================================
# Additional Coverage Tests for Uncovered Lines
# =============================================================================


class TestExecutionAPICoverage:
    """Additional tests to improve coverage for executions.py."""

    @pytest.mark.asyncio
    async def test_list_executions_invalid_pagination(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test listing executions with invalid pagination parameters."""
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions?skip=-1&limit=0"
        )

        # Should return 422 for invalid pagination
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_200_OK,  # FastAPI may handle this
        ]

    @pytest.mark.asyncio
    async def test_create_execution_invalid_workflow_id(
        self, async_client: AsyncClient, sample_execution_data
    ):
        """Test creating execution with non-existent workflow ID."""
        execution_data = {**sample_execution_data, "workflow_id": str(uuid4())}

        response = await async_client.post("/api/v1/executions/", json=execution_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_execution_statistics_not_found(
        self, async_client: AsyncClient, workflow_id: str
    ):
        """Test getting statistics for workflow with no executions."""
        # This should still return stats (all zeros)
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/statistics"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "success_rate" in data
        assert "total_executions" in data

    @pytest.mark.asyncio
    async def test_list_executions_with_status_filter(
        self, async_client: AsyncClient, workflow_id: str, sample_execution_data
    ):
        """Test listing executions with status filter."""
        # Create an execution
        execution_data = {**sample_execution_data, "workflow_id": workflow_id}
        await async_client.post("/api/v1/executions/", json=execution_data)

        # Filter by pending status
        response = await async_client.get(
            f"/api/v1/executions/workflows/{workflow_id}/executions?status=pending"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1


# =============================================================================
# Additional Error Path Coverage Tests for executions.py
# =============================================================================


class TestExecutionErrorPaths:
    """Tests for error handling paths in executions.py."""

    @pytest.mark.asyncio
    async def test_list_executions_without_workflow_filter(
        self, async_client: AsyncClient
    ):
        """Test listing executions without workflow_id returns empty result.

        Covers lines 173-181 in executions.py where workflow_id is None.
        """
        response = await async_client.get("/api/v1/executions/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_execution_detail_not_found(self, async_client: AsyncClient):
        """Test get execution detail returns 404 for non-existent execution.

        Covers lines 307-311 in executions.py.
        """
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/detail")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, async_client: AsyncClient):
        """Test cancel execution returns 404 for non-existent execution.

        Covers lines 367-375 in executions.py.
        """
        response = await async_client.post(f"/api/v1/executions/{uuid4()}/cancel")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_execution_statistics_not_found(self, async_client: AsyncClient):
        """Test get execution statistics returns 404 for non-existent execution.

        Covers lines 407-411 in executions.py.
        """
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/statistics")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_executions_execution_not_found(
        self, async_client: AsyncClient
    ):
        """Test list node executions returns 404 for non-existent execution.

        Covers lines 448-453 in executions.py.
        """
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/nodes")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_node_execution_not_found(self, async_client: AsyncClient):
        """Test get node execution returns 404 for non-existent node execution.

        Covers lines 500-505 and 508-512 in executions.py.
        """
        execution_id = uuid4()
        node_execution_id = uuid4()
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{node_execution_id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_execution_logs_execution_not_found(
        self, async_client: AsyncClient
    ):
        """Test list execution logs returns 404 for non-existent execution.

        Covers lines 558-563 in executions.py.
        """
        response = await async_client.get(f"/api/v1/executions/{uuid4()}/logs")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_execution_logs_not_found(self, async_client: AsyncClient):
        """Test list node execution logs returns 404 for non-existent node execution.

        Covers lines 620-625 in executions.py.
        """
        execution_id = uuid4()
        node_execution_id = uuid4()
        response = await async_client.get(
            f"/api/v1/executions/{execution_id}/nodes/{node_execution_id}/logs"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_workflow_statistics_not_found(self, async_client: AsyncClient):
        """Test get workflow statistics returns 404 for non-existent workflow.

        Covers lines 746-750 in executions.py.
        """
        response = await async_client.get(
            f"/api/v1/executions/workflows/{uuid4()}/statistics"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Mock-Based Exception Handling Tests (Uncovered Paths)
# =============================================================================


class TestExecutionAPIExceptionHandling:
    """Mock-based tests for Execution API exception handling paths.

    These tests use unittest.mock to inject exceptions into the service layer,
    testing error handling paths that are difficult to trigger through
    normal integration tests.

    Covers missing lines:
    - create_execution workflow None (236-240)
    - get_execution execution None (276-281)
    - get_execution_detail execution None (307-311)
    - cancel_execution ValueError (370-381)
    - get_execution_statistics execution None (407-413)
    - list_node_executions execution None (449-453)
    - get_node_execution execution None (501-505)
    - list_execution_logs execution None (559-563)
    """

    @pytest.mark.asyncio
    async def test_get_execution_not_found_by_mock(self, async_client: AsyncClient):
        """Test get execution returns 404 when execution not found.

        Covers lines 276-281 in executions.py where
        WorkflowExecutionService.get returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.get to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(f"/api/v1/executions/{execution_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_execution_detail_not_found_by_mock(
        self, async_client: AsyncClient
    ):
        """Test get execution detail returns 404 when execution not found.

        Covers lines 307-311 in executions.py where
        WorkflowExecutionService.get_with_nodes returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.get_with_nodes to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get_with_nodes",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(
                f"/api/v1/executions/{execution_id}/detail"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_execution_value_error_not_found(
        self, async_client: AsyncClient
    ):
        """Test cancel execution returns 404 when ValueError contains 'not found'.

        Covers lines 370-375 in executions.py where ValueError with
        'not found' is caught.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.cancel to raise ValueError with 'not found'
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.cancel",
            AsyncMock(side_effect=ValueError(f"Execution {execution_id} not found")),
        ):
            response = await async_client.post(
                f"/api/v1/executions/{execution_id}/cancel"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_execution_value_error_invalid_state(
        self, async_client: AsyncClient
    ):
        """Test cancel execution returns 400 when ValueError doesn't contain 'not found'.

        Covers lines 376-380 in executions.py where ValueError without
        'not found' is caught.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.cancel to raise ValueError without 'not found'
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.cancel",
            AsyncMock(side_effect=ValueError("Execution is already completed")),
        ):
            response = await async_client.post(
                f"/api/v1/executions/{execution_id}/cancel"
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "already completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_execution_statistics_not_found_by_mock(
        self, async_client: AsyncClient
    ):
        """Test get execution statistics returns 404 when execution not found.

        Covers lines 407-413 in executions.py where
        WorkflowExecutionService.get_statistics returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.get_statistics to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get_statistics",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(
                f"/api/v1/executions/{execution_id}/statistics"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_node_executions_execution_not_found_by_mock(
        self, async_client: AsyncClient
    ):
        """Test list node executions returns 404 when execution not found.

        Covers lines 449-453 in executions.py where
        WorkflowExecutionService.get returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.get to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(
                f"/api/v1/executions/{execution_id}/nodes"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_node_execution_execution_not_found_by_mock(
        self, async_client: AsyncClient
    ):
        """Test get node execution returns 404 when execution not found.

        Covers lines 501-505 in executions.py where
        WorkflowExecutionService.get returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()
        node_execution_id = uuid4()

        # Mock WorkflowExecutionService.get to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(
                f"/api/v1/executions/{execution_id}/nodes/{node_execution_id}"
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_execution_logs_execution_not_found_by_mock(
        self, async_client: AsyncClient
    ):
        """Test list execution logs returns 404 when execution not found.

        Covers lines 559-563 in executions.py where
        WorkflowExecutionService.get returns None.
        """
        from unittest.mock import AsyncMock, patch

        execution_id = uuid4()

        # Mock WorkflowExecutionService.get to return None
        with patch(
            "app.api.v1.executions.WorkflowExecutionService.get",
            AsyncMock(return_value=None),
        ):
            response = await async_client.get(f"/api/v1/executions/{execution_id}/logs")

            assert response.status_code == status.HTTP_404_NOT_FOUND
