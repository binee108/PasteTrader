"""Pydantic schemas for execution tracking models.

TAG: [SPEC-007] [SCHEMAS] [EXECUTION]
REQ: REQ-001 - WorkflowExecution Schema Definitions
REQ: REQ-002 - NodeExecution Schema Definitions
REQ: REQ-003 - ExecutionLog Schema Definitions

This module defines request/response schemas for execution tracking endpoints.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Required at runtime for Pydantic
from typing import Any
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import Field, computed_field, field_validator

from app.models.enums import ExecutionStatus, LogLevel, TriggerType
from app.schemas.base import BaseResponse, BaseSchema, PaginatedResponse

# =============================================================================
# ExecutionLog Schemas
# =============================================================================


class ExecutionLogBase(BaseSchema):
    """Base schema for ExecutionLog."""

    level: LogLevel = Field(
        ...,
        description="Log level (debug, info, warning, error)",
        examples=["info", "error"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Log message text",
        examples=["Node execution started", "Failed to fetch data from API"],
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Additional structured log data (JSON)",
        examples=[{"url": "https://api.example.com", "status_code": 500}],
    )


class ExecutionLogCreate(ExecutionLogBase):
    """Schema for creating a new execution log entry."""

    workflow_execution_id: UUID = Field(
        ...,
        description="UUID of the parent workflow execution",
    )
    node_execution_id: UUID | None = Field(
        default=None,
        description="UUID of the related node execution (optional)",
    )


class ExecutionLogResponse(BaseSchema):
    """Schema for execution log in API responses."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the log entry",
    )
    workflow_execution_id: UUID = Field(
        ...,
        description="UUID of the parent workflow execution",
    )
    node_execution_id: UUID | None = Field(
        default=None,
        description="UUID of the related node execution",
    )
    level: LogLevel = Field(
        ...,
        description="Log level",
    )
    message: str = Field(
        ...,
        description="Log message text",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Additional structured log data",
    )
    timestamp: datetime = Field(
        ...,
        description="Timestamp when the log was created",
        examples=["2024-01-15T10:30:00Z"],
    )


# =============================================================================
# NodeExecution Schemas
# =============================================================================


class NodeExecutionBase(BaseSchema):
    """Base schema for NodeExecution."""

    node_id: UUID = Field(
        ...,
        description="UUID of the node being executed",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for the node execution (JSON)",
        examples=[{"query": "SELECT * FROM users", "limit": 100}],
    )
    execution_order: int = Field(
        ...,
        ge=0,
        description="Order in which this node was executed within the workflow",
        examples=[0, 1, 2],
    )


class NodeExecutionCreate(NodeExecutionBase):
    """Schema for creating a new node execution record."""

    workflow_execution_id: UUID = Field(
        ...,
        description="UUID of the parent workflow execution",
    )


class NodeExecutionUpdate(BaseSchema):
    """Schema for updating a node execution.

    Used to update status, output, and error information during execution.
    """

    status: ExecutionStatus | None = Field(
        default=None,
        description="Updated execution status",
    )
    output_data: dict[str, Any] | None = Field(
        default=None,
        description="Output data from the node execution",
    )
    error_message: str | None = Field(
        default=None,
        max_length=5000,
        description="Error message if execution failed",
    )
    error_traceback: str | None = Field(
        default=None,
        max_length=50000,
        description="Full traceback if execution failed",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When node execution started",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="When node execution ended",
    )


class NodeExecutionResponse(BaseResponse):
    """Schema for node execution in API responses."""

    workflow_execution_id: UUID = Field(
        ...,
        description="UUID of the parent workflow execution",
    )
    node_id: UUID = Field(
        ...,
        description="UUID of the node being executed",
    )
    status: ExecutionStatus = Field(
        ...,
        description="Current execution status",
        examples=["completed", "failed"],
    )
    started_at: datetime | None = Field(
        default=None,
        description="When node execution started",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="When node execution ended",
    )
    input_data: dict[str, Any] = Field(
        ...,
        description="Input data for the node execution",
    )
    output_data: dict[str, Any] | None = Field(
        default=None,
        description="Output data from the node execution",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )
    error_traceback: str | None = Field(
        default=None,
        description="Full traceback if execution failed",
    )
    retry_count: int = Field(
        ...,
        ge=0,
        description="Number of times this node has been retried",
        examples=[0, 1, 2],
    )
    execution_order: int = Field(
        ...,
        ge=0,
        description="Order in which this node was executed",
    )

    @computed_field
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None


class NodeExecutionWithLogs(NodeExecutionResponse):
    """Schema for node execution with embedded log entries."""

    logs: list[ExecutionLogResponse] = Field(
        default_factory=list,
        description="Log entries for this node execution",
    )


# =============================================================================
# WorkflowExecution Schemas
# =============================================================================


class ExecutionContext(BaseSchema):
    """Schema for workflow execution context."""

    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime variables available during execution",
        examples=[{"user_id": "12345", "environment": "production"}],
    )
    secrets: dict[str, str] = Field(
        default_factory=dict,
        description="Secret references (values are resolved at runtime)",
        examples=[{"API_KEY": "{{vault:api_key}}"}],
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for execution",
        examples=[{"LOG_LEVEL": "debug"}],
    )


class ExecutionMetadata(BaseSchema):
    """Schema for workflow execution metadata."""

    triggered_by: str | None = Field(
        default=None,
        max_length=255,
        description="Identifier of who/what triggered this execution",
        examples=["user:john@example.com", "schedule:daily-job", "event:webhook"],
    )
    priority: int = Field(
        default=0,
        ge=-100,
        le=100,
        description="Execution priority (-100 to 100, higher = more priority)",
        examples=[0, 10, -10],
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Tags for categorizing and filtering executions",
        examples=[["production", "high-priority", "customer-request"]],
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=255,
        description="External correlation ID for tracing across systems",
        examples=["req-abc123", "trace-xyz789"],
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate that each tag has reasonable length."""
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Each tag must be 50 characters or less")
        return v


class WorkflowExecutionBase(BaseSchema):
    """Base schema for WorkflowExecution."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the workflow to execute",
    )
    trigger_type: TriggerType = Field(
        ...,
        description="How this execution was triggered (schedule, event, manual)",
        examples=["manual", "schedule", "event"],
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data for the workflow execution (JSON)",
        examples=[{"user_id": 123, "action": "process_order"}],
    )
    context: ExecutionContext = Field(
        default_factory=ExecutionContext,
        description="Execution context (variables, secrets, environment)",
    )
    metadata_: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        alias="metadata",
        description="Execution metadata (triggered_by, priority, tags)",
    )


class WorkflowExecutionCreate(WorkflowExecutionBase):
    """Schema for creating a new workflow execution."""


class WorkflowExecutionResponse(BaseResponse):
    """Schema for workflow execution in API responses."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the workflow being executed",
    )
    trigger_type: TriggerType = Field(
        ...,
        description="How this execution was triggered",
    )
    status: ExecutionStatus = Field(
        ...,
        description="Current execution status",
        examples=["running", "completed", "failed"],
    )
    started_at: datetime | None = Field(
        default=None,
        description="When execution started",
    )
    ended_at: datetime | None = Field(
        default=None,
        description="When execution ended",
    )
    input_data: dict[str, Any] = Field(
        ...,
        description="Input data for the workflow execution",
    )
    output_data: dict[str, Any] | None = Field(
        default=None,
        description="Output data from the workflow execution",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context (variables, secrets, environment)",
    )
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (triggered_by, priority, tags)",
    )

    @computed_field
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @computed_field
    def is_terminal(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.CANCELLED,
        )

    @property
    def metadata(self) -> dict[str, Any]:
        """Expose metadata_ as metadata for API compatibility."""
        return self.metadata_


class WorkflowExecutionListResponse(BaseSchema):
    """Schema for workflow execution in list responses.

    Includes summary information without full data fields.
    """

    id: UUID = Field(..., description="Unique identifier")
    workflow_id: UUID = Field(..., description="UUID of the workflow")
    workflow_name: str | None = Field(
        default=None,
        description="Name of the workflow (denormalized for convenience)",
    )
    trigger_type: TriggerType = Field(..., description="How execution was triggered")
    status: ExecutionStatus = Field(..., description="Current execution status")
    started_at: datetime | None = Field(default=None, description="When started")
    ended_at: datetime | None = Field(default=None, description="When ended")
    created_at: datetime = Field(..., description="When created")
    node_count: int = Field(
        default=0,
        ge=0,
        description="Number of node executions",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if failed (truncated)",
    )

    @computed_field
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None


class WorkflowExecutionWithNodes(WorkflowExecutionResponse):
    """Schema for workflow execution with embedded node executions."""

    node_executions: list[NodeExecutionResponse] = Field(
        default_factory=list,
        description="List of node execution records",
    )


class WorkflowExecutionDetail(WorkflowExecutionWithNodes):
    """Schema for detailed workflow execution view.

    Includes node executions with their logs.
    """

    node_executions: list[NodeExecutionWithLogs] = Field(  # type: ignore[assignment]
        default_factory=list,
        description="List of node executions with their logs",
    )
    logs: list[ExecutionLogResponse] = Field(
        default_factory=list,
        description="Workflow-level log entries",
    )


# =============================================================================
# Execution Control Schemas
# =============================================================================


class ExecutionCancel(BaseSchema):
    """Schema for cancelling an execution."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional reason for cancellation",
        examples=["User requested stop", "Timeout exceeded"],
    )


class ExecutionRetry(BaseSchema):
    """Schema for retrying a failed node execution."""

    node_execution_id: UUID = Field(
        ...,
        description="UUID of the failed node execution to retry",
    )
    reset_retry_count: bool = Field(
        default=False,
        description="Whether to reset the retry counter",
    )


class ExecutionResume(BaseSchema):
    """Schema for resuming a paused or failed execution."""

    from_node_id: UUID | None = Field(
        default=None,
        description="Optional node ID to resume from (defaults to failed node)",
    )
    input_override: dict[str, Any] | None = Field(
        default=None,
        description="Optional input data override for resumed execution",
    )


# =============================================================================
# Execution Statistics Schemas
# =============================================================================


class ExecutionStatistics(BaseSchema):
    """Schema for execution statistics summary."""

    total_executions: int = Field(
        ...,
        ge=0,
        description="Total number of executions",
    )
    completed: int = Field(
        ...,
        ge=0,
        description="Number of completed executions",
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Number of failed executions",
    )
    running: int = Field(
        ...,
        ge=0,
        description="Number of currently running executions",
    )
    pending: int = Field(
        ...,
        ge=0,
        description="Number of pending executions",
    )
    cancelled: int = Field(
        ...,
        ge=0,
        description="Number of cancelled executions",
    )
    avg_duration_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Average execution duration in seconds",
    )
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of completed executions (0.0 to 1.0)",
    )


class WorkflowExecutionStatistics(ExecutionStatistics):
    """Schema for workflow-specific execution statistics."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the workflow",
    )
    workflow_name: str = Field(
        ...,
        description="Name of the workflow",
    )
    last_execution_at: datetime | None = Field(
        default=None,
        description="Timestamp of the last execution",
    )


# =============================================================================
# Paginated Response Types
# =============================================================================


WorkflowExecutionPaginatedResponse = PaginatedResponse[WorkflowExecutionListResponse]
NodeExecutionPaginatedResponse = PaginatedResponse[NodeExecutionResponse]
ExecutionLogPaginatedResponse = PaginatedResponse[ExecutionLogResponse]


__all__ = [
    # Control schemas
    "ExecutionCancel",
    # WorkflowExecution schemas
    "ExecutionContext",
    # ExecutionLog schemas
    "ExecutionLogBase",
    "ExecutionLogCreate",
    "ExecutionLogPaginatedResponse",
    "ExecutionLogResponse",
    "ExecutionMetadata",
    "ExecutionResume",
    "ExecutionRetry",
    # Statistics schemas
    "ExecutionStatistics",
    # NodeExecution schemas
    "NodeExecutionBase",
    "NodeExecutionCreate",
    "NodeExecutionPaginatedResponse",
    "NodeExecutionResponse",
    "NodeExecutionUpdate",
    "NodeExecutionWithLogs",
    "WorkflowExecutionBase",
    "WorkflowExecutionCreate",
    "WorkflowExecutionDetail",
    "WorkflowExecutionListResponse",
    "WorkflowExecutionPaginatedResponse",
    "WorkflowExecutionResponse",
    "WorkflowExecutionStatistics",
    "WorkflowExecutionWithNodes",
]
