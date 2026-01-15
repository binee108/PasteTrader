"""TDD tests for DAGValidator service.

TAG: [SPEC-010] [TESTS] [DAG] [VALIDATOR]
REQ: REQ-010-B - Core Validation Service Interface

Test coverage for:
- validate_workflow()
- validate_edge_addition()
- validate_batch_edges()
- get_topology()
- check_cycle()
- Internal validation methods

Uses RED-GREEN-REFACTOR TDD cycle with comprehensive edge cases.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.enums import NodeType
from app.models.workflow import Edge, Node, Workflow
from app.schemas.validation import (
    CycleCheckResult,
    TopologyResult,
    ValidationErrorCode,
    ValidationLevel,
    ValidationOptions,
    ValidationResult,
    ValidationWarning,
)
from app.services.workflow.exceptions import (
    CycleDetectedError,
    InvalidNodeReferenceError,
)
from app.services.workflow.validator import DAGValidator


# =============================================================================
# Test Constants
# =============================================================================


class TestDAGValidator:
    """Test suite for DAGValidator using TDD approach."""

    # ========================================================================
    # validate_workflow() Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_workflow_success_basic(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED-GREEN-REFACTOR: Test basic successful workflow validation."""
        workflow_id = sample_workflow.id
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow_id)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.workflow_id == workflow_id
        assert result.node_count == 2
        assert result.edge_count == 1
        assert result.validated_at is not None
        assert result.validation_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_validate_workflow_with_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test validation detects cycles."""
        # Create cycle: trigger -> node -> trigger
        cycle_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_node.id,
            target_node_id=sample_trigger_node.id,
        )
        normal_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, cycle_edge, normal_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == ValidationErrorCode.CYCLE_DETECTED
        assert "cycle" in result.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_validate_workflow_not_found(self, db_session):
        """Test validation raises error for non-existent workflow."""
        validator = DAGValidator(db_session)

        with pytest.raises(InvalidNodeReferenceError):
            await validator.validate_workflow(uuid4())

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Database UNIQUE constraint prevents duplicate edge insertion"
    )
    async def test_validate_workflow_with_duplicate_edges(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test validation detects duplicate edges.

        NOTE: Skipped because SQLite UNIQUE constraint prevents duplicate edge insertion.
        Duplicate detection is tested through validate_edge_addition_duplicate_edge.
        """
        edge1 = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
            source_handle="output",
            target_handle="input",
        )
        edge2 = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
            source_handle="output",
            target_handle="input",
        )

        db_session.add_all([sample_trigger_node, sample_node, edge1, edge2])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.DUPLICATE_EDGE for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_no_trigger_node(self, db_session, sample_node):
        """Test validation fails when no trigger node exists."""
        workflow = Workflow(id=uuid4(), owner_id=uuid4(), name="Test", version=1)
        node = sample_node
        node.workflow_id = workflow.id
        node.node_type = NodeType.TOOL

        db_session.add_all([workflow, node])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.NO_TRIGGER_NODE for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_with_options_standard(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """Test validation with STANDARD level includes connectivity checks."""
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STANDARD)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        assert result.validation_level == ValidationLevel.STANDARD

    @pytest.mark.asyncio
    async def test_validate_workflow_with_topology(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """Test validation includes topology analysis."""
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        options = ValidationOptions(include_topology=True)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        assert result.topology is not None
        assert result.topology.total_levels > 0
        assert len(result.topology.execution_order) > 0

    @pytest.mark.asyncio
    async def test_validate_workflow_tool_node_without_tool_id(
        self, db_session, sample_workflow, sample_trigger_node
    ):
        """Test STRICT validation detects TOOL node without tool_id."""
        tool_node = Node(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            name="Invalid Tool",
            node_type=NodeType.TOOL,
            position_x=100,
            position_y=100,
            config={},
            tool_id=None,  # Missing tool_id
        )

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=tool_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, tool_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.INVALID_NODE_CONFIG
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_agent_node_without_agent_id(
        self, db_session, sample_workflow, sample_trigger_node
    ):
        """Test STRICT validation detects AGENT node without agent_id."""
        agent_node = Node(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            name="Invalid Agent",
            node_type=NodeType.AGENT,
            position_x=100,
            position_y=100,
            config={},
            agent_id=None,  # Missing agent_id
        )

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=agent_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, agent_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.INVALID_NODE_CONFIG
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_with_undefined_variables(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test STRICT validation detects undefined variable references."""
        # Node config references undefined variable
        sample_node.config = {"input": "{{undefined.variable}}"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should detect undefined variables
        assert any(
            error.code == ValidationErrorCode.UNDEFINED_VARIABLE
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_schema_mismatch(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test STRICT validation detects schema incompatibility."""
        # Incompatible schemas: string output vs integer input
        sample_trigger_node.output_schema = {"type": "string"}
        sample_node.input_schema = {"type": "integer"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should detect schema mismatch
        assert any(
            error.code == ValidationErrorCode.SCHEMA_MISMATCH for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_workflow_exceeds_node_limit(
        self, db_session, workflow_factory, node_factory
    ):
        """Test validation enforces node limit."""
        workflow = workflow_factory()
        nodes = [
            node_factory(
                workflow_id=workflow.id, node_type=NodeType.TRIGGER, name=f"Node{i}"
            )
            for i in range(10)
        ]

        db_session.add_all([workflow, *nodes])
        await db_session.flush()

        options = ValidationOptions(max_nodes=5)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id, options)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.GRAPH_TOO_LARGE for error in result.errors
        )
        assert result.errors[0].details["metric"] == "nodes"

    @pytest.mark.asyncio
    async def test_validate_workflow_exceeds_edge_limit(
        self, db_session, sample_workflow, sample_trigger_node, node_factory
    ):
        """Test validation enforces edge limit."""
        nodes = [node_factory(workflow_id=sample_workflow.id) for _ in range(6)]
        edges = []
        for i, node in enumerate(nodes):
            edges.append(
                Edge(
                    id=uuid4(),
                    workflow_id=sample_workflow.id,
                    source_node_id=sample_trigger_node.id,
                    target_node_id=node.id,
                )
            )

        db_session.add_all([sample_workflow, sample_trigger_node, *nodes, *edges])
        await db_session.flush()

        options = ValidationOptions(max_edges=3)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.GRAPH_TOO_LARGE for error in result.errors
        )
        assert result.errors[0].details["metric"] == "edges"

    # ========================================================================
    # validate_edge_addition() Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_edge_addition_success(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test successful edge addition validation."""
        db_session.add_all([sample_trigger_node, sample_node])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_edge_addition(
            sample_workflow.id,
            sample_trigger_node.id,
            sample_node.id,
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_edge_addition_self_loop(
        self, db_session, sample_workflow, sample_node
    ):
        """Test edge addition validation detects self-loops."""
        db_session.add_all([sample_workflow, sample_node])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_edge_addition(
            sample_workflow.id, sample_node.id, sample_node.id
        )

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == ValidationErrorCode.SELF_LOOP_DETECTED
        assert "self-loop" in result.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_validate_edge_addition_node_not_found(
        self, db_session, sample_workflow, sample_trigger_node
    ):
        """Test edge addition validation detects missing nodes."""
        db_session.add(sample_trigger_node)
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_edge_addition(
            sample_workflow.id, sample_trigger_node.id, uuid4()
        )

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.NODE_NOT_FOUND for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_edge_addition_would_create_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test edge addition validation detects cycles."""
        # Create A -> B, then try to add B -> A
        existing_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, existing_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_edge_addition(
            sample_workflow.id, sample_node.id, sample_trigger_node.id
        )

        assert result.is_valid is False
        assert result.errors[0].code == ValidationErrorCode.CYCLE_DETECTED

    @pytest.mark.asyncio
    async def test_validate_edge_addition_duplicate_edge(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test edge addition validation detects duplicate edges."""
        existing_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
            source_handle="output",
            target_handle="input",
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, existing_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_edge_addition(
            sample_workflow.id,
            sample_trigger_node.id,
            sample_node.id,
            "output",
            "input",
        )

        assert result.is_valid is False
        assert result.errors[0].code == ValidationErrorCode.DUPLICATE_EDGE

    # ========================================================================
    # validate_batch_edges() Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_batch_edges_success(
        self, db_session, sample_workflow, sample_trigger_node, node_factory
    ):
        """Test successful batch edge validation."""
        node1 = node_factory(workflow_id=sample_workflow.id)
        node2 = node_factory(workflow_id=sample_workflow.id)

        db_session.add_all([sample_workflow, sample_trigger_node, node1, node2])
        await db_session.flush()

        edges_data = [
            {
                "source_node_id": str(sample_trigger_node.id),
                "target_node_id": str(node1.id),
            },
            {
                "source_node_id": str(node1.id),
                "target_node_id": str(node2.id),
            },
        ]

        validator = DAGValidator(db_session)
        result = await validator.validate_batch_edges(sample_workflow.id, edges_data)

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_batch_edges_with_self_loop(
        self, db_session, sample_workflow, sample_trigger_node
    ):
        """Test batch validation detects self-loops."""
        db_session.add(sample_trigger_node)
        await db_session.flush()

        edges_data = [
            {
                "source_node_id": str(sample_trigger_node.id),
                "target_node_id": str(sample_trigger_node.id),
            },
        ]

        validator = DAGValidator(db_session)
        result = await validator.validate_batch_edges(sample_workflow.id, edges_data)

        assert result.is_valid is False
        assert any(
            error.code == ValidationErrorCode.SELF_LOOP_DETECTED
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_validate_batch_edges_with_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test batch validation detects cycles."""
        # Add trigger -> node edge, then try to add node -> trigger
        existing_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, existing_edge]
        )
        await db_session.flush()

        edges_data = [
            {
                "source_node_id": str(sample_node.id),
                "target_node_id": str(sample_trigger_node.id),
            },
        ]

        validator = DAGValidator(db_session)
        result = await validator.validate_batch_edges(sample_workflow.id, edges_data)

        assert result.is_valid is False
        assert result.errors[0].code == ValidationErrorCode.CYCLE_DETECTED

    # ========================================================================
    # get_topology() Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_topology_success(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """Test successful topology generation."""
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.get_topology(sample_workflow.id)

        assert isinstance(result, TopologyResult)
        assert result.total_levels > 0
        assert len(result.execution_order) > 0
        assert result.critical_path_length > 0

    @pytest.mark.asyncio
    async def test_get_topology_with_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test topology generation raises error for cycles."""
        cycle_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_node.id,
            target_node_id=sample_trigger_node.id,
        )
        normal_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, cycle_edge, normal_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        with pytest.raises(CycleDetectedError):
            await validator.get_topology(sample_workflow.id)

    @pytest.mark.asyncio
    async def test_get_topology_parallel_execution(
        self, db_session, sample_workflow, sample_trigger_node, node_factory
    ):
        """Test topology identifies parallel execution opportunities."""
        node1 = node_factory(workflow_id=sample_workflow.id)
        node2 = node_factory(workflow_id=sample_workflow.id)

        edge1 = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=node1.id,
        )
        edge2 = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=node2.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, node1, node2, edge1, edge2]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.get_topology(sample_workflow.id)

        # Node1 and node2 should be in same level (can execute in parallel)
        assert result.max_parallel_nodes >= 2

    # ========================================================================
    # check_cycle() Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_check_cycle_no_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """Test cycle check returns False for acyclic graph."""
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.check_cycle(sample_workflow.id)

        assert result.has_cycle is False
        assert result.cycle_path is None

    @pytest.mark.asyncio
    async def test_check_cycle_with_cycle(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test cycle check detects existing cycles."""
        cycle_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_node.id,
            target_node_id=sample_trigger_node.id,
        )
        normal_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, cycle_edge, normal_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.check_cycle(sample_workflow.id)

        assert result.has_cycle is True
        assert result.cycle_path is not None
        assert len(result.cycle_path) > 0
        assert "cycle" in result.cycle_description.lower()

    @pytest.mark.asyncio
    async def test_check_cycle_with_proposed_edge(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test cycle check with proposed edges."""
        existing_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, existing_edge]
        )
        await db_session.flush()

        proposed_edges = [
            {
                "source_node_id": str(sample_node.id),
                "target_node_id": str(sample_trigger_node.id),
            }
        ]

        validator = DAGValidator(db_session)
        result = await validator.check_cycle(sample_workflow.id, proposed_edges)

        assert result.has_cycle is True
        assert result.cycle_path is not None

    # ========================================================================
    # Warning Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_dead_end_warning(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test validation warns about dead-end nodes."""
        # Add edge from trigger to node
        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STANDARD)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should have warning for dead-end node
        assert len(result.warnings) > 0
        assert any(w.code == "DEAD_END_NODE" for w in result.warnings)

    # ========================================================================
    # Schema Compatibility Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_schemas_compatible_same_type(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test schema compatibility with same types."""
        sample_trigger_node.output_schema = {"type": "string"}
        sample_node.input_schema = {"type": "string"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should not have schema mismatch error
        assert not any(
            error.code == ValidationErrorCode.SCHEMA_MISMATCH for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_schemas_compatible_any_type(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test schema compatibility with 'any' type."""
        sample_trigger_node.output_schema = {"type": "any"}
        sample_node.input_schema = {"type": "string"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should not have schema mismatch error
        assert not any(
            error.code == ValidationErrorCode.SCHEMA_MISMATCH for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_schemas_compatible_number_to_integer(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test schema compatibility: number to integer."""
        sample_trigger_node.output_schema = {"type": "number"}
        sample_node.input_schema = {"type": "integer"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should not have schema mismatch error
        assert not any(
            error.code == ValidationErrorCode.SCHEMA_MISMATCH for error in result.errors
        )

    # ========================================================================
    # Private Method Tests (via public interface behavior)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_extract_variables_from_workflow(
        self, db_session, sample_workflow, sample_trigger_node
    ):
        """Test variable extraction from workflow config."""
        workflow = Workflow(
            id=sample_workflow.id,
            owner_id=uuid4(),
            name="Test",
            variables={"api_key": "secret", "environment": "prod"},
        )

        db_session.add_all([workflow, sample_trigger_node])
        await db_session.flush()

        validator = DAGValidator(db_session)
        # Variables are used in STRICT validation
        options = ValidationOptions(level=ValidationLevel.STRICT)
        result = await validator.validate_workflow(workflow.id, options)

        # Should validate without undefined variable errors
        assert not any(
            error.code == ValidationErrorCode.UNDEFINED_VARIABLE
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_find_undefined_variables_in_config(
        self, db_session, sample_workflow, sample_trigger_node, sample_node
    ):
        """Test detection of undefined variables in node config."""
        sample_node.config = {"output": "{{workflow.nonexistent_var}}"}

        edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_trigger_node.id,
            target_node_id=sample_node.id,
        )

        db_session.add_all([sample_workflow, sample_trigger_node, sample_node, edge])
        await db_session.flush()

        options = ValidationOptions(level=ValidationLevel.STRICT)
        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id, options)

        # Should detect undefined variable
        assert any(
            error.code == ValidationErrorCode.UNDEFINED_VARIABLE
            for error in result.errors
        )

    @pytest.mark.asyncio
    async def test_empty_workflow_validation(self, db_session, workflow_factory):
        """Test validation of empty workflow (no nodes)."""
        workflow = workflow_factory()
        db_session.add(workflow)
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id)

        # Empty workflow should have errors (no trigger node)
        assert result.is_valid is False
        assert result.node_count == 0
        assert result.edge_count == 0

    @pytest.mark.asyncio
    async def test_single_node_workflow(self, db_session, workflow_factory):
        """Test validation of single-node workflow."""
        workflow = workflow_factory()
        trigger_node = Node(
            id=uuid4(),
            workflow_id=workflow.id,
            name="Single Trigger",
            node_type=NodeType.TRIGGER,
            position_x=0,
            position_y=0,
            config={},
        )

        db_session.add_all([workflow, trigger_node])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(workflow.id)

        # Single trigger node should be valid
        assert result.is_valid is True
        assert result.node_count == 1

    @pytest.mark.asyncio
    async def test_complex_diamond_topology(
        self, db_session, sample_workflow, sample_trigger_node, node_factory
    ):
        """Test topology generation with diamond pattern."""
        node_a = node_factory(workflow_id=sample_workflow.id)
        node_b = node_factory(workflow_id=sample_workflow.id)
        node_c = node_factory(workflow_id=sample_workflow.id)

        # Diamond: trigger -> a, trigger -> b, a -> c, b -> c
        edges = [
            Edge(
                id=uuid4(),
                workflow_id=sample_workflow.id,
                source_node_id=sample_trigger_node.id,
                target_node_id=node_a.id,
            ),
            Edge(
                id=uuid4(),
                workflow_id=sample_workflow.id,
                source_node_id=sample_trigger_node.id,
                target_node_id=node_b.id,
            ),
            Edge(
                id=uuid4(),
                workflow_id=sample_workflow.id,
                source_node_id=node_a.id,
                target_node_id=node_c.id,
            ),
            Edge(
                id=uuid4(),
                workflow_id=sample_workflow.id,
                source_node_id=node_b.id,
                target_node_id=node_c.id,
            ),
        ]

        db_session.add_all([sample_trigger_node, node_a, node_b, node_c, *edges])
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.get_topology(sample_workflow.id)

        # Should have 3 levels: [trigger], [a, b], [c]
        assert result.total_levels == 3
        assert result.max_parallel_nodes == 2  # a and b can run in parallel
