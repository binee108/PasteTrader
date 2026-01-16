"""Tests for ToolNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [TOOL]
REQ: REQ-012-010 - Tool execution with validated parameters
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.tool import ToolNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import ToolProcessorInput, ToolProcessorOutput


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "tool"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestToolNodeProcessorPreProcess:
    """Test ToolNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"key": "value"},
            "timeout_seconds": 30,
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, ToolProcessorInput)
        assert result.tool_id == "test-tool"
        assert result.parameters == {"key": "value"}
        assert result.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_validate_with_defaults(self):
        """Test pre_process applies defaults."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
        }

        result = await processor.pre_process(inputs)

        assert result.parameters == {}
        assert result.timeout_seconds == 30  # Default value

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing tool_id."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        inputs = {
            "parameters": {"key": "value"},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_timeout(self):
        """Test pre_process raises on invalid timeout."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "timeout_seconds": 500,  # Exceeds max of 300
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)


class TestToolNodeProcessorProcess:
    """Test ToolNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_process_returns_valid_output(self):
        """Test process returns ToolProcessorOutput."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        validated_input = ToolProcessorInput(
            tool_id="test-tool",
            parameters={"key": "value"},
        )

        result = await processor.process(validated_input)

        assert isinstance(result, ToolProcessorOutput)
        assert result.result is not None
        assert result.execution_duration_ms >= 0
        assert result.tool_metadata is not None

    @pytest.mark.asyncio
    async def test_process_includes_execution_time(self):
        """Test process measures execution duration."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        validated_input = ToolProcessorInput(
            tool_id="test-tool",
            parameters={"key": "value"},
        )

        result = await processor.process(validated_input)

        assert result.execution_duration_ms >= 0
        assert isinstance(result.execution_duration_ms, float)

    @pytest.mark.asyncio
    async def test_process_includes_tool_metadata(self):
        """Test process includes metadata in output."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        validated_input = ToolProcessorInput(
            tool_id="test-tool",
            parameters={"key": "value"},
        )

        result = await processor.process(validated_input)

        assert "tool_id" in result.tool_metadata
        assert result.tool_metadata["tool_id"] == "test-tool"


class TestToolNodeProcessorPostProcess:
    """Test ToolNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        output = ToolProcessorOutput(
            result={"status": "success"},
            execution_duration_ms=100.0,
            tool_metadata={"tool_id": "test"},
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "result" in result
        assert "execution_duration_ms" in result
        assert "tool_metadata" in result


class TestToolNodeProcessorIntegration:
    """Integration tests for ToolNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ToolNodeProcessor(node, context)

        inputs = {
            "tool_id": "test-tool",
            "parameters": {"query": "test"},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "result" in result
        assert "execution_duration_ms" in result
        assert "tool_metadata" in result
