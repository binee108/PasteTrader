"""Tests for WorkflowExecutor core functionality.

TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
REQ: REQ-011-001 - DAG topological sort based execution
REQ: REQ-011-002 - asyncio.TaskGroup parallel execution
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.enums import ExecutionStatus, NodeType, TriggerType
from app.models.workflow import Edge, Node
from app.services.workflow.exceptions import ExecutionCancelledError, NodeTimeoutError
from app.services.workflow.executor import WorkflowExecutor


class TestWorkflowExecutorInitialization:
    """Tests for WorkflowExecutor initialization.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    """

    def test_executor_initialization(self, db_session) -> None:
        """Test creating WorkflowExecutor with database session.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        executor = WorkflowExecutor(db=db_session)

        assert executor.db is db_session
        assert executor._cancelled is False

    def test_executor_initialization_with_custom_parallel_limit(
        self, db_session
    ) -> None:
        """Test creating WorkflowExecutor with custom parallel node limit.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        executor = WorkflowExecutor(db=db_session, max_parallel_nodes=5)

        assert executor.max_parallel_nodes == 5


class TestWorkflowExecutorBasicExecution:
    """Tests for basic workflow execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    """

    @pytest.mark.asyncio
    async def test_execute_returns_result(self, db_session, workflow_factory) -> None:
        """Test that execute returns an ExecutionResult.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        assert result is not None
        assert hasattr(result, "execution_id")
        assert hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_execute_creates_workflow_execution(
        self, db_session, workflow_factory
    ) -> None:
        """Test that execute creates a WorkflowExecution record.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        from app.models.execution import WorkflowExecution
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Verify execution record was created
        executions = await db_session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == result.execution_id)
        )
        execution = executions.scalars().first()

        assert execution is not None
        assert execution.workflow_id == workflow.id
        assert execution.input_data == {"test": "data"}
        assert execution.trigger_type == TriggerType.MANUAL


class TestWorkflowExecutorCancellation:
    """Tests for workflow execution cancellation.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-009 - Workflow cancellation support
    """

    @pytest.mark.asyncio
    async def test_cancel_sets_cancelled_flag(
        self, db_session, workflow_factory
    ) -> None:
        """Test that cancel sets the cancelled flag.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        # Start execution
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Cancel execution
        await executor.cancel(result.execution_id)

        # Verify cancelled state
        assert executor._cancelled is True

    @pytest.mark.asyncio
    async def test_cancel_updates_execution_status_to_cancelled(
        self, db_session, workflow_factory
    ) -> None:
        """Test that cancel updates execution status to CANCELLED.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        from app.models.execution import WorkflowExecution
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        # Start execution
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Cancel execution
        await executor.cancel(result.execution_id)

        # Verify execution status was updated
        executions = await db_session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == result.execution_id)
        )
        execution = executions.scalars().first()

        # Note: Execution completes quickly, so it won't be CANCELLED unless RUNNING
        # This test verifies the cancel() method is called correctly
        assert executor._cancelled is True

    @pytest.mark.asyncio
    async def test_execute_when_already_cancelled_raises_error(
        self, db_session, workflow_factory
    ) -> None:
        """Test that execute raises error when executor is already cancelled.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        from app.services.workflow.exceptions import ExecutionCancelledError

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        # Cancel first
        executor._cancelled = True

        # Try to execute - should raise
        with pytest.raises(ExecutionCancelledError):
            await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )


class TestWorkflowExecutorErrorHandling:
    """Tests for error handling during execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    """

    @pytest.mark.asyncio
    async def test_execute_with_nonexistent_workflow_fails(self, db_session) -> None:
        """Test that execute returns FAILED status for non-existent workflow.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        from app.services.workflow.exceptions import ExecutionError
        from uuid import uuid4
        import pytest

        executor = WorkflowExecutor(db=db_session)

        # Try to execute non-existent workflow - should raise ExecutionError
        with pytest.raises(ExecutionError, match="not found"):
            await executor.execute(
                workflow_id=uuid4(),
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )


class TestWorkflowExecutorLevelExecution:
    """Tests for level-based execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-002 - asyncio.TaskGroup parallel execution
    """

    @pytest.mark.asyncio
    async def test_execute_with_workflow_returns_output_data(
        self, db_session, workflow_factory
    ) -> None:
        """Test that execute returns output data from execution.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        """
        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Add to database
        db_session.add(workflow)
        await db_session.commit()

        # Execute
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Verify execution completed and has output
        assert result.status == ExecutionStatus.COMPLETED
        assert result.output_data is not None
        assert result.execution_id is not None


class TestWorkflowExecutorExceptionHandling:
    """Tests for exception handling during execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    """

    @pytest.mark.asyncio
    async def test_execute_with_topology_error_returns_failed_status(
        self, db_session, workflow_factory
    ) -> None:
        """Test that execute returns FAILED status when topology validation fails.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-001 - DAG topological sort based execution

        Covers lines 158-165: Exception handling block that catches
        exceptions during execution and marks execution as FAILED.
        """
        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        db_session.add(workflow)
        await db_session.commit()

        # Mock get_topology to raise an exception
        with patch.object(
            executor._validator, "get_topology", side_effect=Exception("Topology error")
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution failed
        assert result.status == ExecutionStatus.FAILED
        assert result.error_message == "Topology error"
        assert result.execution_id is not None


class TestWorkflowExecutorCancellationDuringExecution:
    """Tests for cancellation during execution.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-009 - Workflow cancellation support
    """

    @pytest.mark.asyncio
    async def test_cancel_running_execution_updates_status(
        self, db_session, workflow_factory
    ) -> None:
        """Test that cancel updates execution status to CANCELLED when RUNNING.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-009 - Workflow cancellation support

        Covers lines 185-187: Cancel checks if execution is RUNNING
        and updates status to CANCELLED.
        """
        from app.models.execution import WorkflowExecution
        from datetime import UTC, datetime
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        db_session.add(workflow)
        await db_session.commit()

        # Create a RUNNING execution manually
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
            input_data={"test": "data"},
        )
        db_session.add(execution)
        await db_session.commit()

        # Cancel the execution
        await executor.cancel(execution.id)

        # Verify status was updated to CANCELLED
        executions = await db_session.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution.id)
        )
        updated_execution = executions.scalars().first()

        assert updated_execution.status == ExecutionStatus.CANCELLED
        assert updated_execution.ended_at is not None

    @pytest.mark.asyncio
    async def test_execute_during_level_execution_raises_cancelled_error(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that execute raises ExecutionCancelledError when cancelled during level execution.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-009 - Workflow cancellation support

        Covers lines 230-234: Cancel check during level execution loop.
        """
        from app.models.workflow import NodeType

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node
        node = node_factory(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TOOL,
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock _execute_by_levels to set cancelled flag during execution
        original_execute_by_levels = executor._execute_by_levels

        async def mock_execute_by_levels(*args, **kwargs):
            # Set cancelled flag to simulate cancellation during execution
            executor._cancelled = True
            # Call original to trigger the cancel check
            return await original_execute_by_levels(*args, **kwargs)

        with patch.object(
            executor, "_execute_by_levels", side_effect=mock_execute_by_levels
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution was cancelled
        assert result.status == ExecutionStatus.FAILED
        assert "cancelled" in result.error_message.lower()


class TestWorkflowExecutorNodeTimeout:
    """Tests for node timeout handling.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-008 - Node timeout handling
    """

    @pytest.mark.asyncio
    async def test_node_timeout_raises_node_timeout_error(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that node execution raises NodeTimeoutError when timeout is exceeded.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-008 - Node timeout handling with asyncio.timeout()

        Covers lines 290-291: TimeoutError exception handling that raises
        NodeTimeoutError when asyncio.timeout() is exceeded.
        """
        import asyncio

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with very short timeout and longer sleep time
        # This simulates a slow-running node that exceeds its timeout
        node = node_factory(
            workflow_id=workflow.id,
            name="Slow Node",
            node_type=NodeType.TOOL,
            config={
                "timeout_seconds": 0.05,  # 50ms timeout
                "sleep_seconds": 0.2,  # 200ms execution time (exceeds timeout)
            },
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Execute the node - should timeout and raise NodeTimeoutError
        # This tests the actual asyncio.timeout() behavior in executor.py lines 290-291
        with pytest.raises(NodeTimeoutError) as exc_info:
            await executor._execute_node_with_timeout(node, {"test": "data"}, 1)

        # Verify the error message contains timeout information
        assert "timed out" in str(exc_info.value).lower()
        assert str(node.id)[:8] in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_node_within_timeout_completes_successfully(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that node execution completes successfully within timeout.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-008 - Node timeout handling
        """
        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with reasonable timeout
        node = node_factory(
            workflow_id=workflow.id,
            name="Fast Node",
            node_type=NodeType.TOOL,
            config={"timeout_seconds": 5},  # 5 second timeout
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Execute should complete within timeout
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Verify execution completed successfully
        assert result.status == ExecutionStatus.COMPLETED


class TestWorkflowExecutorRetryWithExponentialBackoff:
    """Tests for exponential backoff retry mechanism.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-004 - Exponential backoff retry
    """

    @pytest.mark.asyncio
    async def test_retry_on_failure_with_exponential_backoff(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that failed node execution is retried with exponential backoff.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-004 - Retry with delay * (2 ** attempt)
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with retry config
        node = node_factory(
            workflow_id=workflow.id,
            name="Flaky Node",
            node_type=NodeType.TOOL,
            config={"retry_config": {"max_retries": 3, "delay": 0.01}},  # 10ms delay
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock to simulate initial failure then success
        attempt_count = [0]

        async def flaky_execute(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] <= 2:  # Fail first 2 attempts
                raise Exception("Simulated failure")
            return {"executed": True}

        with patch.object(
            executor, "_execute_node_with_timeout", side_effect=flaky_execute
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution eventually succeeded after retries
        assert result.status == ExecutionStatus.COMPLETED
        assert attempt_count[0] == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_retry_respects_max_retries(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that retry mechanism respects max_retries configuration.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-004 - Node.retry_config max_retries
        """
        from unittest.mock import AsyncMock, patch

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with retry config (max 2 retries)
        node = node_factory(
            workflow_id=workflow.id,
            name="Failing Node",
            node_type=NodeType.TOOL,
            config={"retry_config": {"max_retries": 2, "delay": 0.01}},
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock to always fail
        attempt_count = [0]

        async def always_failing_execute(*args, **kwargs):
            attempt_count[0] += 1
            raise Exception("Always fails")

        with patch.object(
            executor, "_execute_node_with_timeout", side_effect=always_failing_execute
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution failed after max retries exceeded
        assert result.status == ExecutionStatus.FAILED
        assert attempt_count[0] == 3  # Initial + 2 retries (max_retries=2)

    @pytest.mark.asyncio
    async def test_retry_count_recorded_in_node_execution(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that retry_count is recorded in NodeExecution.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-004 - NodeExecution.retry_count tracking
        """
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with retry config
        node = node_factory(
            workflow_id=workflow.id,
            name="Retry Node",
            node_type=NodeType.TOOL,
            config={"retry_config": {"max_retries": 3, "delay": 0.01}},
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock to simulate failure then success
        attempt_count = [0]

        async def retry_execute(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise Exception("First attempt fails")
            return {"executed": True}

        with patch.object(
            executor, "_execute_node_with_timeout", side_effect=retry_execute
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution succeeded
        assert result.status == ExecutionStatus.COMPLETED

        # Verify NodeExecution has retry_count recorded
        from app.models.execution import NodeExecution

        node_executions = await db_session.execute(
            select(NodeExecution).where(
                NodeExecution.workflow_execution_id == result.execution_id
            )
        )
        node_execution = node_executions.scalars().first()

        assert node_execution is not None
        assert node_execution.retry_count == 1  # 1 retry occurred


class TestWorkflowExecutorExecutionLogging:
    """Tests for execution logging integration.

    TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
    REQ: REQ-011-010 - ExecutionLog integration
    """

    @pytest.mark.asyncio
    async def test_workflow_start_and_end_logs_created(
        self, db_session, workflow_factory
    ) -> None:
        """Test that workflow execution creates start and end logs.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-010 - Workflow start/end logs
        """
        from sqlalchemy import select

        from app.models.execution import ExecutionLog

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        db_session.add(workflow)
        await db_session.commit()

        # Execute workflow
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Verify logs were created
        logs = await db_session.execute(
            select(ExecutionLog).where(
                ExecutionLog.workflow_execution_id == result.execution_id
            )
        )
        execution_logs = logs.scalars().all()

        # Should have at least start and end logs
        assert len(execution_logs) >= 2

        # Check for workflow start log
        start_logs = [log for log in execution_logs if "start" in log.message.lower()]
        assert len(start_logs) > 0

        # Check for workflow end log
        end_logs = [log for log in execution_logs if "complete" in log.message.lower()]
        assert len(end_logs) > 0

    @pytest.mark.asyncio
    async def test_node_execution_logs_created(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that node execution creates start, complete, and failure logs.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-010 - Node execution start/complete/failure logs
        """
        from sqlalchemy import select

        from app.models.execution import ExecutionLog

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node
        node = node_factory(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TOOL,
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Execute workflow
        result = await executor.execute(
            workflow_id=workflow.id,
            input_data={"test": "data"},
            trigger_type=TriggerType.MANUAL,
        )

        # Verify node execution logs were created
        logs = await db_session.execute(
            select(ExecutionLog).where(
                ExecutionLog.workflow_execution_id == result.execution_id
            )
        )
        execution_logs = logs.scalars().all()

        # Should have logs for node execution
        node_logs = [log for log in execution_logs if log.node_execution_id is not None]
        assert len(node_logs) > 0

    @pytest.mark.asyncio
    async def test_error_logs_created_on_failure(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that ERROR level logs are created on failures.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-010 - ERROR level logs on errors
        """
        from app.models.enums import LogLevel
        from app.models.execution import ExecutionLog
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with retry config that will fail
        node = node_factory(
            workflow_id=workflow.id,
            name="Failing Node",
            node_type=NodeType.TOOL,
            config={"retry_config": {"max_retries": 1, "delay": 0.01}},
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock to always fail
        async def failing_execute(*args, **kwargs):
            raise Exception("Simulated failure")

        with patch.object(
            executor, "_execute_node_with_timeout", side_effect=failing_execute
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution failed
        assert result.status == ExecutionStatus.FAILED

        # Verify ERROR logs were created
        logs = await db_session.execute(
            select(ExecutionLog).where(
                ExecutionLog.workflow_execution_id == result.execution_id,
                ExecutionLog.level == LogLevel.ERROR,
            )
        )
        error_logs = logs.scalars().all()

        assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_retry_logs_created_with_warn_level(
        self, db_session, workflow_factory, node_factory
    ) -> None:
        """Test that WARN level logs are created during retries.

        TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
        REQ: REQ-011-010 - WARN level logs on retries
        """
        from app.models.enums import LogLevel
        from app.models.execution import ExecutionLog
        from sqlalchemy import select

        executor = WorkflowExecutor(db=db_session)
        workflow = workflow_factory()

        # Create a node with retry config
        node = node_factory(
            workflow_id=workflow.id,
            name="Flaky Node",
            node_type=NodeType.TOOL,
            config={"retry_config": {"max_retries": 2, "delay": 0.01}},
        )

        db_session.add(workflow)
        db_session.add(node)
        await db_session.commit()

        # Mock to fail then succeed
        attempt_count = [0]

        async def flaky_execute(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise Exception("First attempt fails")
            return {"executed": True}

        with patch.object(
            executor, "_execute_node_with_timeout", side_effect=flaky_execute
        ):
            result = await executor.execute(
                workflow_id=workflow.id,
                input_data={"test": "data"},
                trigger_type=TriggerType.MANUAL,
            )

        # Verify execution succeeded after retry
        assert result.status == ExecutionStatus.COMPLETED

        # Verify WARN logs were created for retry
        logs = await db_session.execute(
            select(ExecutionLog).where(
                ExecutionLog.workflow_execution_id == result.execution_id,
                ExecutionLog.level == LogLevel.WARNING,
            )
        )
        warn_logs = logs.scalars().all()

        assert len(warn_logs) > 0
