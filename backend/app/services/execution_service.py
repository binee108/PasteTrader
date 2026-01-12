"""Execution services for workflow runs.

TAG: [SPEC-006] [SERVICES] [EXECUTION]
REQ: REQ-001 - WorkflowExecutionService Implementation
REQ: REQ-002 - NodeExecutionService Implementation
REQ: REQ-003 - ExecutionLogService Implementation

This module provides service classes for managing workflow executions,
node executions, and execution logs with proper state transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.enums import ExecutionStatus, LogLevel
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.schemas.execution import (
    ExecutionStatistics,
    WorkflowExecutionCreate,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class WorkflowExecutionService:
    """Service for managing WorkflowExecution records.

    Handles CRUD operations and state transitions for workflow executions.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        workflow_id: uuid.UUID,
        data: WorkflowExecutionCreate,
    ) -> WorkflowExecution:
        """Create a new workflow execution.

        Args:
            db: Database session.
            workflow_id: UUID of the workflow to execute.
            data: Workflow execution creation data.

        Returns:
            The created WorkflowExecution instance.
        """
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_type=data.trigger_type,
            status=ExecutionStatus.PENDING,
            input_data=data.input_data,
            context=data.context.model_dump() if data.context else {},
            metadata_=data.metadata_.model_dump() if data.metadata_ else {},
        )
        db.add(execution)
        await db.flush()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def get(
        db: AsyncSession,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        """Get a workflow execution by ID.

        Args:
            db: Database session.
            execution_id: UUID of the execution to retrieve.

        Returns:
            The WorkflowExecution if found, None otherwise.
        """
        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_with_nodes(
        db: AsyncSession,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution | None:
        """Get a workflow execution with node executions eagerly loaded.

        Args:
            db: Database session.
            execution_id: UUID of the execution to retrieve.

        Returns:
            The WorkflowExecution with node_executions loaded if found,
            None otherwise.
        """
        result = await db.execute(
            select(WorkflowExecution)
            .where(WorkflowExecution.id == execution_id)
            .options(selectinload(WorkflowExecution.node_executions))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        workflow_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        status: ExecutionStatus | None = None,
    ) -> list[WorkflowExecution]:
        """List workflow executions for a workflow.

        Args:
            db: Database session.
            workflow_id: UUID of the workflow.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            status: Optional status filter.

        Returns:
            List of WorkflowExecution records.
        """
        query = select(WorkflowExecution).where(
            WorkflowExecution.workflow_id == workflow_id
        )

        if status is not None:
            query = query.where(WorkflowExecution.status == status)

        query = query.order_by(WorkflowExecution.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count(
        db: AsyncSession,
        workflow_id: uuid.UUID,
        status: ExecutionStatus | None = None,
    ) -> int:
        """Count workflow executions for a workflow.

        Args:
            db: Database session.
            workflow_id: UUID of the workflow.
            status: Optional status filter.

        Returns:
            Count of matching executions.
        """
        query = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.workflow_id == workflow_id
        )

        if status is not None:
            query = query.where(WorkflowExecution.status == status)

        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def start(
        db: AsyncSession,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution:
        """Start a workflow execution (transition to RUNNING).

        Args:
            db: Database session.
            execution_id: UUID of the execution to start.

        Returns:
            The updated WorkflowExecution.

        Raises:
            ValueError: If execution not found or not in PENDING state.
        """
        execution = await WorkflowExecutionService.get(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        execution.start()
        await db.flush()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def complete(
        db: AsyncSession,
        execution_id: uuid.UUID,
        output_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Complete a workflow execution (transition to COMPLETED).

        Args:
            db: Database session.
            execution_id: UUID of the execution to complete.
            output_data: Optional output data from the workflow.

        Returns:
            The updated WorkflowExecution.

        Raises:
            ValueError: If execution not found or not in RUNNING state.
        """
        execution = await WorkflowExecutionService.get(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        execution.complete(output_data)
        await db.flush()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def fail(
        db: AsyncSession,
        execution_id: uuid.UUID,
        error_message: str,
    ) -> WorkflowExecution:
        """Fail a workflow execution (transition to FAILED).

        Args:
            db: Database session.
            execution_id: UUID of the execution to fail.
            error_message: Description of the failure.

        Returns:
            The updated WorkflowExecution.

        Raises:
            ValueError: If execution not found or not in RUNNING state.
        """
        execution = await WorkflowExecutionService.get(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        execution.fail(error_message)
        await db.flush()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def cancel(
        db: AsyncSession,
        execution_id: uuid.UUID,
    ) -> WorkflowExecution:
        """Cancel a workflow execution (transition to CANCELLED).

        Args:
            db: Database session.
            execution_id: UUID of the execution to cancel.

        Returns:
            The updated WorkflowExecution.

        Raises:
            ValueError: If execution not found or not in PENDING/RUNNING state.
        """
        execution = await WorkflowExecutionService.get(db, execution_id)
        if execution is None:
            raise ValueError(f"Execution {execution_id} not found")

        execution.cancel()
        await db.flush()
        await db.refresh(execution)
        return execution

    @staticmethod
    async def get_statistics(
        db: AsyncSession,
        workflow_id: uuid.UUID,
    ) -> ExecutionStatistics:
        """Get execution statistics for a workflow.

        Args:
            db: Database session.
            workflow_id: UUID of the workflow.

        Returns:
            ExecutionStatistics with counts and metrics.
        """
        # Count by status
        status_counts = {}
        for status in ExecutionStatus:
            count = await WorkflowExecutionService.count(db, workflow_id, status)
            status_counts[status.value] = count

        total = sum(status_counts.values())
        completed = status_counts.get(ExecutionStatus.COMPLETED.value, 0)
        failed = status_counts.get(ExecutionStatus.FAILED.value, 0)
        running = status_counts.get(ExecutionStatus.RUNNING.value, 0)
        pending = status_counts.get(ExecutionStatus.PENDING.value, 0)
        cancelled = status_counts.get(ExecutionStatus.CANCELLED.value, 0)

        # Calculate average duration for completed executions
        avg_duration_query = select(
            func.avg(
                func.extract(
                    "epoch",
                    WorkflowExecution.ended_at - WorkflowExecution.started_at,
                )
            )
        ).where(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.status == ExecutionStatus.COMPLETED,
            WorkflowExecution.started_at.isnot(None),
            WorkflowExecution.ended_at.isnot(None),
        )
        avg_result = await db.execute(avg_duration_query)
        avg_duration = avg_result.scalar_one_or_none()

        # Calculate success rate
        terminal_count = completed + failed + cancelled
        success_rate = completed / terminal_count if terminal_count > 0 else 0.0

        # Handle negative or null duration values
        avg_duration_seconds = None
        if avg_duration is not None and avg_duration >= 0:
            avg_duration_seconds = float(avg_duration)

        return ExecutionStatistics(
            total_executions=total,
            completed=completed,
            failed=failed,
            running=running,
            pending=pending,
            cancelled=cancelled,
            avg_duration_seconds=avg_duration_seconds,
            success_rate=success_rate,
        )


class NodeExecutionService:
    """Service for managing NodeExecution records.

    Handles CRUD operations and state transitions for node executions.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        workflow_execution_id: uuid.UUID,
        node_id: uuid.UUID,
        execution_order: int,
    ) -> NodeExecution:
        """Create a new node execution record.

        Args:
            db: Database session.
            workflow_execution_id: UUID of the parent workflow execution.
            node_id: UUID of the node being executed.
            execution_order: Order of this node in the execution sequence.

        Returns:
            The created NodeExecution instance.
        """
        node_execution = NodeExecution(
            workflow_execution_id=workflow_execution_id,
            node_id=node_id,
            execution_order=execution_order,
            status=ExecutionStatus.PENDING,
            input_data={},
            retry_count=0,
        )
        db.add(node_execution)
        await db.flush()
        await db.refresh(node_execution)
        return node_execution

    @staticmethod
    async def get(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
    ) -> NodeExecution | None:
        """Get a node execution by ID.

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution to retrieve.

        Returns:
            The NodeExecution if found, None otherwise.
        """
        result = await db.execute(
            select(NodeExecution).where(NodeExecution.id == node_execution_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_execution(
        db: AsyncSession,
        workflow_execution_id: uuid.UUID,
    ) -> list[NodeExecution]:
        """List all node executions for a workflow execution.

        Args:
            db: Database session.
            workflow_execution_id: UUID of the parent workflow execution.

        Returns:
            List of NodeExecution records ordered by execution_order.
        """
        result = await db.execute(
            select(NodeExecution)
            .where(NodeExecution.workflow_execution_id == workflow_execution_id)
            .order_by(NodeExecution.execution_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def start(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
        input_data: dict[str, Any] | None = None,
    ) -> NodeExecution:
        """Start a node execution (transition to RUNNING).

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution to start.
            input_data: Optional input data for the node.

        Returns:
            The updated NodeExecution.

        Raises:
            ValueError: If node execution not found or not in PENDING state.
        """
        node_execution = await NodeExecutionService.get(db, node_execution_id)
        if node_execution is None:
            raise ValueError(f"NodeExecution {node_execution_id} not found")

        if node_execution.status != ExecutionStatus.PENDING:
            raise ValueError(
                f"Cannot start node execution in {node_execution.status} state"
            )

        node_execution.status = ExecutionStatus.RUNNING
        node_execution.started_at = datetime.now(UTC)
        if input_data is not None:
            node_execution.input_data = input_data

        await db.flush()
        await db.refresh(node_execution)
        return node_execution

    @staticmethod
    async def complete(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
        output_data: dict[str, Any] | None = None,
    ) -> NodeExecution:
        """Complete a node execution (transition to COMPLETED).

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution to complete.
            output_data: Optional output data from the node.

        Returns:
            The updated NodeExecution.

        Raises:
            ValueError: If node execution not found or not in RUNNING state.
        """
        node_execution = await NodeExecutionService.get(db, node_execution_id)
        if node_execution is None:
            raise ValueError(f"NodeExecution {node_execution_id} not found")

        if node_execution.status != ExecutionStatus.RUNNING:
            raise ValueError(
                f"Cannot complete node execution in {node_execution.status} state"
            )

        node_execution.status = ExecutionStatus.COMPLETED
        node_execution.ended_at = datetime.now(UTC)
        if output_data is not None:
            node_execution.output_data = output_data

        await db.flush()
        await db.refresh(node_execution)
        return node_execution

    @staticmethod
    async def fail(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
        error_message: str,
        traceback: str | None = None,
    ) -> NodeExecution:
        """Fail a node execution (transition to FAILED).

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution to fail.
            error_message: Description of the failure.
            traceback: Optional full traceback.

        Returns:
            The updated NodeExecution.

        Raises:
            ValueError: If node execution not found or not in RUNNING state.
        """
        node_execution = await NodeExecutionService.get(db, node_execution_id)
        if node_execution is None:
            raise ValueError(f"NodeExecution {node_execution_id} not found")

        if node_execution.status != ExecutionStatus.RUNNING:
            raise ValueError(
                f"Cannot fail node execution in {node_execution.status} state"
            )

        node_execution.status = ExecutionStatus.FAILED
        node_execution.ended_at = datetime.now(UTC)
        node_execution.error_message = error_message
        if traceback is not None:
            node_execution.error_traceback = traceback

        await db.flush()
        await db.refresh(node_execution)
        return node_execution

    @staticmethod
    async def skip(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
    ) -> NodeExecution:
        """Skip a node execution (transition to SKIPPED).

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution to skip.

        Returns:
            The updated NodeExecution.

        Raises:
            ValueError: If node execution not found or not in PENDING state.
        """
        node_execution = await NodeExecutionService.get(db, node_execution_id)
        if node_execution is None:
            raise ValueError(f"NodeExecution {node_execution_id} not found")

        if node_execution.status != ExecutionStatus.PENDING:
            raise ValueError(
                f"Cannot skip node execution in {node_execution.status} state"
            )

        node_execution.status = ExecutionStatus.SKIPPED
        node_execution.ended_at = datetime.now(UTC)

        await db.flush()
        await db.refresh(node_execution)
        return node_execution

    @staticmethod
    async def increment_retry(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
    ) -> NodeExecution:
        """Increment the retry count for a node execution.

        Resets the node execution to PENDING state for retry.

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution.

        Returns:
            The updated NodeExecution.

        Raises:
            ValueError: If node execution not found or not in FAILED state.
        """
        node_execution = await NodeExecutionService.get(db, node_execution_id)
        if node_execution is None:
            raise ValueError(f"NodeExecution {node_execution_id} not found")

        if node_execution.status != ExecutionStatus.FAILED:
            raise ValueError(
                f"Cannot retry node execution in {node_execution.status} state"
            )

        node_execution.retry_count += 1
        node_execution.status = ExecutionStatus.PENDING
        node_execution.started_at = None
        node_execution.ended_at = None
        node_execution.error_message = None
        node_execution.error_traceback = None

        await db.flush()
        await db.refresh(node_execution)
        return node_execution


class ExecutionLogService:
    """Service for managing ExecutionLog records.

    Handles creation and retrieval of execution log entries.
    """

    @staticmethod
    async def create(
        db: AsyncSession,
        workflow_execution_id: uuid.UUID,
        node_execution_id: uuid.UUID | None,
        level: LogLevel,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> ExecutionLog:
        """Create a new execution log entry.

        Args:
            db: Database session.
            workflow_execution_id: UUID of the parent workflow execution.
            node_execution_id: Optional UUID of the related node execution.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            message: Log message text.
            data: Optional additional structured log data.

        Returns:
            The created ExecutionLog instance.
        """
        log = ExecutionLog(
            workflow_execution_id=workflow_execution_id,
            node_execution_id=node_execution_id,
            level=level,
            message=message,
            data=data,
            timestamp=datetime.now(UTC),
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    @staticmethod
    async def list_by_execution(
        db: AsyncSession,
        workflow_execution_id: uuid.UUID,
        level: LogLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExecutionLog]:
        """List execution logs for a workflow execution.

        Args:
            db: Database session.
            workflow_execution_id: UUID of the workflow execution.
            level: Optional log level filter.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of ExecutionLog records ordered by timestamp.
        """
        query = select(ExecutionLog).where(
            ExecutionLog.workflow_execution_id == workflow_execution_id
        )

        if level is not None:
            query = query.where(ExecutionLog.level == level)

        query = query.order_by(ExecutionLog.timestamp)
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def list_by_node(
        db: AsyncSession,
        node_execution_id: uuid.UUID,
        level: LogLevel | None = None,
    ) -> list[ExecutionLog]:
        """List execution logs for a specific node execution.

        Args:
            db: Database session.
            node_execution_id: UUID of the node execution.
            level: Optional log level filter.

        Returns:
            List of ExecutionLog records ordered by timestamp.
        """
        query = select(ExecutionLog).where(
            ExecutionLog.node_execution_id == node_execution_id
        )

        if level is not None:
            query = query.where(ExecutionLog.level == level)

        query = query.order_by(ExecutionLog.timestamp)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count(
        db: AsyncSession,
        workflow_execution_id: uuid.UUID,
        level: LogLevel | None = None,
    ) -> int:
        """Count execution logs for a workflow execution.

        Args:
            db: Database session.
            workflow_execution_id: UUID of the workflow execution.
            level: Optional log level filter.

        Returns:
            Count of matching log entries.
        """
        query = select(func.count(ExecutionLog.id)).where(
            ExecutionLog.workflow_execution_id == workflow_execution_id
        )

        if level is not None:
            query = query.where(ExecutionLog.level == level)

        result = await db.execute(query)
        return result.scalar_one()


__all__ = [
    "ExecutionLogService",
    "NodeExecutionService",
    "WorkflowExecutionService",
]
