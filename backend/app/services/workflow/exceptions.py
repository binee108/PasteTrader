"""DAG Validation Service custom exceptions.

TAG: [SPEC-010] [DAG] [EXCEPTIONS]

This module defines custom exceptions for DAG validation operations.
All exceptions inherit from DAGValidationError for consistent error handling.
"""

from typing import Any

from uuid import UUID


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
