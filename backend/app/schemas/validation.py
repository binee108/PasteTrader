"""Pydantic schemas for DAG validation operations.

TAG: [SPEC-010] [SCHEMAS] [VALIDATION]
REQ: REQ-010-C - Validation Schemas

This module defines request/response schemas for workflow DAG validation.
All validation results use consistent error codes and detailed messages.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema

if TYPE_CHECKING:
    pass

# =============================================================================
# Validation Enums
# =============================================================================


class ValidationLevel(str, Enum):
    """Validation strictness level.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    MINIMAL: Only cycle detection (fastest)
    STANDARD: Structural + connectivity validation (default)
    STRICT: All validations including schema compatibility
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


class ValidationErrorCode(str, Enum):
    """Validation error codes.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Standardized error codes for all validation failures.
    """

    # Structural errors
    CYCLE_DETECTED = "CYCLE_DETECTED"
    SELF_LOOP_DETECTED = "SELF_LOOP_DETECTED"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    DUPLICATE_EDGE = "DUPLICATE_EDGE"

    # Connectivity errors
    NO_TRIGGER_NODE = "NO_TRIGGER_NODE"
    DANGLING_NODES = "DANGLING_NODES"
    UNREACHABLE_NODES = "UNREACHABLE_NODES"
    DEAD_END_NODE = "DEAD_END_NODE"

    # Node compatibility errors
    INVALID_NODE_CONFIG = "INVALID_NODE_CONFIG"
    INVALID_HANDLE = "INVALID_HANDLE"
    INVALID_REFERENCE = "INVALID_REFERENCE"

    # Data flow errors
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    UNDEFINED_VARIABLE = "UNDEFINED_VARIABLE"

    # Limit errors
    GRAPH_TOO_LARGE = "GRAPH_TOO_LARGE"
    VALIDATION_TIMEOUT = "VALIDATION_TIMEOUT"


# =============================================================================
# Validation Request/Option Schemas
# =============================================================================


class ValidationOptions(BaseSchema):
    """Options for validation request.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Controls validation behavior including strictness level,
    timeout settings, and size limits.
    """

    level: ValidationLevel = Field(
        default=ValidationLevel.STANDARD,
        description="Validation strictness level",
    )
    include_topology: bool = Field(
        default=True,
        description="Include topology analysis in results",
    )
    include_warnings: bool = Field(
        default=True,
        description="Include non-blocking warnings",
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum validation time in seconds",
    )
    max_nodes: int = Field(
        default=500,
        ge=1,
        le=10000,
        description="Maximum allowed nodes",
    )
    max_edges: int = Field(
        default=2000,
        ge=0,
        le=50000,
        description="Maximum allowed edges",
    )
    max_depth: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum graph depth",
    )


class ValidationRequest(BaseSchema):
    """Request for workflow validation.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Used for on-demand validation of workflow graphs.
    """

    workflow_id: UUID = Field(
        ...,
        description="Workflow ID to validate",
    )
    options: ValidationOptions = Field(
        default_factory=ValidationOptions,
        description="Validation options",
    )
    proposed_edges: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Optional proposed edges to validate before adding",
    )


# =============================================================================
# Validation Result Schemas
# =============================================================================


class ValidationError(BaseSchema):
    """Single validation error.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Represents a blocking validation error that prevents workflow execution.
    """

    code: ValidationErrorCode = Field(
        ...,
        description="Machine-readable error code",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    node_ids: list[UUID] = Field(
        default_factory=list,
        description="Affected node IDs",
    )
    edge_ids: list[UUID] = Field(
        default_factory=list,
        description="Affected edge IDs",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context",
    )


class ValidationWarning(BaseSchema):
    """Single validation warning (non-blocking).

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]
    REQ: REQ-010-019 - Visualization Hints

    Represents a warning that doesn't prevent execution but may indicate issues.
    Includes position information for UI visualization.
    """

    code: str = Field(
        ...,
        description="Warning code",
    )
    message: str = Field(
        ...,
        description="Human-readable warning message",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Affected node ID if applicable",
    )
    suggestion: str | None = Field(
        default=None,
        description="Suggested fix or action",
    )
    position_x: float | None = Field(
        default=None,
        description="Node X coordinate for visualization",
    )
    position_y: float | None = Field(
        default=None,
        description="Node Y coordinate for visualization",
    )


class TopologyLevel(BaseSchema):
    """Single level in topological sort.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Represents a set of nodes that can execute in parallel.
    """

    level: int = Field(
        ...,
        ge=0,
        description="Execution level (0-based)",
    )
    node_ids: list[UUID] = Field(
        ...,
        description="Node IDs at this level",
    )
    can_parallel: bool = Field(
        default=True,
        description="Whether nodes at this level can execute in parallel",
    )


class TopologyResult(BaseSchema):
    """Topological analysis result.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Contains execution order and parallelization information.
    """

    execution_order: list[TopologyLevel] = Field(
        ...,
        description="Nodes grouped by execution level",
    )
    total_levels: int = Field(
        ...,
        ge=0,
        description="Total number of execution levels",
    )
    max_parallel_nodes: int = Field(
        ...,
        ge=0,
        description="Maximum nodes executing in parallel",
    )
    critical_path_length: int = Field(
        ...,
        ge=0,
        description="Length of critical path (longest dependency chain)",
    )
    critical_path: list[UUID] = Field(
        default_factory=list,
        description="Node IDs forming the critical path",
    )


class CycleCheckResult(BaseSchema):
    """Result of cycle detection.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Lightweight result for real-time UI validation.
    """

    has_cycle: bool = Field(
        ...,
        description="Whether a cycle exists",
    )
    cycle_path: list[UUID] | None = Field(
        default=None,
        description="Cycle path if cycle detected",
    )
    cycle_description: str | None = Field(
        default=None,
        description="Human-readable cycle description",
    )


class ValidationResult(BaseSchema):
    """Complete validation result.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Comprehensive validation result including errors, warnings,
    topology, and statistics.
    """

    model_config = ConfigDict(from_attributes=True)

    is_valid: bool = Field(
        ...,
        description="Whether workflow passed validation",
    )
    workflow_id: UUID = Field(
        ...,
        description="Validated workflow ID",
    )
    workflow_version: int = Field(
        ...,
        ge=1,
        description="Workflow version at time of validation",
    )
    validated_at: datetime = Field(
        ...,
        description="Validation timestamp",
    )

    # Validation details
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="Blocking validation errors",
    )
    warnings: list[ValidationWarning] = Field(
        default_factory=list,
        description="Non-blocking warnings",
    )

    # Topology (if requested and valid)
    topology: TopologyResult | None = Field(
        default=None,
        description="Topology analysis (if requested)",
    )

    # Statistics
    node_count: int = Field(
        default=0,
        ge=0,
        description="Number of nodes in workflow",
    )
    edge_count: int = Field(
        default=0,
        ge=0,
        description="Number of edges in workflow",
    )
    validation_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Validation duration in milliseconds",
    )

    # Metadata
    validation_level: ValidationLevel = Field(
        default=ValidationLevel.STANDARD,
        description="Validation level used",
    )
    cached: bool = Field(
        default=False,
        description="Whether result was retrieved from cache",
    )


# =============================================================================
# Batch Validation Schemas
# =============================================================================


class EdgeValidationRequest(BaseSchema):
    """Request for edge addition validation.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Used for real-time validation when adding edges in UI.
    """

    source_node_id: UUID = Field(
        ...,
        description="Source node ID",
    )
    target_node_id: UUID = Field(
        ...,
        description="Target node ID",
    )
    source_handle: str | None = Field(
        default=None,
        description="Source handle (for multi-output nodes)",
    )
    target_handle: str | None = Field(
        default=None,
        description="Target handle (for multi-input nodes)",
    )


class BatchValidationRequest(BaseSchema):
    """Request for batch edge validation.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Validates multiple edges together for efficiency.
    """

    workflow_id: UUID = Field(
        ...,
        description="Workflow ID",
    )
    edges: list[EdgeValidationRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Edges to validate",
    )


# =============================================================================
# Internal Use Schemas
# =============================================================================


class NodeGraphInfo(BaseSchema):
    """Internal node information for graph building.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Used internally when constructing graph structures.
    """

    id: UUID
    node_type: str
    is_trigger: bool = False
    can_be_terminal: bool = False


class EdgeGraphInfo(BaseSchema):
    """Internal edge information for graph building.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Used internally when constructing graph structures.
    """

    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    source_handle: str | None = None
    target_handle: str | None = None


# =============================================================================
# Response Wrapper
# =============================================================================


class ValidationResponse(BaseSchema):
    """Standard validation API response wrapper.

    TAG: [SPEC-010] [SCHEMAS] [VALIDATION]

    Provides consistent response format for validation endpoints.
    """

    success: bool = Field(
        ...,
        description="Whether validation completed successfully",
    )
    result: ValidationResult | None = Field(
        default=None,
        description="Validation result if successful",
    )
    error: str | None = Field(
        default=None,
        description="Error message if validation failed",
    )


__all__ = [
    "BatchValidationRequest",
    "CycleCheckResult",
    "EdgeGraphInfo",
    "EdgeValidationRequest",
    # Internal schemas
    "NodeGraphInfo",
    "TopologyLevel",
    "TopologyResult",
    # Result schemas
    "ValidationError",
    "ValidationErrorCode",
    # Enums
    "ValidationLevel",
    "ValidationOptions",
    # Request schemas
    "ValidationRequest",
    "ValidationResponse",
    "ValidationResult",
    "ValidationWarning",
]
