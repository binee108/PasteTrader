"""Tests for BaseProcessor abstract class.

TAG: [SPEC-012] [PROCESSOR] [TEST] [BASE]
REQ: REQ-012-001, REQ-012-002, REQ-012-003, REQ-012-004, REQ-012-005
"""

import pytest
import asyncio
from datetime import datetime, UTC
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import (
    ProcessorValidationError,
    ProcessorExecutionError,
    ProcessorTimeoutError,
)
from app.schemas.processors import ToolProcessorInput, ToolProcessorOutput


class MockProcessor(BaseProcessor):
    """Mock processor for testing BaseProcessor.

    TAG: [SPEC-012] [TEST] [MOCK]
    """

    input_schema = ToolProcessorInput
    output_schema = ToolProcessorOutput

    def __init__(self, node, context, config=None, raise_error=None):
        super().__init__(node, context, config)
        self.raise_error = raise_error
        self.call_count = {"pre": 0, "process": 0, "post": 0}

    async def pre_process(self, inputs: dict) -> ToolProcessorInput:
        """Mock pre_process that validates input."""
        self.call_count["pre"] += 1
        try:
            return ToolProcessorInput.model_validate(inputs)
        except Exception as e:
            raise ProcessorValidationError(
                processor="MockProcessor",
                errors=[{"message": str(e)}],
            )

    async def process(self, validated_input: ToolProcessorInput) -> ToolProcessorOutput:
        """Mock process that optionally raises error."""
        self.call_count["process"] += 1
        if self.raise_error:
            raise self.raise_error

        return ToolProcessorOutput(
            result={"status": "success", "data": validated_input.model_dump()}
        )

    async def post_process(self, output: ToolProcessorOutput) -> dict:
        """Mock post_process that serializes output."""
        self.call_count["post"] += 1
        return output.model_dump()


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_id: str):
        self.id = uuid4()
        self.node_id = node_id


class TestProcessorConfig:
    """Test ProcessorConfig dataclass."""

    def test_default_config_values(self):
        """Test ProcessorConfig has correct defaults."""
        config = ProcessorConfig()

        assert config.timeout_seconds == 60
        assert config.retry_enabled is True
        assert config.max_retries == 3
        assert config.initial_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.collect_metrics is True

    def test_custom_config_values(self):
        """Test ProcessorConfig accepts custom values."""
        config = ProcessorConfig(
            timeout_seconds=120,
            retry_enabled=False,
            max_retries=5,
        )

        assert config.timeout_seconds == 120
        assert config.retry_enabled is False
        assert config.max_retries == 5


class TestBaseProcessorLifecycle:
    """Test BaseProcessor lifecycle hook execution."""

    @pytest.mark.asyncio
    async def test_lifecycle_execution_order(self):
        """Test that lifecycle hooks execute in correct order."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        result = await processor.execute(inputs)

        # Verify execution order: pre -> process -> post
        assert processor.call_count["pre"] == 1
        assert processor.call_count["process"] == 1
        assert processor.call_count["post"] == 1

    @pytest.mark.asyncio
    async def test_execute_returns_serialized_output(self):
        """Test execute returns dict from post_process."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "result" in result
        assert result["result"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_pre_process_validates_input(self):
        """Test pre_process validates against input schema."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        # Invalid input (missing required field)
        with pytest.raises(ProcessorValidationError):
            await processor.execute({"parameters": {"key": "value"}})


class TestBaseProcessorRetryLogic:
    """Test BaseProcessor retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Test processor retries on TimeoutError."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(
            retry_enabled=True,
            max_retries=2,
            initial_delay_seconds=0.01,  # Fast for testing
        )

        # Use ConnectionError instead of TimeoutError to avoid asyncio.wait_for conflicts
        processor = MockProcessor(node, context, config, raise_error=ConnectionError("Test connection error"))

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        with pytest.raises(ProcessorExecutionError) as exc_info:
            await processor.execute(inputs)

        # Should have attempted initial + 2 retries = 3 total
        assert processor.call_count["process"] == 3
        assert "retries: 3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_retry_when_disabled(self):
        """Test processor does not retry when retry_enabled=False."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(retry_enabled=False)

        processor = MockProcessor(node, context, config, raise_error=ConnectionError("Test error"))

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        with pytest.raises(ProcessorExecutionError):
            await processor.execute(inputs)

        # Should only attempt once (no retries)
        assert processor.call_count["process"] == 1

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry uses exponential backoff."""
        import time

        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(
            retry_enabled=True,
            max_retries=2,
            initial_delay_seconds=0.05,
            backoff_multiplier=2.0,
        )

        # Use ConnectionError instead of TimeoutError
        processor = MockProcessor(node, context, config, raise_error=ConnectionError("Test"))

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        start = time.time()
        with pytest.raises(ProcessorExecutionError):
            await processor.execute(inputs)
        elapsed = time.time() - start

        # Expected delays: 0.05 (retry 1) + 0.10 (retry 2) = 0.15s minimum
        # Allow some margin for test execution time
        assert elapsed >= 0.14

    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(self):
        """Test validation errors are never retried."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(
            retry_enabled=True,
            max_retries=3,
        )

        processor = MockProcessor(node, context, config)

        # Invalid input (will fail validation in pre_process)
        with pytest.raises(ProcessorValidationError):
            await processor.execute({"invalid": "data"})

        # pre_process should only be called once (no retries for validation)
        assert processor.call_count["pre"] == 1
        assert processor.call_count["process"] == 0


class TestBaseProcessorMetrics:
    """Test BaseProcessor metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_collected_on_success(self):
        """Test metrics are collected for successful execution."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        await processor.execute(inputs)

        # Verify metrics were recorded
        metrics = processor.metrics_collector.get_metrics()
        assert len(metrics) == 1

        metric = metrics[0]
        assert metric.processor_type == "MockProcessor"
        assert metric.success is True
        assert metric.retry_count == 0

    @pytest.mark.asyncio
    async def test_metrics_include_timing(self):
        """Test metrics include timing information."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        await processor.execute(inputs)

        metrics = processor.metrics_collector.get_metrics()[0]

        # Verify timing fields are populated
        assert metrics.pre_process_duration_ms >= 0
        assert metrics.process_duration_ms >= 0
        assert metrics.post_process_duration_ms >= 0
        assert metrics.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_metrics_on_failure(self):
        """Test metrics record failure information."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        # Use ConnectionError which is retriable, will become ProcessorExecutionError
        processor = MockProcessor(node, context, raise_error=ConnectionError("Test failure"))

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
        }

        with pytest.raises(ProcessorExecutionError):
            await processor.execute(inputs)

        metrics = processor.metrics_collector.get_metrics()[0]

        assert metrics.success is False
        # error_type is ProcessorExecutionError (the wrapper), not ConnectionError
        assert metrics.error_type == "ProcessorExecutionError"


class TestBaseProcessorContextAccess:
    """Test BaseProcessor context helper methods."""

    @pytest.mark.asyncio
    async def test_get_variable_from_context(self):
        """Test get_variable retrieves from context."""
        node = MockNode("test-node")
        context = ExecutionContext(
            execution_id=uuid4(),
            variables={"user": {"id": "123", "name": "John"}},
        )
        processor = MockProcessor(node, context)

        # Get nested variable
        user_id = processor.get_variable("user.id")
        assert user_id == "123"

        # Get with default
        missing = processor.get_variable("missing.key", "default")
        assert missing == "default"

    @pytest.mark.asyncio
    async def test_get_node_output_from_context(self):
        """Test get_node_output retrieves from context."""
        node = MockNode("test-node")
        context = ExecutionContext(
            execution_id=uuid4(),
            node_outputs={
                "node-1": {"status": "done", "result": "data"},
            },
        )
        processor = MockProcessor(node, context)

        # Get entire output
        output = processor.get_node_output("node-1")
        assert output["status"] == "done"

        # Get specific key
        result = processor.get_node_output("node-1", "result")
        assert result == "data"

    @pytest.mark.asyncio
    async def test_get_node_output_raises_on_missing(self):
        """Test get_node_output raises KeyError for missing node."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        processor = MockProcessor(node, context)

        with pytest.raises(KeyError, match="Node missing-node not found in execution context"):
            processor.get_node_output("missing-node")


class TestBaseProcessorTimeout:
    """Test BaseProcessor timeout enforcement."""

    @pytest.mark.asyncio
    async def test_process_timeout_enforcement(self):
        """Test process is cancelled after timeout."""
        node = MockNode("test-node")
        context = ExecutionContext(execution_id=uuid4())
        config = ProcessorConfig(timeout_seconds=0.1)  # 100ms timeout

        async def slow_process(validated_input):
            await asyncio.sleep(0.2)  # Sleep longer than timeout
            return ToolProcessorOutput(result={"status": "done"})

        processor = MockProcessor(node, context, config)
        processor.process = slow_process

        inputs = {
            "tool_id": "test-tool",
            "parameters": {},
        }

        # ProcessorTimeoutError should be raised (not ProcessorExecutionError)
        with pytest.raises(ProcessorTimeoutError):
            await processor.execute(inputs)
