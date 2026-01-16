"""Unit tests for ExecutionService classes.

TAG: [SPEC-007] [TESTS] [SERVICES] [EXECUTION]
REQ: REQ-001 - WorkflowExecutionService Tests
REQ: REQ-002 - NodeExecutionService Tests
REQ: REQ-003 - ExecutionLogService Tests
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.enums import ExecutionStatus, LogLevel
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.schemas.execution import (
    WorkflowExecutionCreate,
)
from app.services.execution_service import (
    ExecutionLogService,
    NodeExecutionService,
    WorkflowExecutionService,
)

# =============================================================================
# WorkflowExecutionService Tests
# =============================================================================


class TestWorkflowExecutionService:
    """Test suite for WorkflowExecutionService."""

    @pytest.mark.asyncio
    async def test_create_execution_success(self, db_session, sample_execution_data):
        """Test successful workflow execution creation."""
        execution_data = WorkflowExecutionCreate(**sample_execution_data)
        workflow_id = uuid4()

        execution = await WorkflowExecutionService.create(
            db_session, workflow_id, execution_data
        )

        assert execution.id is not None
        assert execution.workflow_id == workflow_id
        assert execution.status == ExecutionStatus.PENDING
        assert execution.trigger_type.value == "manual"
        assert execution.input_data == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_execution_success(self, db_session):
        """Test successful workflow execution retrieval."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.PENDING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.flush()

        result = await WorkflowExecutionService.get(db_session, execution.id)

        assert result is not None
        assert result.id == execution.id

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, db_session):
        """Test getting non-existent execution returns None."""
        result = await WorkflowExecutionService.get(db_session, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_nodes_success(self, db_session):
        """Test getting execution with node executions."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=execution.id,
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={},
            retry_count=0,
        )

        db_session.add_all([execution, node_exec])
        await db_session.flush()

        result = await WorkflowExecutionService.get_with_nodes(db_session, execution.id)

        assert result is not None
        assert len(result.node_executions) == 1

    @pytest.mark.asyncio
    async def test_list_executions(self, db_session):
        """Test listing executions with pagination and filtering."""
        workflow_id = uuid4()
        execution1 = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            status=ExecutionStatus.PENDING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        execution2 = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        execution3 = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),  # Different workflow
            status=ExecutionStatus.PENDING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )

        db_session.add_all([execution1, execution2, execution3])
        await db_session.flush()

        # List all for workflow
        executions = await WorkflowExecutionService.list(
            db_session, workflow_id, skip=0, limit=10
        )
        assert len(executions) == 2

        # Filter by status
        pending_executions = await WorkflowExecutionService.list(
            db_session, workflow_id, skip=0, limit=10, status=ExecutionStatus.PENDING
        )
        assert len(pending_executions) == 1

    @pytest.mark.asyncio
    async def test_count_executions(self, db_session):
        """Test counting executions."""
        workflow_id = uuid4()
        execution1 = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            status=ExecutionStatus.PENDING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        execution2 = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )

        db_session.add_all([execution1, execution2])
        await db_session.flush()

        # Count all
        total = await WorkflowExecutionService.count(db_session, workflow_id)
        assert total == 2

        # Count by status
        pending_count = await WorkflowExecutionService.count(
            db_session, workflow_id, status=ExecutionStatus.PENDING
        )
        assert pending_count == 1

    @pytest.mark.asyncio
    async def test_start_execution_success(self, db_session):
        """Test starting an execution."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.PENDING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            created_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.flush()

        started = await WorkflowExecutionService.start(db_session, execution.id)

        assert started.status == ExecutionStatus.RUNNING
        assert started.started_at is not None

    @pytest.mark.asyncio
    async def test_start_execution_not_found(self, db_session):
        """Test starting non-existent execution raises error."""
        with pytest.raises(ValueError, match="not found"):
            await WorkflowExecutionService.start(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_complete_execution_success(self, db_session):
        """Test completing an execution."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.flush()

        output = {"result": "success"}
        completed = await WorkflowExecutionService.complete(
            db_session, execution.id, output_data=output
        )

        assert completed.status == ExecutionStatus.COMPLETED
        assert completed.ended_at is not None
        assert completed.output_data == output

    @pytest.mark.asyncio
    async def test_complete_execution_not_found(self, db_session):
        """Test completing non-existent execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await WorkflowExecutionService.complete(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_fail_execution_success(self, db_session):
        """Test failing an execution."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.flush()

        error_msg = "Database connection failed"
        failed = await WorkflowExecutionService.fail(
            db_session, execution.id, error_msg
        )

        assert failed.status == ExecutionStatus.FAILED
        assert failed.ended_at is not None
        assert failed.error_message == error_msg

    @pytest.mark.asyncio
    async def test_fail_execution_not_found(self, db_session):
        """Test failing non-existent execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await WorkflowExecutionService.fail(db_session, uuid4(), "Error")

    @pytest.mark.asyncio
    async def test_cancel_execution_success(self, db_session):
        """Test cancelling an execution."""
        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.flush()

        cancelled = await WorkflowExecutionService.cancel(db_session, execution.id)

        assert cancelled.status == ExecutionStatus.CANCELLED
        assert cancelled.ended_at is not None

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, db_session):
        """Test cancelling non-existent execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await WorkflowExecutionService.cancel(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_get_statistics(self, db_session):
        """Test getting execution statistics."""
        workflow_id = uuid4()

        # Create various execution states
        now = datetime.now(UTC)
        executions = [
            WorkflowExecution(
                id=uuid4(),
                workflow_id=workflow_id,
                status=ExecutionStatus.COMPLETED,
                trigger_type="manual",
                input_data={},
                context={},
                metadata_={},
                started_at=now,
                ended_at=now,
                created_at=now,
            ),
            WorkflowExecution(
                id=uuid4(),
                workflow_id=workflow_id,
                status=ExecutionStatus.FAILED,
                trigger_type="manual",
                input_data={},
                context={},
                metadata_={},
                started_at=now,
                ended_at=now,
                created_at=now,
            ),
            WorkflowExecution(
                id=uuid4(),
                workflow_id=workflow_id,
                status=ExecutionStatus.RUNNING,
                trigger_type="manual",
                input_data={},
                context={},
                metadata_={},
                started_at=now,
                created_at=now,
            ),
            WorkflowExecution(
                id=uuid4(),
                workflow_id=workflow_id,
                status=ExecutionStatus.PENDING,
                trigger_type="manual",
                input_data={},
                context={},
                metadata_={},
                created_at=now,
            ),
        ]

        db_session.add_all(executions)
        await db_session.flush()

        stats = await WorkflowExecutionService.get_statistics(db_session, workflow_id)

        assert stats.total_executions == 4
        assert stats.completed == 1
        assert stats.failed == 1
        assert stats.running == 1
        assert stats.pending == 1
        assert stats.cancelled == 0
        assert stats.success_rate == 0.5  # 1 completed out of 2 terminal

    @pytest.mark.asyncio
    async def test_get_statistics_negative_duration(self, db_session):
        """Test statistics handles negative duration values correctly."""
        workflow_id = uuid4()

        # Create execution with negative duration (ended before started)
        # This simulates edge case in timing
        now = datetime.now(UTC)
        future = datetime.now(UTC)

        execution = WorkflowExecution(
            id=uuid4(),
            workflow_id=workflow_id,
            status=ExecutionStatus.COMPLETED,
            trigger_type="manual",
            input_data={},
            context={},
            metadata_={},
            started_at=future,  # Later
            ended_at=now,  # Earlier - creates negative duration
            created_at=now,
        )

        db_session.add(execution)
        await db_session.flush()

        stats = await WorkflowExecutionService.get_statistics(db_session, workflow_id)

        # Negative duration should be handled (filtered out)
        assert stats.total_executions == 1
        assert stats.avg_duration_seconds is None  # Negative filtered out


# =============================================================================
# NodeExecutionService Tests
# =============================================================================


class TestNodeExecutionService:
    """Test suite for NodeExecutionService."""

    @pytest.mark.asyncio
    async def test_create_node_execution_success(self, db_session):
        """Test successful node execution creation."""
        workflow_execution_id = uuid4()
        node_id = uuid4()

        node_execution = await NodeExecutionService.create(
            db_session, workflow_execution_id, node_id, execution_order=0
        )

        assert node_execution.id is not None
        assert node_execution.workflow_execution_id == workflow_execution_id
        assert node_execution.node_id == node_id
        assert node_execution.status == ExecutionStatus.PENDING
        assert node_execution.execution_order == 0
        assert node_execution.retry_count == 0

    @pytest.mark.asyncio
    async def test_get_node_execution_success(self, db_session):
        """Test successful node execution retrieval."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        result = await NodeExecutionService.get(db_session, node_exec.id)

        assert result is not None
        assert result.id == node_exec.id

    @pytest.mark.asyncio
    async def test_get_node_execution_not_found(self, db_session):
        """Test getting non-existent node execution returns None."""
        result = await NodeExecutionService.get(db_session, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_execution(self, db_session):
        """Test listing node executions by workflow execution."""
        workflow_execution_id = uuid4()
        node_exec1 = NodeExecution(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        node_exec2 = NodeExecution(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_id=uuid4(),
            status=ExecutionStatus.COMPLETED,
            execution_order=1,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )

        db_session.add_all([node_exec1, node_exec2])
        await db_session.flush()

        result = await NodeExecutionService.list_by_execution(
            db_session, workflow_execution_id
        )

        assert len(result) == 2
        assert result[0].execution_order == 0
        assert result[1].execution_order == 1

    @pytest.mark.asyncio
    async def test_start_node_execution_success(self, db_session):
        """Test starting a node execution."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        input_data = {"test": "data"}
        started = await NodeExecutionService.start(
            db_session, node_exec.id, input_data=input_data
        )

        assert started.status == ExecutionStatus.RUNNING
        assert started.started_at is not None
        assert started.input_data == input_data

    @pytest.mark.asyncio
    async def test_start_node_execution_not_found(self, db_session):
        """Test starting non-existent node execution raises error."""
        with pytest.raises(ValueError, match="not found"):
            await NodeExecutionService.start(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_start_node_execution_without_input_data(self, db_session):
        """Test starting node execution without input_data preserves existing input_data."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={"existing": "data"},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        started = await NodeExecutionService.start(db_session, node_exec.id)

        assert started.status == ExecutionStatus.RUNNING
        assert started.started_at is not None
        # input_data should be preserved when None is passed
        assert started.input_data == {"existing": "data"}

    @pytest.mark.asyncio
    async def test_start_node_execution_invalid_state(self, db_session):
        """Test starting node execution in invalid state raises error."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,  # Already running
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot start node execution"):
            await NodeExecutionService.start(db_session, node_exec.id)

    @pytest.mark.asyncio
    async def test_complete_node_execution_success(self, db_session):
        """Test completing a node execution."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        output = {"result": "success"}
        completed = await NodeExecutionService.complete(
            db_session, node_exec.id, output_data=output
        )

        assert completed.status == ExecutionStatus.COMPLETED
        assert completed.ended_at is not None
        assert completed.output_data == output

    @pytest.mark.asyncio
    async def test_complete_node_not_found(self, db_session):
        """Test completing non-existent node execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await NodeExecutionService.complete(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_complete_node_invalid_state(self, db_session):
        """Test completing node execution in invalid state raises ValueError."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,  # Not RUNNING
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot complete node execution"):
            await NodeExecutionService.complete(db_session, node_exec.id)

    @pytest.mark.asyncio
    async def test_complete_node_without_output_data(self, db_session):
        """Test completing node execution without output_data preserves existing."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            output_data={"existing": "output"},
        )
        db_session.add(node_exec)
        await db_session.flush()

        # Complete without output_data (None by default)
        completed = await NodeExecutionService.complete(db_session, node_exec.id)

        assert completed.status == ExecutionStatus.COMPLETED
        assert completed.ended_at is not None
        # output_data should be preserved when None is passed
        assert completed.output_data == {"existing": "output"}

    @pytest.mark.asyncio
    async def test_fail_node_execution_success(self, db_session):
        """Test failing a node execution."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        error_msg = "API call failed"
        traceback = "Traceback..."
        failed = await NodeExecutionService.fail(
            db_session, node_exec.id, error_msg, traceback
        )

        assert failed.status == ExecutionStatus.FAILED
        assert failed.ended_at is not None
        assert failed.error_message == error_msg
        assert failed.error_traceback == traceback

    @pytest.mark.asyncio
    async def test_fail_node_not_found(self, db_session):
        """Test failing non-existent node execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await NodeExecutionService.fail(db_session, uuid4(), "Error")

    @pytest.mark.asyncio
    async def test_fail_node_invalid_state(self, db_session):
        """Test failing node execution in invalid state raises ValueError."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,  # Not RUNNING
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot fail node execution"):
            await NodeExecutionService.fail(db_session, node_exec.id, "Error")

    @pytest.mark.asyncio
    async def test_fail_node_without_traceback(self, db_session):
        """Test failing node execution without traceback preserves None."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        error_msg = "API call failed"
        # Fail without traceback (None by default)
        failed = await NodeExecutionService.fail(db_session, node_exec.id, error_msg)

        assert failed.status == ExecutionStatus.FAILED
        assert failed.ended_at is not None
        assert failed.error_message == error_msg
        assert failed.error_traceback is None  # Should remain None

    @pytest.mark.asyncio
    async def test_skip_node_execution_success(self, db_session):
        """Test skipping a node execution."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        skipped = await NodeExecutionService.skip(db_session, node_exec.id)

        assert skipped.status == ExecutionStatus.SKIPPED
        assert skipped.ended_at is not None

    @pytest.mark.asyncio
    async def test_skip_node_not_found(self, db_session):
        """Test skipping non-existent node execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await NodeExecutionService.skip(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_skip_node_invalid_state(self, db_session):
        """Test skipping node execution in invalid state raises ValueError."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.RUNNING,  # Not PENDING
            execution_order=0,
            input_data={},
            retry_count=0,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot skip node execution"):
            await NodeExecutionService.skip(db_session, node_exec.id)

    @pytest.mark.asyncio
    async def test_increment_retry_success(self, db_session):
        """Test incrementing retry count."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.FAILED,
            execution_order=0,
            input_data={},
            retry_count=0,
            error_message="Error",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        retried = await NodeExecutionService.increment_retry(db_session, node_exec.id)

        assert retried.status == ExecutionStatus.PENDING
        assert retried.retry_count == 1
        assert retried.started_at is None
        assert retried.ended_at is None
        assert retried.error_message is None

    @pytest.mark.asyncio
    async def test_increment_retry_not_found(self, db_session):
        """Test retrying non-existent node execution raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await NodeExecutionService.increment_retry(db_session, uuid4())

    @pytest.mark.asyncio
    async def test_increment_retry_invalid_state(self, db_session):
        """Test retrying node execution in invalid state raises error."""
        node_exec = NodeExecution(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_id=uuid4(),
            status=ExecutionStatus.PENDING,  # Not failed
            execution_order=0,
            input_data={},
            retry_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(node_exec)
        await db_session.flush()

        with pytest.raises(ValueError, match="Cannot retry node execution"):
            await NodeExecutionService.increment_retry(db_session, node_exec.id)


# =============================================================================
# ExecutionLogService Tests
# =============================================================================


class TestExecutionLogService:
    """Test suite for ExecutionLogService."""

    @pytest.mark.asyncio
    async def test_create_log_success(self, db_session):
        """Test successful log creation."""
        workflow_execution_id = uuid4()
        node_execution_id = uuid4()

        log = await ExecutionLogService.create(
            db_session,
            workflow_execution_id=workflow_execution_id,
            node_execution_id=node_execution_id,
            level=LogLevel.INFO,
            message="Test log message",
            data={"key": "value"},
        )

        assert log.id is not None
        assert log.workflow_execution_id == workflow_execution_id
        assert log.node_execution_id == node_execution_id
        assert log.level == LogLevel.INFO
        assert log.message == "Test log message"
        assert log.data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_list_by_execution_success(self, db_session):
        """Test listing logs by workflow execution."""
        workflow_execution_id = uuid4()
        log1 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_execution_id=None,
            level=LogLevel.INFO,
            message="Info message",
            timestamp=datetime.now(UTC),
        )
        log2 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_execution_id=None,
            level=LogLevel.ERROR,
            message="Error message",
            timestamp=datetime.now(UTC),
        )
        log3 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),  # Different execution
            node_execution_id=None,
            level=LogLevel.INFO,
            message="Other message",
            timestamp=datetime.now(UTC),
        )

        db_session.add_all([log1, log2, log3])
        await db_session.flush()

        # List all
        logs = await ExecutionLogService.list_by_execution(
            db_session, workflow_execution_id, skip=0, limit=10
        )
        assert len(logs) == 2

        # Filter by level
        error_logs = await ExecutionLogService.list_by_execution(
            db_session, workflow_execution_id, level=LogLevel.ERROR, skip=0, limit=10
        )
        assert len(error_logs) == 1
        assert error_logs[0].level == LogLevel.ERROR

    @pytest.mark.asyncio
    async def test_list_by_node_success(self, db_session):
        """Test listing logs by node execution."""
        node_execution_id = uuid4()
        log1 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_execution_id=node_execution_id,
            level=LogLevel.INFO,
            message="Node log 1",
            timestamp=datetime.now(UTC),
        )
        log2 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_execution_id=node_execution_id,
            level=LogLevel.WARNING,
            message="Node log 2",
            timestamp=datetime.now(UTC),
        )

        db_session.add_all([log1, log2])
        await db_session.flush()

        logs = await ExecutionLogService.list_by_node(db_session, node_execution_id)

        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_list_by_node_with_level_filter(self, db_session):
        """Test listing logs by node execution with level filter."""
        node_execution_id = uuid4()
        log1 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_execution_id=node_execution_id,
            level=LogLevel.INFO,
            message="Node log 1",
            timestamp=datetime.now(UTC),
        )
        log2 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_execution_id=node_execution_id,
            level=LogLevel.ERROR,
            message="Node log 2",
            timestamp=datetime.now(UTC),
        )
        log3 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=uuid4(),
            node_execution_id=node_execution_id,
            level=LogLevel.INFO,
            message="Node log 3",
            timestamp=datetime.now(UTC),
        )

        db_session.add_all([log1, log2, log3])
        await db_session.flush()

        # Filter by INFO level
        logs = await ExecutionLogService.list_by_node(
            db_session, node_execution_id, level=LogLevel.INFO
        )

        assert len(logs) == 2
        assert all(log.level == LogLevel.INFO for log in logs)

    @pytest.mark.asyncio
    async def test_count_logs(self, db_session):
        """Test counting logs."""
        workflow_execution_id = uuid4()
        log1 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_execution_id=None,
            level=LogLevel.INFO,
            message="Info",
            timestamp=datetime.now(UTC),
        )
        log2 = ExecutionLog(
            id=uuid4(),
            workflow_execution_id=workflow_execution_id,
            node_execution_id=None,
            level=LogLevel.ERROR,
            message="Error",
            timestamp=datetime.now(UTC),
        )

        db_session.add_all([log1, log2])
        await db_session.flush()

        # Count all
        total = await ExecutionLogService.count(db_session, workflow_execution_id)
        assert total == 2

        # Count by level
        error_count = await ExecutionLogService.count(
            db_session, workflow_execution_id, level=LogLevel.ERROR
        )
        assert error_count == 1
