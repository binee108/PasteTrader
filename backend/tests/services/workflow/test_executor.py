"""Tests for WorkflowExecutor core functionality.

TAG: [SPEC-011] [EXECUTION] [EXECUTOR] [TEST]
REQ: REQ-011-001 - DAG topological sort based execution
REQ: REQ-011-002 - asyncio.TaskGroup parallel execution
"""

import pytest

from app.models.enums import ExecutionStatus, TriggerType
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
    async def test_execute_returns_result(
        self, db_session, workflow_factory
    ) -> None:
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
            select(WorkflowExecution).where(
                WorkflowExecution.id == result.execution_id
            )
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
