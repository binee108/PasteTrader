"""Tests for TriggerNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [TRIGGER]
REQ: REQ-012-014 - Trigger initialization and execution
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.trigger import TriggerNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import TriggerProcessorInput


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "trigger"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestTriggerNodeProcessorPreProcess:
    """Test TriggerNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        inputs = {
            "trigger_type": "webhook",
            "trigger_payload": {"event": "data"},
            "trigger_metadata": {"source": "external"},
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, TriggerProcessorInput)
        assert result.trigger_type == "webhook"

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing trigger_type."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        inputs = {
            "trigger_payload": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_trigger_type(self):
        """Test pre_process raises on invalid trigger_type."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        inputs = {
            "trigger_type": "invalid_type",
            "trigger_payload": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_with_defaults(self):
        """Test pre_process applies defaults."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        inputs = {
            "trigger_type": "schedule",
        }

        result = await processor.pre_process(inputs)

        assert result.trigger_payload == {}
        assert result.trigger_metadata == {}


class TestTriggerNodeProcessorProcess:
    """Test TriggerNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_process_webhook_trigger(self):
        """Test process handles webhook trigger."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        validated_input = TriggerProcessorInput(
            trigger_type="webhook",
            trigger_payload={"event": "user.created"},
            trigger_metadata={"source": "api"},
        )

        result = await processor.process(validated_input)

        assert result.initialized is True
        assert isinstance(result.context_variables, dict)
        assert isinstance(result.trigger_timestamp, datetime)

    @pytest.mark.asyncio
    async def test_process_schedule_trigger(self):
        """Test process handles schedule trigger."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        validated_input = TriggerProcessorInput(
            trigger_type="schedule",
            trigger_payload={"schedule_id": "daily-9am"},
        )

        result = await processor.process(validated_input)

        assert result.initialized is True
        assert "schedule_id" in result.context_variables

    @pytest.mark.asyncio
    async def test_process_manual_trigger(self):
        """Test process handles manual trigger."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        validated_input = TriggerProcessorInput(
            trigger_type="manual",
            trigger_payload={"user_id": "user-123"},
        )

        result = await processor.process(validated_input)

        assert result.initialized is True


class TestTriggerNodeProcessorPostProcess:
    """Test TriggerNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        from app.schemas.processors import TriggerProcessorOutput

        output = TriggerProcessorOutput(
            initialized=True,
            context_variables={"user_id": "123"},
            trigger_timestamp=datetime.now(UTC),
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "initialized" in result
        assert "context_variables" in result
        assert "trigger_timestamp" in result


class TestTriggerNodeProcessorIntegration:
    """Integration tests for TriggerNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = TriggerNodeProcessor(node, context)

        inputs = {
            "trigger_type": "webhook",
            "trigger_payload": {"event": "data"},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "initialized" in result
        assert "context_variables" in result
        assert "trigger_timestamp" in result
