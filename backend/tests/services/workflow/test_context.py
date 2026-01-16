"""Tests for ExecutionContext.

TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
REQ: REQ-011-003 - ExecutionContext for node data passing
"""

import pytest

from app.models.enums import NodeType
from app.models.workflow import Edge, Node
from app.services.workflow.context import ExecutionContext


class TestExecutionContextCreation:
    """Tests for ExecutionContext initialization.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
    """

    @pytest.mark.asyncio
    async def test_context_initialization(self) -> None:
        """Test creating ExecutionContext with workflow execution ID and input data.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        workflow_execution_id = uuid4()
        input_data = {"key1": "value1", "key2": 42}

        context = ExecutionContext(
            workflow_execution_id=workflow_execution_id, input_data=input_data
        )

        assert context.workflow_execution_id == workflow_execution_id
        assert await context.get_variable("key1") == "value1"
        assert await context.get_variable("key2") == 42


class TestVariableManagement:
    """Tests for workflow variable management.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
    """

    @pytest.mark.asyncio
    async def test_get_variable_existing(self) -> None:
        """Test getting an existing variable.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(
            workflow_execution_id=uuid4(), input_data={"var1": "test"}
        )

        value = await context.get_variable("var1")
        assert value == "test"

    @pytest.mark.asyncio
    async def test_get_variable_nonexistent(self) -> None:
        """Test getting a nonexistent variable returns None.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})

        value = await context.get_variable("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_set_variable(self) -> None:
        """Test setting a workflow variable.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})

        await context.set_variable("new_var", "new_value")
        value = await context.get_variable("new_var")
        assert value == "new_value"

    @pytest.mark.asyncio
    async def test_set_variable_overwrites(self) -> None:
        """Test that set_variable overwrites existing values.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(
            workflow_execution_id=uuid4(), input_data={"var1": "old"}
        )

        await context.set_variable("var1", "new")
        value = await context.get_variable("var1")
        assert value == "new"


class TestNodeInputOutput:
    """Tests for node input/output management.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
    """

    @pytest.mark.asyncio
    async def test_set_and_get_output(self) -> None:
        """Test setting and getting node output.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})
        node_id = uuid4()
        output_data = {"result": "success", "count": 10}

        await context.set_output(node_id, output_data)

        all_outputs = await context.get_all_outputs()
        assert node_id in all_outputs
        assert all_outputs[node_id] == output_data

    @pytest.mark.asyncio
    async def test_get_input_no_edges(self) -> None:
        """Test getting input for node with no incoming edges.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})
        node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            name="TestNode",
            node_type=NodeType.TOOL,
            position_x=0.0,
            position_y=0.0,
        )

        input_data = await context.get_input(node, [])
        assert input_data == {}

    @pytest.mark.asyncio
    async def test_get_input_with_predecessor_outputs(self) -> None:
        """Test getting input from predecessor node outputs.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})

        # Create predecessor nodes and edges
        node1_id = uuid4()
        node2_id = uuid4()
        target_node = Node(
            id=uuid4(),
            workflow_id=uuid4(),
            name="TargetNode",
            node_type=NodeType.TOOL,
            position_x=0.0,
            position_y=0.0,
        )

        # Set predecessor outputs
        await context.set_output(node1_id, {"data": "from_node1"})
        await context.set_output(node2_id, {"value": 42})

        # Create edges
        edge1 = Edge(
            id=uuid4(),
            workflow_id=uuid4(),
            source_node_id=node1_id,
            target_node_id=target_node.id,
        )
        edge2 = Edge(
            id=uuid4(),
            workflow_id=uuid4(),
            source_node_id=node2_id,
            target_node_id=target_node.id,
        )

        # Get input
        input_data = await context.get_input(target_node, [edge1, edge2])

        # Should contain merged outputs from both predecessors
        assert "data" in input_data
        assert input_data["data"] == "from_node1"
        assert "value" in input_data
        assert input_data["value"] == 42


class TestErrorHandling:
    """Tests for error recording and checking.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
    """

    @pytest.mark.asyncio
    async def test_add_error(self) -> None:
        """Test adding an error to the context.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})
        node_id = uuid4()

        await context.add_error(
            node_id=node_id, error_type="ExecutionError", message="Node failed"
        )

        assert context.has_errors() is True

    @pytest.mark.asyncio
    async def test_has_errors_no_errors(self) -> None:
        """Test has_errors returns False when no errors.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})

        assert context.has_errors() is False

    @pytest.mark.asyncio
    async def test_get_all_outputs_empty(self) -> None:
        """Test get_all_outputs returns empty dict when no outputs.

        TAG: [SPEC-011] [EXECUTION] [CONTEXT] [TEST]
        """
        from uuid import uuid4

        context = ExecutionContext(workflow_execution_id=uuid4(), input_data={})

        outputs = await context.get_all_outputs()
        assert outputs == {}
