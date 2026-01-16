"""ExecutionContext for workflow execution.

TAG: [SPEC-011] [EXECUTION] [CONTEXT]
REQ: REQ-011-003 - ExecutionContext for node data passing

This module provides ExecutionContext class for managing data flow
between workflow nodes during execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.workflow import Edge, Node


class ExecutionContext:
    """Thread-safe context for passing data between nodes.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT]
    REQ: REQ-011-003

    Manages workflow variables, node outputs, and error recording
    during workflow execution. Uses asyncio.Lock for thread safety.

    Attributes:
        workflow_execution_id: UUID of the workflow execution.
        _variables: Workflow variables dictionary.
        _node_outputs: Dictionary mapping node IDs to their output data.
        _errors: List of error dictionaries.
        _lock: Async lock for thread-safe operations.

    """

    def __init__(self, workflow_execution_id: UUID, input_data: dict[str, Any]) -> None:
        """Initialize the execution context.

        Args:
            workflow_execution_id: UUID of the workflow execution.
            input_data: Initial input data for the workflow.

        """
        from asyncio import Lock

        self.workflow_execution_id = workflow_execution_id
        self._variables: dict[str, Any] = dict(input_data)
        self._node_outputs: dict[UUID, dict[str, Any]] = {}
        self._errors: list[dict[str, Any]] = []
        self._lock = Lock()

    async def get_input(self, node: Node, incoming_edges: list[Edge]) -> dict[str, Any]:  # noqa: ARG002
        """Get input data for a node from predecessor outputs.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Merges outputs from all predecessor nodes into a single input dict.
        If multiple predecessors produce the same key, the last one wins.

        Args:
            node: The target node to get input for.
            incoming_edges: List of edges coming into this node.

        Returns:
            Merged input data dictionary from all predecessor outputs.

        """
        input_data: dict[str, Any] = {}

        async with self._lock:
            for edge in incoming_edges:
                predecessor_output = self._node_outputs.get(edge.source_node_id, {})
                input_data.update(predecessor_output)

        return input_data

    async def set_output(self, node_id: UUID, data: dict[str, Any]) -> None:
        """Store output data from a node.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Args:
            node_id: UUID of the node that produced the output.
            data: Output data dictionary to store.

        """
        async with self._lock:
            self._node_outputs[node_id] = data

    async def get_variable(self, name: str) -> Any:
        """Get a workflow variable.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Args:
            name: Name of the variable to retrieve.

        Returns:
            Variable value, or None if not found.

        """
        async with self._lock:
            return self._variables.get(name)

    async def set_variable(self, name: str, value: Any) -> None:
        """Set a workflow variable.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Args:
            name: Name of the variable to set.
            value: Value to set.

        """
        async with self._lock:
            self._variables[name] = value

    async def add_error(
        self, node_id: UUID, error_type: str, message: str,
    ) -> None:
        """Record an execution error.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Args:
            node_id: UUID of the node where the error occurred.
            error_type: Type/class name of the error.
            message: Error message.

        """
        async with self._lock:
            self._errors.append(
                {"node_id": str(node_id), "error_type": error_type, "message": message},
            )

    def has_errors(self) -> bool:
        """Check if any errors occurred.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Returns:
            True if errors have been recorded, False otherwise.

        """
        # Synchronous method - lock not needed for simple len check
        return len(self._errors) > 0

    async def get_all_outputs(self) -> dict[UUID, dict[str, Any]]:
        """Get all node outputs.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT]
        REQ: REQ-011-003

        Returns:
            Dictionary mapping node IDs to their output data.

        """
        async with self._lock:
            return dict(self._node_outputs)
