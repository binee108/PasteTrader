"""Tests for ConditionNodeProcessor.

TAG: [SPEC-012] [PROCESSOR] [TEST] [CONDITION]
REQ: REQ-012-012 - Condition evaluation and branching
"""

import pytest
from uuid import uuid4

from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.condition import ConditionNodeProcessor
from app.services.workflow.processors.errors import ProcessorValidationError
from app.schemas.processors import ConditionProcessorInput, ConditionExpression


class MockNode:
    """Mock node for testing."""

    def __init__(self, node_type: str = "condition"):
        self.id = uuid4()
        self.node_type = node_type
        self.config = {}


class TestConditionNodeProcessorPreProcess:
    """Test ConditionNodeProcessor pre_process method."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self):
        """Test pre_process validates correct input."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        conditions = [
            ConditionExpression(
                name="high_value",
                expression="data.value > 100",
                target_node="node-a",
            )
        ]

        inputs = {
            "conditions": [c.model_dump() for c in conditions],
            "evaluation_context": {"data": {"value": 150}},
        }

        result = await processor.pre_process(inputs)

        assert isinstance(result, ConditionProcessorInput)
        assert len(result.conditions) == 1
        assert result.conditions[0].name == "high_value"

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self):
        """Test pre_process raises on missing conditions."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        inputs = {
            "evaluation_context": {},
        }

        with pytest.raises(ProcessorValidationError):
            await processor.pre_process(inputs)


class TestConditionNodeProcessorProcess:
    """Test ConditionNodeProcessor process method."""

    @pytest.mark.asyncio
    async def test_selects_first_matching_condition(self):
        """Test process selects first condition that evaluates true."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        conditions = [
            ConditionExpression(
                name="low_value",
                expression="data.value < 50",
                target_node="node-a",
            ),
            ConditionExpression(
                name="high_value",
                expression="data.value > 100",
                target_node="node-b",
            ),
        ]

        validated_input = ConditionProcessorInput(
            conditions=conditions,
            evaluation_context={"data": {"value": 150}},
        )

        result = await processor.process(validated_input)

        assert result.selected_branch == "high_value"
        assert result.target_node == "node-b"

    @pytest.mark.asyncio
    async def test_evaluates_all_conditions(self):
        """Test process evaluates all conditions."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        conditions = [
            ConditionExpression(
                name="condition_a",
                expression="data.x > 0",
                target_node="node-a",
            ),
            ConditionExpression(
                name="condition_b",
                expression="data.y < 0",
                target_node="node-b",
            ),
        ]

        validated_input = ConditionProcessorInput(
            conditions=conditions,
            evaluation_context={"data": {"x": 10, "y": -5}},
        )

        result = await processor.process(validated_input)

        assert len(result.evaluated_conditions) == 2


class TestConditionNodeProcessorPostProcess:
    """Test ConditionNodeProcessor post_process method."""

    @pytest.mark.asyncio
    async def test_post_process_serializes_output(self):
        """Test post_process returns dict."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        from app.schemas.processors import ConditionProcessorOutput

        output = ConditionProcessorOutput(
            selected_branch="test_branch",
            target_node="node-a",
            evaluated_conditions=[],
        )

        result = await processor.post_process(output)

        assert isinstance(result, dict)
        assert "selected_branch" in result
        assert "target_node" in result


class TestConditionNodeProcessorIntegration:
    """Integration tests for ConditionNodeProcessor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self):
        """Test complete execute flow."""
        node = MockNode()
        context = ExecutionContext(execution_id=uuid4())
        processor = ConditionNodeProcessor(node, context)

        conditions = [
            ConditionExpression(
                name="active",
                expression="status == 'active'",
                target_node="process-node",
            )
        ]

        inputs = {
            "conditions": [c.model_dump() for c in conditions],
            "evaluation_context": {"status": "active"},
        }

        result = await processor.execute(inputs)

        assert isinstance(result, dict)
        assert "selected_branch" in result
        assert "target_node" in result
