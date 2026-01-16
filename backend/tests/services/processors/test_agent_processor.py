"""Tests for AgentNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [AGENT]
REQ: REQ-012-011 - Agent execution with LLM calls
"""

import pytest
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.agent import AgentNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import AgentProcessorInput, AgentProcessorOutput


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "agent"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestAgentNodeProcessorPreProcess:
    """Test AgentNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "agent_id": "agent-123",
            "prompt_variables": {"name": "John"},
            "max_tokens": 2048,
            "temperature": 0.5,
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, AgentProcessorInput)
        assert result.agent_id == "agent-123"
        assert result.prompt_variables == {"name": "John"}
        assert result.max_tokens == 2048
        assert result.temperature == 0.5

    @pytest.mark.asyncio
    async def test_validate_with_defaults(self):
        """Test pre_process applies defaults."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "agent_id": "agent-123",
        }

        result = await processor.pre_process(inputs)

        assert result.prompt_variables == {}
        assert result.max_tokens == 4096  # Default
        assert result.temperature == 0.7  # Default

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing agent_id."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "temperature": 0.5,
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_temperature(self):
        """Test pre_process raises on invalid temperature."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "agent_id": "agent-123",
            "temperature": 3.0,  # Exceeds max of 2.0
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_max_tokens(self):
        """Test pre_process raises on invalid max_tokens."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "agent_id": "agent-123",
            "max_tokens": 200000,  # Exceeds max of 128000
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)


class TestAgentNodeProcessorProcess:
    """Test AgentNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_process_returns_valid_output(self):
        """Test process returns AgentProcessorOutput."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        validated_input = AgentProcessorInput(
            agent_id="agent-123",
            prompt_variables={"name": "John"},
        )

        result = await processor.process(validated_input)

        assert isinstance(result, AgentProcessorOutput)
        assert result.response is not None
        assert result.model_used is not None

    @pytest.mark.asyncio
    async def test_process_includes_model_used(self):
        """Test process includes model identifier."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        validated_input = AgentProcessorInput(
            agent_id="agent-123",
        )

        result = await processor.process(validated_input)

        assert result.model_used is not None
        assert isinstance(result.model_used, str)

    @pytest.mark.asyncio
    async def test_process_includes_token_usage(self):
        """Test process includes token usage stats."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        validated_input = AgentProcessorInput(
            agent_id="agent-123",
        )

        result = await processor.process(validated_input)

        assert isinstance(result.token_usage, dict)


class TestAgentNodeProcessorPostProcess:
    """Test AgentNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        output = AgentProcessorOutput(
            response="Test response",
            model_used="claude-3-5-sonnet",
            token_usage={"prompt": 10, "completion": 20},
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "response" in result
        assert "model_used" in result
        assert "token_usage" in result


class TestAgentNodeProcessorIntegration:
    """Integration tests for AgentNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AgentNodeProcessor(node, context)

        inputs = {
            "agent_id": "agent-123",
            "prompt_variables": {"query": "test"},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "response" in result
        assert "model_used" in result
        assert "token_usage" in result
