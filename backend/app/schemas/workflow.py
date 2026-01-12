"""Pydantic schemas for Workflow, Node, and Edge models.

TAG: [SPEC-006] [SCHEMAS] [WORKFLOW] [NODE] [EDGE]
REQ: REQ-001 - Workflow Schema Definitions
REQ: REQ-002 - Node Schema Definitions
REQ: REQ-003 - Edge Schema Definitions
REQ: REQ-004 - Composite Schema Definitions

This module defines request/response schemas for workflow-related endpoints.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Required at runtime for Pydantic
from typing import Any, Self
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import Field, model_validator

from app.models.enums import NodeType
from app.schemas.base import (
    BaseResponse,
    BaseSchema,
    PaginatedResponse,
)

# =============================================================================
# Edge Schemas
# =============================================================================


class EdgeBase(BaseSchema):
    """Base schema for Edge with common fields."""

    source_node_id: UUID = Field(
        ...,
        description="UUID of the source node",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    target_node_id: UUID = Field(
        ...,
        description="UUID of the target node",
        examples=["550e8400-e29b-41d4-a716-446655440002"],
    )
    source_handle: str | None = Field(
        default=None,
        max_length=50,
        description="Handle identifier on source node (for multi-output nodes)",
        examples=["output_1", "success", "failure"],
    )
    target_handle: str | None = Field(
        default=None,
        max_length=50,
        description="Handle identifier on target node (for multi-input nodes)",
        examples=["input_1", "data"],
    )
    condition: dict[str, Any] | None = Field(
        default=None,
        description="Condition expression for conditional edges (JSON)",
        examples=[{"type": "expression", "value": "result.status == 'success'"}],
    )
    priority: int = Field(
        default=0,
        ge=0,
        description="Execution priority (higher = processed first)",
        examples=[0, 1, 10],
    )
    label: str | None = Field(
        default=None,
        max_length=100,
        description="Display label for the edge in the UI",
        examples=["on success", "default path"],
    )

    @model_validator(mode="after")
    def validate_no_self_loop(self) -> Self:
        """Ensure source and target nodes are different."""
        if self.source_node_id == self.target_node_id:
            raise ValueError(
                "Self-loops are not allowed: source and target must be different"
            )
        return self


class EdgeCreate(EdgeBase):
    """Schema for creating a new edge."""


class EdgeResponse(EdgeBase):
    """Schema for edge in API responses."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the edge",
        examples=["550e8400-e29b-41d4-a716-446655440003"],
    )
    workflow_id: UUID = Field(
        ...,
        description="UUID of the parent workflow",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the edge was created",
        examples=["2024-01-15T10:30:00Z"],
    )


# =============================================================================
# Node Schemas
# =============================================================================


class RetryConfig(BaseSchema):
    """Configuration for node retry behavior."""

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
        examples=[3],
    )
    delay: float = Field(
        default=1.0,
        ge=0.0,
        le=300.0,
        description="Delay between retries in seconds",
        examples=[1.0, 5.0],
    )
    backoff_multiplier: float = Field(
        default=1.0,
        ge=1.0,
        le=10.0,
        description="Multiplier for exponential backoff",
        examples=[1.0, 2.0],
    )


class NodeBase(BaseSchema):
    """Base schema for Node with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Node"],
    )
    node_type: NodeType = Field(
        ...,
        description="Type of the node (trigger, tool, agent, condition, adapter, parallel, aggregator)",
        examples=["trigger", "tool", "agent"],
    )
    position_x: float = Field(
        default=0.0,
        description="X coordinate for UI positioning",
        examples=[100.0, 250.5],
    )
    position_y: float = Field(
        default=0.0,
        description="Y coordinate for UI positioning",
        examples=[50.0, 175.5],
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration object (JSON)",
        examples=[{"timeout": 30, "retries": 3}],
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for validating node input",
        examples=[{"type": "object", "properties": {"data": {"type": "string"}}}],
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for validating node output",
        examples=[{"type": "object", "properties": {"result": {"type": "boolean"}}}],
    )
    tool_id: UUID | None = Field(
        default=None,
        description="UUID of the linked tool (required for tool nodes)",
        examples=["550e8400-e29b-41d4-a716-446655440004"],
    )
    agent_id: UUID | None = Field(
        default=None,
        description="UUID of the linked agent (required for agent nodes)",
        examples=["550e8400-e29b-41d4-a716-446655440005"],
    )
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Execution timeout in seconds (1-3600)",
        examples=[300, 600],
    )
    retry_config: RetryConfig = Field(
        default_factory=lambda: RetryConfig(),
        description="Retry configuration for failed executions",
    )

    @model_validator(mode="after")
    def validate_type_requirements(self) -> Self:
        """Validate that tool/agent nodes have the required IDs."""
        if self.node_type == NodeType.TOOL and self.tool_id is None:
            raise ValueError("tool_id is required for tool nodes")
        if self.node_type == NodeType.AGENT and self.agent_id is None:
            raise ValueError("agent_id is required for agent nodes")
        return self


class NodeCreate(NodeBase):
    """Schema for creating a new node."""


class NodeUpdate(BaseSchema):
    """Schema for updating an existing node.

    All fields are optional to support partial updates.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Node"],
    )
    position_x: float | None = Field(
        default=None,
        description="X coordinate for UI positioning",
    )
    position_y: float | None = Field(
        default=None,
        description="Y coordinate for UI positioning",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Configuration object (JSON)",
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for validating node input",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for validating node output",
    )
    tool_id: UUID | None = Field(
        default=None,
        description="UUID of the linked tool",
    )
    agent_id: UUID | None = Field(
        default=None,
        description="UUID of the linked agent",
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        le=3600,
        description="Execution timeout in seconds",
    )
    retry_config: RetryConfig | None = Field(
        default=None,
        description="Retry configuration",
    )


class NodeResponse(BaseResponse):
    """Schema for node in API responses."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the parent workflow",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    name: str = Field(
        ...,
        description="Display name of the node",
        examples=["Data Fetcher"],
    )
    node_type: NodeType = Field(
        ...,
        description="Type of the node",
        examples=["tool"],
    )
    position_x: float = Field(
        ...,
        description="X coordinate for UI positioning",
    )
    position_y: float = Field(
        ...,
        description="Y coordinate for UI positioning",
    )
    config: dict[str, Any] = Field(
        ...,
        description="Configuration object",
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for input validation",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for output validation",
    )
    tool_id: UUID | None = Field(
        default=None,
        description="UUID of the linked tool",
    )
    agent_id: UUID | None = Field(
        default=None,
        description="UUID of the linked agent",
    )
    timeout_seconds: int = Field(
        ...,
        description="Execution timeout in seconds",
    )
    retry_config: dict[str, Any] = Field(
        ...,
        description="Retry configuration",
    )


# =============================================================================
# Workflow Schemas
# =============================================================================


class WorkflowBase(BaseSchema):
    """Base schema for Workflow with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Workflow"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description",
        examples=["This workflow processes incoming data"],
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration object (JSON)",
        examples=[{"timeout": 30, "retries": 3}],
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow variables (JSON)",
        examples=[{"api_key": "{{secrets.API_KEY}}", "max_items": 100}],
    )
    is_active: bool = Field(
        default=True,
        description="Whether the workflow is active and can be executed",
        examples=[True],
    )


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow.

    Note: owner_id is not included here as it's automatically set
    by the API endpoint from the authenticated user (or TEMP_OWNER_ID
    until authentication is implemented).
    """


class WorkflowUpdate(BaseSchema):
    """Schema for updating an existing workflow.

    All fields are optional to support partial updates.
    Requires version for optimistic locking.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Workflow"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Configuration object (JSON)",
    )
    variables: dict[str, Any] | None = Field(
        default=None,
        description="Workflow variables (JSON)",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the workflow is active",
    )
    version: int = Field(
        ...,
        ge=1,
        description="Version number for optimistic locking",
        examples=[1],
    )


class WorkflowResponse(BaseResponse):
    """Schema for workflow in API responses."""

    owner_id: UUID = Field(
        ...,
        description="UUID of the workflow owner",
    )
    name: str = Field(
        ...,
        description="Display name of the workflow",
        examples=["Data Processing Pipeline"],
    )
    description: str | None = Field(
        default=None,
        description="Optional description",
    )
    config: dict[str, Any] = Field(
        ...,
        description="Workflow configuration",
    )
    variables: dict[str, Any] = Field(
        ...,
        description="Workflow variables",
    )
    is_active: bool = Field(
        ...,
        description="Whether the workflow is active",
    )
    version: int = Field(
        ...,
        description="Version number for optimistic locking",
    )


class WorkflowListResponse(WorkflowResponse):
    """Schema for workflow in list responses.

    Includes summary counts for nodes and edges.
    """

    node_count: int = Field(
        default=0,
        ge=0,
        description="Number of nodes in the workflow",
        examples=[5],
    )
    edge_count: int = Field(
        default=0,
        ge=0,
        description="Number of edges in the workflow",
        examples=[4],
    )


class WorkflowWithNodes(WorkflowResponse):
    """Schema for workflow with full node and edge details.

    Used for detailed workflow views and workflow editing.
    """

    nodes: list[NodeResponse] = Field(
        default_factory=list,
        description="List of nodes in the workflow",
    )
    edges: list[EdgeResponse] = Field(
        default_factory=list,
        description="List of edges connecting nodes",
    )


# =============================================================================
# Workflow Import/Export Schemas
# =============================================================================


class WorkflowExportData(BaseSchema):
    """Schema for exporting a workflow as portable data.

    Includes all nodes and edges without internal IDs.
    """

    name: str = Field(..., description="Workflow name")
    description: str | None = Field(default=None, description="Workflow description")
    config: dict[str, Any] = Field(..., description="Workflow configuration")
    variables: dict[str, Any] = Field(..., description="Workflow variables")
    nodes: list[dict[str, Any]] = Field(..., description="Node definitions")
    edges: list[dict[str, Any]] = Field(..., description="Edge definitions")
    version: str = Field(
        default="1.0",
        description="Export format version",
        examples=["1.0"],
    )


class WorkflowImport(BaseSchema):
    """Schema for importing a workflow from exported data."""

    workflow_data: WorkflowExportData = Field(
        ...,
        description="Exported workflow data to import",
    )
    owner_id: UUID = Field(
        ...,
        description="UUID of the user who will own the imported workflow",
    )
    name_prefix: str | None = Field(
        default=None,
        max_length=50,
        description="Optional prefix to add to workflow name",
        examples=["Imported-", "Copy of "],
    )


# =============================================================================
# Batch Operation Schemas
# =============================================================================


class NodeBatchCreate(BaseSchema):
    """Schema for creating multiple nodes at once."""

    nodes: list[NodeCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of nodes to create",
    )


class EdgeBatchCreate(BaseSchema):
    """Schema for creating multiple edges at once."""

    edges: list[EdgeCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of edges to create",
    )


class WorkflowGraphUpdate(BaseSchema):
    """Schema for updating the entire workflow graph.

    Used for bulk updates from the visual editor.
    Replaces all nodes and edges with the provided data.
    """

    version: int = Field(
        ...,
        ge=1,
        description="Version number for optimistic locking",
        examples=[1],
    )
    nodes: list[NodeCreate] = Field(
        default_factory=list,
        max_length=100,
        description="List of all nodes in the workflow",
    )
    edges: list[EdgeCreate] = Field(
        default_factory=list,
        max_length=200,
        description="List of all edges in the workflow",
    )


# =============================================================================
# Paginated Response Types
# =============================================================================


WorkflowPaginatedResponse = PaginatedResponse[WorkflowListResponse]
NodePaginatedResponse = PaginatedResponse[NodeResponse]
EdgePaginatedResponse = PaginatedResponse[EdgeResponse]


__all__ = [
    # Edge schemas
    "EdgeBase",
    "EdgeBatchCreate",
    "EdgeCreate",
    "EdgePaginatedResponse",
    "EdgeResponse",
    # Node schemas
    "NodeBase",
    "NodeBatchCreate",
    "NodeCreate",
    "NodePaginatedResponse",
    "NodeResponse",
    "NodeUpdate",
    # Workflow schemas
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowGraphUpdate",
    "WorkflowListResponse",
    "WorkflowPaginatedResponse",
    "WorkflowResponse",
    "WorkflowUpdate",
    "WorkflowWithNodes",
]
