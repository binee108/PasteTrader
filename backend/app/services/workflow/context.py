"""ExecutionContext for workflow execution.

TAG: [SPEC-012] [WORKFLOW] [CONTEXT]

This module provides the execution context for processors.
Will be fully integrated with SPEC-011 when available.
"""

from typing import Any
from uuid import UUID


class ExecutionContext:
    """Execution context for workflow processors.

    TAG: [SPEC-012] [CONTEXT]

    Provides access to execution variables and node outputs.
    This is a simplified stub that will be enhanced by SPEC-011.
    """

    def __init__(
        self,
        execution_id: UUID,
        variables: dict[str, Any] | None = None,
        node_outputs: dict[str, dict[str, Any]] | None = None,
    ):
        """Initialize execution context.

        Args:
            execution_id: Unique identifier for this execution
            variables: Runtime variables available during execution
            node_outputs: Outputs from previously executed nodes
        """
        self.execution_id = execution_id
        self.variables = variables or {}
        self.node_outputs = node_outputs or {}

    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get variable from execution context.

        TAG: [SPEC-012] [CONTEXT] [GET_VARIABLE]

        Args:
            path: Variable path (e.g., "user.id" or "api_key")
            default: Default value if variable not found

        Returns:
            Variable value or default
        """
        # Simple dot-notation access
        keys = path.split(".")
        value = self.variables

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_node_output(self, node_id: str, key: str | None = None) -> Any:
        """Get output from a previously executed node.

        TAG: [SPEC-012] [CONTEXT] [GET_NODE_OUTPUT]

        Args:
            node_id: ID of the node to get output from
            key: Optional key within the node output

        Returns:
            Node output value or entire output dict if key is None

        Raises:
            KeyError: If node_id not found in context
        """
        if node_id not in self.node_outputs:
            raise KeyError(f"Node {node_id} not found in execution context")

        output = self.node_outputs[node_id]

        if key is not None:
            if isinstance(output, dict) and key in output:
                return output[key]
            raise KeyError(f"Key {key} not found in node {node_id} output")

        return output

    def set_variable(self, path: str, value: Any) -> None:
        """Set variable in execution context.

        TAG: [SPEC-012] [CONTEXT] [SET_VARIABLE]

        Args:
            path: Variable path (e.g., "user.id")
            value: Value to set
        """
        keys = path.split(".")
        current = self.variables

        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the value
        current[keys[-1]] = value

    def set_node_output(self, node_id: str, outputs: dict[str, Any]) -> None:
        """Store node output in execution context.

        TAG: [SPEC-012] [CONTEXT] [SET_NODE_OUTPUT]

        Args:
            node_id: ID of the node
            outputs: Output data from the node
        """
        self.node_outputs[node_id] = outputs
