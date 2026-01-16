"""Tests for ProcessorRegistry.

TAG: [SPEC-012] [PROCESSOR] [TEST] [REGISTRY]
REQ: REQ-012-016, REQ-012-017 - Dynamic Processor Registration and Default Registration
"""

import pytest
from uuid import uuid4

from app.models.enums import NodeType
from app.models.workflow import Node
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.registry import ProcessorRegistry, get_registry
from app.services.workflow.processors.errors import ProcessorNotFoundError
from app.schemas.processors import ToolProcessorInput, ToolProcessorOutput


# Mock processor for testing
class MockToolProcessor(BaseProcessor[ToolProcessorInput, ToolProcessorOutput]):
    """Mock tool processor for testing."""

    input_schema = ToolProcessorInput
    output_schema = ToolProcessorOutput

    def __init__(self, node, context, config=None):
        super().__init__(node, context, config)

    async def pre_process(self, inputs):
        return ToolProcessorInput.model_validate(inputs)

    async def process(self, validated_input):
        return ToolProcessorOutput(result={"status": "done"})

    async def post_process(self, output):
        return output.model_dump()


class MockAgentProcessor(BaseProcessor[ToolProcessorInput, ToolProcessorOutput]):
    """Mock agent processor for testing."""

    input_schema = ToolProcessorInput
    output_schema = ToolProcessorOutput

    def __init__(self, node, context, config=None):
        super().__init__(node, context, config)

    async def pre_process(self, inputs):
        return ToolProcessorInput.model_validate(inputs)

    async def process(self, validated_input):
        return ToolProcessorOutput(result={"status": "agent_done"})

    async def post_process(self, output):
        return output.model_dump()


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = NodeType.TOOL):
        self.id = uuid4()
        self.node_type = node_type
        self.name = "test-node"


class TestProcessorRegistry:
    """Test ProcessorRegistry functionality."""

    def test_registry_initialization(self):
        """Test registry initializes with default processors."""
        registry = ProcessorRegistry()

        # Check default processors are registered
        registered = registry.list_registered()

        assert "tool" in registered
        assert "agent" in registered
        assert "condition" in registered
        assert "adapter" in registered
        assert "trigger" in registered
        assert "aggregator" in registered

    def test_register_custom_processor(self):
        """Test registering a custom processor."""
        registry = ProcessorRegistry()

        # Register custom processor
        registry.register("custom_tool", MockToolProcessor)

        # Verify it's registered
        processor_class = registry.get("custom_tool")
        assert processor_class is MockToolProcessor

    def test_register_overwrites_existing(self):
        """Test registering overwrites existing processor."""
        registry = ProcessorRegistry()

        # Register custom processor for existing type
        registry.register("tool", MockAgentProcessor)

        # Verify it was overwritten
        processor_class = registry.get("tool")
        assert processor_class is MockAgentProcessor

    def test_get_processor_class(self):
        """Test getting processor class by node type."""
        registry = ProcessorRegistry()

        # Get existing processor
        processor_class = registry.get("tool")

        assert processor_class is not None
        assert callable(processor_class)

    def test_get_nonexistent_processor_raises(self):
        """Test getting non-existent processor raises error."""
        registry = ProcessorRegistry()

        with pytest.raises(ProcessorNotFoundError):
            registry.get("nonexistent_type")

    def test_create_processor_instance(self):
        """Test creating processor instance."""
        registry = ProcessorRegistry()
        node = MockNode(NodeType.TOOL)
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(timeout_seconds=30)

        # Create processor instance
        processor = registry.create("tool", node, context, config)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)
        assert processor.node is node
        assert processor.context is context
        assert processor.config.timeout_seconds == 30

    def test_create_with_default_config(self):
        """Test creating processor without config uses defaults."""
        registry = ProcessorRegistry()
        node = MockNode(NodeType.AGENT)
        context = ExecutionContext(execution_id=uuid4())

        # Create without config
        processor = registry.create("agent", node, context)

        assert processor.config is not None
        assert processor.config.timeout_seconds == 60  # Default value

    def test_create_nonexistent_processor_raises(self):
        """Test creating non-existent processor raises error."""
        registry = ProcessorRegistry()
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())

        with pytest.raises(ProcessorNotFoundError):
            registry.create("nonexistent", node, context)

    def test_list_registered(self):
        """Test listing all registered processors."""
        registry = ProcessorRegistry()

        # Register custom processor
        registry.register("custom", MockToolProcessor)

        # List all
        registered = registry.list_registered()

        assert "tool" in registered
        assert "agent" in registered
        assert "custom" in registered
        assert len(registered) >= 7  # 6 defaults + 1 custom


class TestRegistryModuleLevelSingleton:
    """Test module-level registry singleton."""

    def test_get_registry_returns_singleton(self):
        """Test get_registry returns singleton instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        # Should be the same instance
        assert registry1 is registry2

    def test_get_registry_is_initialized(self):
        """Test get_registry returns initialized registry."""
        registry = get_registry()

        # Should have default processors
        registered = registry.list_registered()
        assert len(registered) >= 6

    def test_get_registry_persists_registrations(self):
        """Test registrations persist across get_registry calls."""
        registry1 = get_registry()
        registry1.register("custom_singleton", MockToolProcessor)

        registry2 = get_registry()

        # Registration should persist
        assert "custom_singleton" in registry2.list_registered()


class TestProcessorRegistryWithRealNodes:
    """Test registry with real Node objects."""

    def test_create_for_tool_node(self):
        """Test creating processor for TOOL node type."""
        registry = ProcessorRegistry()

        # Create real Node model
        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.TOOL,
            name="test-tool-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("tool", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    def test_create_for_agent_node(self):
        """Test creating processor for AGENT node type."""
        registry = ProcessorRegistry()

        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.AGENT,
            name="test-agent-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("agent", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    def test_create_for_condition_node(self):
        """Test creating processor for CONDITION node type."""
        registry = ProcessorRegistry()

        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.CONDITION,
            name="test-condition-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("condition", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    def test_create_for_adapter_node(self):
        """Test creating processor for ADAPTER node type."""
        registry = ProcessorRegistry()

        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.ADAPTER,
            name="test-adapter-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("adapter", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    def test_create_for_trigger_node(self):
        """Test creating processor for TRIGGER node type."""
        registry = ProcessorRegistry()

        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.TRIGGER,
            name="test-trigger-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("trigger", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)

    def test_create_for_aggregator_node(self):
        """Test creating processor for AGGREGATOR node type."""
        registry = ProcessorRegistry()

        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            node_type=NodeType.AGGREGATOR,
            name="test-aggregator-node",
            position_x=0,
            position_y=0,
        )
        context = ExecutionContext(execution_id=uuid4())

        processor = registry.create("aggregator", node, context)

        assert processor is not None
        assert isinstance(processor, BaseProcessor)
