"""Tests for AggregatorNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [AGGREGATOR]
REQ: REQ-012-015 - Data aggregation from multiple sources
"""

import pytest
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.aggregator import AggregatorNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import AggregatorProcessorInput


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "aggregator"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestAggregatorNodeProcessorPreProcess:
    """Test AggregatorNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        inputs = {
            "strategy": "merge",
            "input_sources": {
                "source1": {"key": "value1"},
                "source2": {"key2": "value2"},
            },
            "aggregation_config": {"deep": True},
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, AggregatorProcessorInput)
        assert result.strategy == "merge"

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        inputs = {
            "input_sources": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_strategy(self):
        """Test pre_process raises on invalid strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        inputs = {
            "strategy": "invalid_strategy",
            "input_sources": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_with_defaults(self):
        """Test pre_process applies defaults."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        inputs = {
            "strategy": "list",
            "input_sources": {"source1": [1, 2], "source2": [3, 4]},
        }

        result = await processor.pre_process(inputs)

        assert result.aggregation_config == {}


class TestAggregatorNodeProcessorProcess:
    """Test AggregatorNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_merge_strategy(self):
        """Test process applies merge strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        validated_input = AggregatorProcessorInput(
            strategy="merge",
            input_sources={"source1": {"a": 1}, "source2": {"b": 2}},
        )

        result = await processor.process(validated_input)

        assert result.strategy_used == "merge"
        assert result.source_count == 2
        assert isinstance(result.aggregated_result, dict)

    @pytest.mark.asyncio
    async def test_list_strategy(self):
        """Test process applies list strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        validated_input = AggregatorProcessorInput(
            strategy="list",
            input_sources={"source1": [1, 2], "source2": [3, 4]},
        )

        result = await processor.process(validated_input)

        assert result.strategy_used == "list"
        assert result.source_count == 2
        assert isinstance(result.aggregated_result, list)

    @pytest.mark.asyncio
    async def test_reduce_strategy(self):
        """Test process applies reduce strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        validated_input = AggregatorProcessorInput(
            strategy="reduce",
            input_sources={"source1": 10, "source2": 20, "source3": 30},
            aggregation_config={"operation": "sum"},
        )

        result = await processor.process(validated_input)

        assert result.strategy_used == "reduce"
        assert result.source_count == 3

    @pytest.mark.asyncio
    async def test_custom_strategy(self):
        """Test process applies custom strategy."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        validated_input = AggregatorProcessorInput(
            strategy="custom",
            input_sources={"source1": "data1", "source2": "data2"},
            aggregation_config={"function": "concatenate"},
        )

        result = await processor.process(validated_input)

        assert result.strategy_used == "custom"
        assert result.source_count == 2


class TestAggregatorNodeProcessorPostProcess:
    """Test AggregatorNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        from app.schemas.processors import AggregatorProcessorOutput

        output = AggregatorProcessorOutput(
            aggregated_result={"merged": "data"},
            source_count=2,
            strategy_used="merge",
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "aggregated_result" in result
        assert "source_count" in result
        assert "strategy_used" in result


class TestAggregatorNodeProcessorIntegration:
    """Integration tests for AggregatorNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AggregatorNodeProcessor(node, context)

        inputs = {
            "strategy": "merge",
            "input_sources": {"source1": {"a": 1}, "source2": {"b": 2}},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "aggregated_result" in result
        assert "source_count" in result
        assert "strategy_used" in result
