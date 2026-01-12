"""Execution tracking models for workflow runs.

TAG: [SPEC-005] [DATABASE] [EXECUTION] [TRACKING]
REQ: REQ-001 - WorkflowExecution Model Definition
REQ: REQ-002 - NodeExecution Model Definition
REQ: REQ-003 - ExecutionLog Model Definition
REQ: REQ-004 - Workflow-WorkflowExecution Relationship
REQ: REQ-005 - WorkflowExecution-NodeExecution Relationship (CASCADE)
REQ: REQ-006 - WorkflowExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-007 - NodeExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-008 - State Transition Helpers
REQ: REQ-009 - Duration Properties

This module defines execution tracking models for PasteTrader's workflow engine.
These models track workflow execution state, node execution details, and execution logs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ExecutionStatus, LogLevel, TriggerType

if TYPE_CHECKING:
    from app.models.workflow import Node, Workflow

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class WorkflowExecution(UUIDMixin, TimestampMixin, Base):
    """WorkflowExecution model for tracking workflow runs.

    Represents a single execution instance of a workflow.
    Tracks execution state, timing, input/output data, and errors.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_id: UUID of the parent workflow
        trigger_type: How this execution was triggered (SCHEDULE, EVENT, MANUAL)
        status: Current execution status (PENDING, RUNNING, COMPLETED, etc.)
        started_at: When execution started (nullable)
        ended_at: When execution ended (nullable)
        input_data: JSONB input data for the workflow
        output_data: JSONB output data from the workflow (nullable)
        error_message: Error message if execution failed (nullable)
        context: JSONB execution context (variables, secrets, environment)
        metadata_: JSONB metadata (triggered_by, priority, tags, etc.)
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        workflow: Relationship to parent Workflow
        node_executions: Relationship to NodeExecution records
        logs: Relationship to ExecutionLog records
    """

    __tablename__ = "workflow_executions"

    # Foreign key to workflows table
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    # Trigger type
    trigger_type: Mapped[TriggerType] = mapped_column(
        String(50),
        nullable=False,
    )

    # Execution status with default
    status: Mapped[ExecutionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default="pending",
    )

    # Timing fields
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Data fields
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Context and metadata
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(
        "Workflow",
        back_populates="executions",
    )

    node_executions: Mapped[list[NodeExecution]] = relationship(
        "NodeExecution",
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="NodeExecution.execution_order",
    )

    logs: Mapped[list[ExecutionLog]] = relationship(
        "ExecutionLog",
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExecutionLog.timestamp",
        foreign_keys="ExecutionLog.workflow_execution_id",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds.

        Returns:
            Duration in seconds if both started_at and ended_at are set,
            None otherwise.
        """
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state.

        Returns:
            True if execution is in COMPLETED, FAILED, SKIPPED, or CANCELLED state.
        """
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.CANCELLED,
        )

    def start(self) -> None:
        """Mark execution as running.

        Sets status to RUNNING and records started_at timestamp.

        Raises:
            ValueError: If execution is not in PENDING state.
        """
        if self.status != ExecutionStatus.PENDING:
            raise ValueError(f"Cannot start execution in {self.status} state")
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self, output_data: dict[str, Any] | None = None) -> None:
        """Mark execution as completed.

        Sets status to COMPLETED, records ended_at timestamp,
        and optionally stores output data.

        Args:
            output_data: Optional output data from the workflow execution.

        Raises:
            ValueError: If execution is not in RUNNING state.
        """
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Cannot complete execution in {self.status} state")
        self.status = ExecutionStatus.COMPLETED
        self.ended_at = datetime.now(UTC)
        if output_data is not None:
            self.output_data = output_data

    def fail(self, error_message: str) -> None:
        """Mark execution as failed.

        Sets status to FAILED, records ended_at timestamp,
        and stores the error message.

        Args:
            error_message: Description of what caused the failure.

        Raises:
            ValueError: If execution is not in RUNNING state.
        """
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Cannot fail execution in {self.status} state")
        self.status = ExecutionStatus.FAILED
        self.ended_at = datetime.now(UTC)
        self.error_message = error_message

    def cancel(self) -> None:
        """Cancel the execution.

        Sets status to CANCELLED and records ended_at timestamp.

        Raises:
            ValueError: If execution is not in PENDING or RUNNING state.
        """
        if self.status not in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
            raise ValueError(f"Cannot cancel execution in {self.status} state")
        self.status = ExecutionStatus.CANCELLED
        self.ended_at = datetime.now(UTC)

    def __repr__(self) -> str:
        """Return string representation of the workflow execution."""
        return (
            f"<WorkflowExecution(id={self.id}, "
            f"workflow_id={self.workflow_id}, "
            f"status={self.status})>"
        )


class NodeExecution(UUIDMixin, TimestampMixin, Base):
    """NodeExecution model for tracking individual node runs within a workflow.

    Represents a single execution instance of a node within a workflow execution.
    Tracks execution state, timing, input/output data, errors, and retry information.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_execution_id: UUID of the parent workflow execution
        node_id: UUID of the node being executed
        status: Current execution status (PENDING, RUNNING, COMPLETED, etc.)
        started_at: When node execution started (nullable)
        ended_at: When node execution ended (nullable)
        input_data: JSONB input data for the node
        output_data: JSONB output data from the node (nullable)
        error_message: Error message if node failed (nullable)
        error_traceback: Full traceback if node failed (nullable)
        retry_count: Number of times this node has been retried
        execution_order: Order in which this node was executed
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        workflow_execution: Relationship to parent WorkflowExecution
        node: Relationship to the Node being executed
        logs: Relationship to ExecutionLog records
    """

    __tablename__ = "node_executions"

    # Foreign key to workflow_executions table with CASCADE delete
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to nodes table
    node_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("nodes.id"),
        nullable=False,
        index=True,
    )

    # Execution status with default
    status: Mapped[ExecutionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default="pending",
    )

    # Timing fields
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Data fields
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Error fields
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_traceback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Retry and ordering
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    execution_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Relationships
    workflow_execution: Mapped[WorkflowExecution] = relationship(
        "WorkflowExecution",
        back_populates="node_executions",
    )

    node: Mapped[Node] = relationship("Node")

    logs: Mapped[list[ExecutionLog]] = relationship(
        "ExecutionLog",
        back_populates="node_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExecutionLog.timestamp",
        foreign_keys="ExecutionLog.node_execution_id",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate node execution duration in seconds.

        Returns:
            Duration in seconds if both started_at and ended_at are set,
            None otherwise.
        """
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Check if node execution can be retried.

        Returns:
            True if node is in FAILED state and retry_count is less than
            max_retries configured for the node.
        """
        if self.status != ExecutionStatus.FAILED:
            return False

        # Get max_retries from node's retry_config, default to 3
        max_retries = 3
        if self.node and self.node.retry_config:
            max_retries = self.node.retry_config.get("max_retries", 3)

        return self.retry_count < max_retries

    def __repr__(self) -> str:
        """Return string representation of the node execution."""
        return (
            f"<NodeExecution(id={self.id}, "
            f"node_id={self.node_id}, "
            f"status={self.status})>"
        )


class ExecutionLog(UUIDMixin, Base):
    """ExecutionLog model for storing execution log entries.

    Represents a log entry generated during workflow or node execution.
    Can be associated with a workflow execution and optionally a specific node execution.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_execution_id: UUID of the parent workflow execution
        node_execution_id: UUID of the node execution (nullable, for node-level logs)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        message: Log message text
        data: JSONB additional log data (nullable)
        timestamp: When the log was created
        workflow_execution: Relationship to parent WorkflowExecution
        node_execution: Relationship to NodeExecution (nullable)
    """

    __tablename__ = "execution_logs"

    # Foreign key to workflow_executions table with CASCADE delete
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to node_executions table with CASCADE delete (nullable)
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("node_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Log level
    level: Mapped[LogLevel] = mapped_column(
        String(20),
        nullable=False,
    )

    # Log message
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Additional log data
    data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    workflow_execution: Mapped[WorkflowExecution] = relationship(
        "WorkflowExecution",
        back_populates="logs",
        foreign_keys=[workflow_execution_id],
    )

    node_execution: Mapped[NodeExecution | None] = relationship(
        "NodeExecution",
        back_populates="logs",
        foreign_keys=[node_execution_id],
    )

    def __repr__(self) -> str:
        """Return string representation of the execution log."""
        return (
            f"<ExecutionLog(id={self.id}, "
            f"level={self.level}, "
            f"message='{self.message[:50]}...')>"
        )


__all__ = ["ExecutionLog", "NodeExecution", "WorkflowExecution"]
