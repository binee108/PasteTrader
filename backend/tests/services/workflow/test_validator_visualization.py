"""TDD tests for Visualization Hints in DAGValidator.

TAG: [SPEC-010] [TESTS] [DAG] [VISUALIZATION]
REQ: REQ-010-019 - Visualization Hints

Test coverage for:
- ValidationError includes node position (position_x, position_y)
- ValidationWarning includes node position (position_x, position_y)
- Cycle errors include coordinates
- Node configuration errors include coordinates
- Schema mismatch errors include coordinates
- Edge errors don't have position (edges don't have positions)

Uses RED-GREEN-REFACTOR TDD cycle.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.enums import NodeType
from app.models.workflow import Edge, Node, Workflow
from app.schemas.validation import (
    ValidationErrorCode,
    ValidationLevel,
    ValidationOptions,
)
from app.services.workflow.validator import DAGValidator


class TestVisualizationHints:
    """Test suite for visualization hints in validation errors.

    TAG: [SPEC-010] [TESTS] [VISUALIZATION]
    REQ: REQ-010-019 - Visualization Hints

    Tests that validation errors include node position information
    to help UI visualize where errors occur in the workflow graph.
    """

    # ========================================================================
    # Cycle Detection with Position
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cycle_error_includes_node_positions(
        self, db_session, workflow_factory
    ):
        """RED: Cycle error should include position_x and position_y.

        When a cycle is detected, the validation error should include
        the coordinates of all nodes in the cycle for UI visualization.
        """
        workflow = workflow_factory()

        # Create nodes with specific positions
        node_a = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Node A",
            node_type=NodeType.TRIGGER,
            position_x=100.0,
            position_y=200.0,
            config={},
        )

        node_b = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Node B",
            node_type=NodeType.TOOL,
            position_x=300.0,
            position_y=400.0,
            config={},
            tool_id=uuid4(),
        )

        # Create cycle: A -> B -> A
        edge_ab = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
        )

        edge_ba = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node_b.id,
            target_node_id=node_a.id,
        )

        db_session.add_all([workflow, node_a, node_b, edge_ab, edge_ba])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id)

        # Should have cycle error
        assert result.is_valid is False
        cycle_errors = [
            e for e in result.errors if e.code == ValidationErrorCode.CYCLE_DETECTED
        ]
        assert len(cycle_errors) == 1

        error = cycle_errors[0]

        # Check that position information is included in details
        assert "node_positions" in error.details
        positions = error.details["node_positions"]

        # Should have positions for both nodes
        assert str(node_a.id) in positions
        assert str(node_b.id) in positions

        # Check coordinates
        assert positions[str(node_a.id)] == {"x": 100.0, "y": 200.0}
        assert positions[str(node_b.id)] == {"x": 300.0, "y": 400.0}

    # ========================================================================
    # Node Configuration Errors with Position
    # ========================================================================

    @pytest.mark.asyncio
    async def test_tool_node_config_error_includes_position(
        self, db_session, workflow_factory
    ):
        """RED: Tool node without tool_id should include position.

        When a TOOL node is missing required tool_id, the error should
        include the node's position for UI visualization.
        """
        workflow = workflow_factory()

        trigger_node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Trigger",
            node_type=NodeType.TRIGGER,
            position_x=0.0,
            position_y=0.0,
            config={},
        )

        # Invalid tool node (missing tool_id) at specific position
        tool_node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Invalid Tool",
            node_type=NodeType.TOOL,
            position_x=500.0,
            position_y=600.0,
            config={},
            tool_id=None,  # Missing!
        )

        edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=trigger_node.id,
            target_node_id=tool_node.id,
        )

        db_session.add_all([workflow, trigger_node, tool_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id, options)

        # Should have config error
        assert result.is_valid is False
        config_errors = [
            e
            for e in result.errors
            if e.code == ValidationErrorCode.INVALID_NODE_CONFIG
        ]
        assert len(config_errors) == 1

        error = config_errors[0]

        # Check that position information is included
        assert "node_positions" in error.details
        positions = error.details["node_positions"]

        # Should have position for the invalid tool node
        assert str(tool_node.id) in positions
        assert positions[str(tool_node.id)] == {"x": 500.0, "y": 600.0}

    # ========================================================================
    # Schema Mismatch Errors with Position
    # ========================================================================

    @pytest.mark.asyncio
    async def test_schema_mismatch_includes_node_positions(
        self, db_session, workflow_factory
    ):
        """RED: Schema mismatch should include source and target positions.

        When schemas are incompatible, the error should include positions
        of both source and target nodes for UI visualization.
        """
        workflow = workflow_factory()

        source_node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Source",
            node_type=NodeType.TRIGGER,
            position_x=100.0,
            position_y=150.0,
            config={},
            output_schema={"type": "string"},
        )

        target_node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Target",
            node_type=NodeType.TOOL,
            position_x=700.0,
            position_y=800.0,
            config={},
            input_schema={"type": "integer"},  # Incompatible!
            tool_id=uuid4(),
        )

        edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=source_node.id,
            target_node_id=target_node.id,
        )

        db_session.add_all([workflow, source_node, target_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id, options)

        # Should have schema mismatch error
        assert result.is_valid is False
        schema_errors = [
            e for e in result.errors if e.code == ValidationErrorCode.SCHEMA_MISMATCH
        ]
        assert len(schema_errors) == 1

        error = schema_errors[0]

        # Check that position information is included for both nodes
        assert "node_positions" in error.details
        positions = error.details["node_positions"]

        # Should have positions for both source and target
        assert str(source_node.id) in positions
        assert str(target_node.id) in positions

        assert positions[str(source_node.id)] == {"x": 100.0, "y": 150.0}
        assert positions[str(target_node.id)] == {"x": 700.0, "y": 800.0}

    # ========================================================================
    # Multiple Errors with Positions
    # ========================================================================

    @pytest.mark.asyncio
    async def test_multiple_errors_include_respective_positions(
        self, db_session, workflow_factory
    ):
        """RED: Multiple errors should include their respective node positions.

        When multiple nodes have errors, each error should include
        the position information for its specific node(s).
        """
        workflow = workflow_factory()

        trigger = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Trigger",
            node_type=NodeType.TRIGGER,
            position_x=0.0,
            position_y=0.0,
            config={},
        )

        # Two invalid tool nodes at different positions
        tool1 = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Tool 1",
            node_type=NodeType.TOOL,
            position_x=100.0,
            position_y=200.0,
            config={},
            tool_id=None,  # Invalid
        )

        tool2 = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Tool 2",
            node_type=NodeType.TOOL,
            position_x=300.0,
            position_y=400.0,
            config={},
            tool_id=None,  # Invalid
        )

        edge1 = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=trigger.id,
            target_node_id=tool1.id,
        )

        edge2 = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=trigger.id,
            target_node_id=tool2.id,
        )

        db_session.add_all([workflow, trigger, tool1, tool2, edge1, edge2])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id, options)

        # Should have multiple config errors
        config_errors = [
            e
            for e in result.errors
            if e.code == ValidationErrorCode.INVALID_NODE_CONFIG
        ]
        assert len(config_errors) == 2

        # Each error should have positions
        for error in config_errors:
            assert "node_positions" in error.details
            positions = error.details["node_positions"]
            assert len(positions) > 0

            # Verify position format
            for node_id, pos in positions.items():
                assert "x" in pos
                assert "y" in pos
                assert isinstance(pos["x"], float)
                assert isinstance(pos["y"], float)

    # ========================================================================
    # Edge Addition Errors with Node Positions
    # ========================================================================

    @pytest.mark.asyncio
    async def test_edge_addition_cycle_includes_positions(
        self, db_session, workflow_factory
    ):
        """RED: Edge addition cycle error should include node positions.

        When validating edge addition that would create a cycle,
        the error should include positions of all nodes in the cycle.
        """
        workflow = workflow_factory()

        node_a = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Node A",
            node_type=NodeType.TRIGGER,
            position_x=50.0,
            position_y=100.0,
            config={},
        )

        node_b = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Node B",
            node_type=NodeType.TOOL,
            position_x=250.0,
            position_y=350.0,
            config={},
            tool_id=uuid4(),
        )

        # Existing edge: A -> B
        existing_edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
        )

        db_session.add_all([workflow, node_a, node_b, existing_edge])
        await db_session.flush()

        validator = DAGValidator(db_session)

        # Try to add B -> A (would create cycle)
        result = await validator.validate_edge_addition(
            workflow.id, node_b.id, node_a.id
        )

        assert result.is_valid is False
        cycle_errors = [
            e for e in result.errors if e.code == ValidationErrorCode.CYCLE_DETECTED
        ]
        assert len(cycle_errors) == 1

        error = cycle_errors[0]

        # Check positions
        assert "node_positions" in error.details
        positions = error.details["node_positions"]

        assert str(node_a.id) in positions
        assert str(node_b.id) in positions

        assert positions[str(node_a.id)] == {"x": 50.0, "y": 100.0}
        assert positions[str(node_b.id)] == {"x": 250.0, "y": 350.0}

    # ========================================================================
    # Self-Loop Error with Position
    # ========================================================================

    @pytest.mark.asyncio
    async def test_self_loop_error_includes_position(
        self, db_session, workflow_factory
    ):
        """RED: Self-loop error should include the node's position.

        When a self-loop is detected, the error should include
        the position of the node attempting to connect to itself.
        """
        workflow = workflow_factory()

        node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Self Loop Node",
            node_type=NodeType.TOOL,
            position_x=999.0,
            position_y=888.0,
            config={},
            tool_id=uuid4(),
        )

        db_session.add_all([workflow, node])
        await db_session.flush()

        validator = DAGValidator(db_session)

        # Try to add self-loop
        result = await validator.validate_edge_addition(
            workflow.id, node.id, node.id
        )

        assert result.is_valid is False
        loop_errors = [
            e for e in result.errors if e.code == ValidationErrorCode.SELF_LOOP_DETECTED
        ]
        assert len(loop_errors) == 1

        error = loop_errors[0]

        # Check position
        assert "node_positions" in error.details
        positions = error.details["node_positions"]

        assert str(node.id) in positions
        assert positions[str(node.id)] == {"x": 999.0, "y": 888.0}

    # ========================================================================
    # Warnings with Position
    # ========================================================================

    @pytest.mark.asyncio
    async def test_dead_end_warning_includes_position(
        self, db_session, workflow_factory
    ):
        """RED: Dead-end warning should include node position.

        When a node has no outgoing edges, the warning should include
        its position for UI visualization.
        """
        workflow = workflow_factory()

        trigger = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Trigger",
            node_type=NodeType.TRIGGER,
            position_x=0.0,
            position_y=0.0,
            config={},
        )

        dead_end = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Dead End",
            node_type=NodeType.TOOL,
            position_x=400.0,
            position_y=500.0,
            config={},
            tool_id=uuid4(),
        )

        edge = Edge(
            id=uuid4(),
            workflow_id=workflow.id,
            source_node_id=trigger.id,
            target_node_id=dead_end.id,
        )

        db_session.add_all([workflow, trigger, dead_end, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STANDARD)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id, options)

        # Should have dead-end warning
        dead_end_warnings = [w for w in result.warnings if w.code == "DEAD_END_NODE"]
        assert len(dead_end_warnings) > 0

        warning = dead_end_warnings[0]

        # Check that warning includes position
        assert hasattr(warning, "position_x")
        assert hasattr(warning, "position_y")

        # The warning should be for the dead_end node
        assert warning.position_x == 400.0
        assert warning.position_y == 500.0
