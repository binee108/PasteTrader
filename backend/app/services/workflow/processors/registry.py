"""Processor Registry.

TAG: [SPEC-012] [PROCESSOR] [REGISTRY]
REQ: REQ-012-016, REQ-012-017 - Dynamic Processor Registration and Default Registration
"""

from typing import Any

from app.models.workflow import Node
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorNotFoundError


class ProcessorRegistry:
    """Registry for dynamic processor lookup and instantiation.

    TAG: [SPEC-012] [REGISTRY]

    Manages processor class registration and provides methods for
    looking up and instantiating processors by node type.

    Example:
        registry = ProcessorRegistry()
        processor = registry.create("tool", node, context)
        result = await processor.execute(inputs)
    """

    def __init__(self) -> None:
        """Initialize registry and register default processors."""
        self._processors: dict[str, type[BaseProcessor[Any, Any]]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default processor types.

        TAG: [SPEC-012] [REGISTRY] [DEFAULTS]

        Registers the six built-in processor types.
        """
        # Import here to avoid circular dependencies
        from app.services.workflow.processors.adapter import AdapterNodeProcessor
        from app.services.workflow.processors.agent import AgentNodeProcessor
        from app.services.workflow.processors.aggregator import AggregatorNodeProcessor
        from app.services.workflow.processors.condition import ConditionNodeProcessor
        from app.services.workflow.processors.tool import ToolNodeProcessor
        from app.services.workflow.processors.trigger import TriggerNodeProcessor

        defaults = {
            "tool": ToolNodeProcessor,
            "agent": AgentNodeProcessor,
            "condition": ConditionNodeProcessor,
            "adapter": AdapterNodeProcessor,
            "trigger": TriggerNodeProcessor,
            "aggregator": AggregatorNodeProcessor,
        }

        for node_type, processor_class in defaults.items():
            self.register(node_type, processor_class)

    def register(
        self,
        node_type: str,
        processor_class: type,
    ) -> None:
        """Register a processor class for a node type.

        TAG: [SPEC-012] [REGISTRY] [REGISTER]

        Args:
            node_type: The node type identifier (e.g., "tool", "agent")
            processor_class: The processor class to register

        Note:
            If a processor is already registered for the node_type,
            it will be overwritten with the new processor class.
        """
        self._processors[node_type] = processor_class

    def get(self, node_type: str) -> type[BaseProcessor[Any, Any]]:
        """Get processor class for node type.

        TAG: [SPEC-012] [REGISTRY] [GET]

        Args:
            node_type: The node type identifier

        Returns:
            The processor class for the node type

        Raises:
            ProcessorNotFoundError: If no processor registered for node_type
        """
        if node_type not in self._processors:
            raise ProcessorNotFoundError(
                f"No processor registered for node type: {node_type}"
            )
        return self._processors[node_type]

    def create(
        self,
        node_type: str,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> BaseProcessor[Any, Any]:
        """Create processor instance with configuration.

        TAG: [SPEC-012] [REGISTRY] [CREATE]

        Args:
            node_type: The node type identifier
            node: The workflow node instance
            context: The execution context
            config: Optional processor configuration (uses defaults if None)

        Returns:
            Instantiated processor with node, context, and config

        Raises:
            ProcessorNotFoundError: If no processor registered for node_type
        """
        processor_class = self.get(node_type)
        return processor_class(node=node, context=context, config=config)

    def list_registered(self) -> list[str]:
        """List all registered processor types.

        TAG: [SPEC-012] [REGISTRY] [LIST]

        Returns:
            List of registered node type identifiers
        """
        return list(self._processors.keys())


# Module-level singleton for convenience
_registry: ProcessorRegistry | None = None


def get_registry() -> ProcessorRegistry:
    """Get the global processor registry singleton.

    TAG: [SPEC-012] [REGISTRY] [SINGLETON]

    Returns:
        The global ProcessorRegistry instance (creates on first call)

    Example:
        registry = get_registry()
        processor = registry.create("tool", node, context)
    """
    global _registry
    if _registry is None:
        _registry = ProcessorRegistry()
    return _registry
