"""Tests for AdapterNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [ADAPTER]
REQ: REQ-012-013 - Data transformation with adapters
"""

import pytest
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.adapter import AdapterNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import AdapterProcessorInput


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "adapter"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestAdapterNodeProcessorPreProcess:
    """Test AdapterNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        inputs = {
            "transformation_type": "field_mapping",
            "source_data": {"old_name": "value"},
            "transformation_config": {"mapping": {"old_name": "new_name"}},
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, AdapterProcessorInput)
        assert result.transformation_type == "field_mapping"

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing transformation_type."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        inputs = {
            "source_data": {"key": "value"},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)

    @pytest.mark.asyncio
    async def test_validate_invalid_transformation_type(self):
        """Test pre_process raises on invalid transformation_type."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        inputs = {
            "transformation_type": "invalid_type",
            "source_data": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)


class TestAdapterNodeProcessorProcess:
    """Test AdapterNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_field_mapping_transformation(self):
        """Test process applies field mapping."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        validated_input = AdapterProcessorInput(
            transformation_type="field_mapping",
            source_data={"old_name": "value"},
            transformation_config={"mapping": {"old_name": "new_name"}},
        )

        result = await processor.process(validated_input)

        assert result.transformation_applied == "field_mapping"
        assert "new_name" in result.transformed_data

    @pytest.mark.asyncio
    async def test_type_conversion_transformation(self):
        """Test process applies type conversion."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        validated_input = AdapterProcessorInput(
            transformation_type="type_conversion",
            source_data={"value": "123"},
            transformation_config={"conversions": {"value": "integer"}},
        )

        result = await processor.process(validated_input)

        assert result.transformation_applied == "type_conversion"
        assert isinstance(result.transformed_data.get("value"), int)

    @pytest.mark.asyncio
    async def test_filtering_transformation(self):
        """Test process applies filtering."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        validated_input = AdapterProcessorInput(
            transformation_type="filtering",
            source_data={"items": [1, 2, 3, 4, 5]},
            transformation_config={"filter": "items > 2"},
        )

        result = await processor.process(validated_input)

        assert result.transformation_applied == "filtering"
        assert result.records_processed > 0

    @pytest.mark.asyncio
    async def test_aggregation_transformation(self):
        """Test process applies aggregation."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        validated_input = AdapterProcessorInput(
            transformation_type="aggregation",
            source_data={"field1": "value1", "field2": "value2", "field3": "value3"},
            transformation_config={},
        )

        result = await processor.process(validated_input)

        assert result.transformation_applied == "aggregation"
        assert result.transformed_data == {"aggregated": 3}
        assert result.records_processed == 3

    @pytest.mark.asyncio
    async def test_custom_transformation(self):
        """Test process applies custom transformation (pass-through)."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        validated_input = AdapterProcessorInput(
            transformation_type="custom",
            source_data={"custom_field": "custom_value"},
            transformation_config={},
        )

        result = await processor.process(validated_input)

        assert result.transformation_applied == "custom"
        assert result.transformed_data == {"custom_field": "custom_value"}
        assert result.records_processed == 1


class TestAdapterNodeProcessorPostProcess:
    """Test AdapterNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        from app.schemas.processors import AdapterProcessorOutput

        output = AdapterProcessorOutput(
            transformed_data={"result": "value"},
            transformation_applied="field_mapping",
            records_processed=1,
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "transformed_data" in result
        assert "transformation_applied" in result


class TestAdapterNodeProcessorIntegration:
    """Integration tests for AdapterNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = AdapterNodeProcessor(node, context)

        inputs = {
            "transformation_type": "field_mapping",
            "source_data": {"old": "value"},
            "transformation_config": {"mapping": {"old": "new"}},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "transformed_data" in result
        assert "transformation_applied" in result
