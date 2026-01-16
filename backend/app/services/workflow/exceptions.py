"""DAG Validation and Execution custom exceptions.

TAG: [SPEC-010] [DAG] [EXCEPTIONS]
TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

This module defines custom exceptions for DAG validation operations
and workflow execution operations. All exceptions inherit from their
respective base exceptions for consistent error handling.
"""

from typing import Any
from uuid import UUID


# ============================================================================
# DAG Validation Exceptions (SPEC-010)
# ============================================================================

class DAGValidationError(Exception):
    """Base exception for DAG validation errors.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]

    Attributes:
        message: Human-readable error message.
        error_code: Machine-readable error code for API responses.
        details: Additional error context as dictionary.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class CycleDetectedError(DAGValidationError):
    """Raised when a cycle is detected in the graph.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]

    Attributes:
        cycle_path: List of node IDs forming the cycle.
    """

    def __init__(self, cycle_path: list[UUID]) -> None:
        cycle_str = " -> ".join(str(n)[:8] for n in cycle_path)
        super().__init__(
            message=f"Cycle detected: {cycle_str}",
            error_code="CYCLE_DETECTED",
            details={"cycle_path": [str(n) for n in cycle_path]},
        )
        self.cycle_path = cycle_path


class InvalidNodeReferenceError(DAGValidationError):
    """Raised when node reference is invalid.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]

    Attributes:
        missing_nodes: List of node IDs that were not found.
    """

    def __init__(self, node_ids: list[UUID]) -> None:
        super().__init__(
            message=f"Invalid node references: {node_ids}",
            error_code="NODE_NOT_FOUND",
            details={"missing_nodes": [str(n) for n in node_ids]},
        )
        self.missing_nodes = node_ids


class GraphTooLargeError(DAGValidationError):
    """Raised when graph exceeds size limits.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]

    Attributes:
        current: Current count.
        limit: Maximum allowed limit.
        metric: Type of metric (nodes, edges, depth).
    """

    def __init__(self, current: int, limit: int, metric: str = "nodes") -> None:
        super().__init__(
            message=f"Graph too large: {current} {metric} (limit: {limit})",
            error_code="GRAPH_TOO_LARGE",
            details={"current": current, "limit": limit, "metric": metric},
        )
        self.current = current
        self.limit = limit
        self.metric = metric


class ValidationTimeoutError(DAGValidationError):
    """Raised when validation exceeds timeout.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS]

    Attributes:
        timeout_seconds: Timeout duration in seconds.
    """

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            message=f"Validation timeout after {timeout_seconds}s",
            error_code="VALIDATION_TIMEOUT",
            details={"timeout_seconds": timeout_seconds},
        )
        self.timeout_seconds = timeout_seconds


# ============================================================================
# Workflow Execution Exceptions (SPEC-011)
# ============================================================================

class ExecutionError(Exception):
    """Base exception for workflow execution errors.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

    Attributes:
        message: Human-readable error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NodeTimeoutError(ExecutionError):
    """Raised when node execution exceeds timeout.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

    Attributes:
        node_id: ID of the node that timed out.
        timeout_seconds: Timeout duration in seconds.
    """

    def __init__(self, node_id: UUID, timeout_seconds: float) -> None:
        message = f"Node {str(node_id)[:8]} execution timed out after {timeout_seconds}s"
        super().__init__(message)
        self.node_id = node_id
        self.timeout_seconds = timeout_seconds


class NodeExecutionError(ExecutionError):
    """Raised when node execution fails.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

    Attributes:
        node_id: ID of the node that failed.
        message: Error message.
        original_error: The original exception that caused the failure.
    """

    def __init__(self, node_id: UUID, message: str, original_error: Exception | None = None) -> None:
        error_message = f"Node {str(node_id)[:8]} execution failed: {message}"
        super().__init__(error_message)
        self.node_id = node_id
        self.message = message
        self.original_error = original_error


class ExecutionCancelledError(ExecutionError):
    """Raised when workflow execution is cancelled.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

    Attributes:
        execution_id: ID of the cancelled execution.
    """

    def __init__(self, execution_id: UUID) -> None:
        message = f"Execution {str(execution_id)[:8]} was cancelled"
        super().__init__(message)
        self.execution_id = execution_id


class ConditionEvaluationError(ExecutionError):
    """Raised when condition evaluation fails.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]

    Attributes:
        node_id: ID of the condition node that failed.
        reason: Reason for the evaluation failure.
    """

    def __init__(self, node_id: UUID, reason: str) -> None:
        message = f"Condition node {str(node_id)[:8]} evaluation failed: {reason}"
        super().__init__(message)
        self.node_id = node_id
        self.reason = reason
