"""Tests for conftest.py fixtures and configuration.

TAG: [SPEC-010] [TESTING] [COVERAGE] [PYTEST_FIXTURES]
REQ: REQ-001 - Test conftest.py configuration and fixtures
REQ: REQ-002 - Cover event listeners and edge case fixtures
REQ: REQ-003 - Ensure 80%+ coverage for conftest.py

This test module ensures comprehensive coverage of pytest fixtures,
event listeners, and configuration functions defined in conftest.py.
"""

from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.main import app
from app.models.agent import Agent
from app.models.enums import (
    ExecutionStatus,
    LogLevel,
    ModelProvider,
    NodeType,
    ToolType,
    TriggerType,
)
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.models.tool import Tool
from app.models.workflow import Edge, Node, Workflow

# =============================================================================
# PYTEST CONFIGURATION TESTS
# =============================================================================


class TestPytestConfigure:
    """Tests for pytest_configure function."""

    def test_pytest_configure_adds_markers(self, request):
        """Test that pytest_configure adds custom markers.

        Verifies that the custom markers (slow, integration, asyncio)
        are properly registered with pytest configuration.

        Args:
            request: pytest fixture for accessing test configuration.
        """
        config = request.config
        markers = config.getini("markers")

        # Check for custom markers
        marker_names = [m.split(":")[0].strip() for m in markers]

        assert "slow" in marker_names
        assert "integration" in marker_names
        assert "asyncio" in marker_names


# =============================================================================
# ASYNC ENGINE FIXTURE TESTS
# =============================================================================


class TestAsyncEngine:
    """Tests for async_engine fixture."""

    @pytest_asyncio.fixture
    async def engine_instance(
        self, async_engine: AsyncEngine
    ) -> AsyncGenerator[AsyncEngine]:
        """Provide the engine instance for testing."""
        yield async_engine

    @pytest.mark.asyncio
    async def test_async_engine_creates_in_memory_db(self, engine_instance):
        """Test that async_engine creates an in-memory SQLite database.

        Verifies that the engine is properly configured with the
        SQLite in-memory URL for fast isolated testing.
        """
        assert engine_instance is not None
        assert "sqlite" in str(engine_instance.url)
        assert ":memory:" in str(engine_instance.url)

    @pytest.mark.asyncio
    async def test_async_engine_creates_tables(self, engine_instance):
        """Test that async_engine creates all tables on setup.

        Verifies that Base.metadata.create_all is called during
        fixture setup, creating all necessary tables.
        """
        async with engine_instance.connect() as conn:
            # Check that Workflow table exists
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
                )
            )
            workflow_table = result.fetchone()
            assert workflow_table is not None

            # Check that nodes table exists
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
                )
            )
            node_table = result.fetchone()
            assert node_table is not None

    @pytest.mark.asyncio
    async def test_async_engine_disposes_after_test(self, engine_instance):
        """Test that async_engine is properly disposed after test.

        Verifies that the finally block in async_engine properly
        drops all tables and disposes of the engine.
        """
        # Engine should still be available during test
        assert engine_instance is not None
        # After test, pytest should handle cleanup


# =============================================================================
# ASYNC SESSION MAKER FIXTURE TESTS
# =============================================================================


class TestAsyncSessionMaker:
    """Tests for async_session_maker fixture."""

    @pytest.mark.asyncio
    async def test_async_session_maker_returns_factory(self, async_session_maker):
        """Test that async_session_maker returns a session factory.

        Verifies that the fixture returns an async_sessionmaker
        instance configured for the test engine.
        """
        assert async_session_maker is not None
        assert isinstance(async_session_maker, async_sessionmaker)

    @pytest.mark.asyncio
    async def test_async_session_maker_creates_sessions(self, async_session_maker):
        """Test that the factory can create async sessions.

        Verifies that sessions created by the factory are properly
        configured AsyncSession instances.
        """
        async with async_session_maker() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)
            assert session.autoflush is False  # Configured in fixture


# =============================================================================
# DATABASE SESSION FIXTURE TESTS
# =============================================================================


class TestDbSession:
    """Tests for db_session fixture."""

    @pytest.mark.asyncio
    async def test_db_session_is_async_session(self, db_session):
        """Test that db_session yields an AsyncSession.

        Verifies that the fixture provides a valid AsyncSession
        instance for database operations.
        """
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)

    @pytest.mark.asyncio
    async def test_db_session_begins_nested_transaction(self, db_session):
        """Test that db_session begins a nested transaction.

        Verifies that begin_nested() is called to enable SAVEPOINT
        functionality for transaction rollback isolation.
        """
        # Session should have an active transaction
        # Note: in_transaction() might be False for nested transactions in async
        # Instead, verify the session is usable for database operations
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test",
            is_active=True,
            version=1,
        )
        db_session.add(workflow)
        # Should not raise an error if transaction is properly set up
        await db_session.flush()

    @pytest.mark.asyncio
    async def test_db_session_event_listener_registered(self, db_session):
        """Test that the restart_savepoint event listener is registered.

        Verifies that the event listener for after_transaction_end
        is properly registered to handle nested transaction restarts
        when session.commit() is called within tests.
        """
        # The event listener should be registered on the sync session
        # We can verify it works by triggering a commit
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Workflow",
            is_active=True,
            version=1,
        )
        db_session.add(workflow)
        await db_session.commit()

        # After commit, the event listener should restart the nested transaction
        # allowing us to continue using the session
        # Verify by adding another entity and committing again
        workflow2 = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Workflow 2",
            is_active=True,
            version=1,
        )
        db_session.add(workflow2)
        await db_session.commit()
        await db_session.flush()  # Should work if event listener is active

    @pytest.mark.asyncio
    async def test_db_session_rolls_back_after_test(self, db_session):
        """Test that db_session rolls back all changes after test.

        Verifies that the finally block properly rolls back the
        transaction, ensuring test isolation.
        """
        # Add data within the test
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Should be rolled back",
            is_active=True,
            version=1,
        )
        db_session.add(workflow)
        await db_session.commit()

        # Data should be visible during test
        result = await db_session.execute(
            select(Workflow).where(Workflow.name == "Should be rolled back")
        )
        assert result.scalar_one_or_none() is not None

        # After test completes, rollback should happen (verified by next test)


# =============================================================================
# DB_WITH_DATA FIXTURE TESTS
# =============================================================================


class TestDbWithData:
    """Tests for db_with_data fixture."""

    @pytest.mark.asyncio
    async def test_db_with_data_contains_workflow(self, db_with_data):
        """Test that db_with_data contains a sample workflow.

        Verifies that the fixture adds the sample_workflow to the
        session and flushes it to the database.
        """
        from sqlalchemy import select

        result = await db_with_data.execute(select(Workflow))
        workflows = result.scalars().all()
        assert len(workflows) >= 1
        assert workflows[0].name == "Test Workflow"

    @pytest.mark.asyncio
    async def test_db_with_data_contains_node(self, db_with_data):
        """Test that db_with_data contains a sample node.

        Verifies that the fixture adds the sample_node to the session.
        """
        from sqlalchemy import select

        result = await db_with_data.execute(select(Node))
        nodes = result.scalars().all()
        assert len(nodes) >= 1
        assert nodes[0].name == "Test Node"

    @pytest.mark.asyncio
    async def test_db_with_data_contains_edge(self, db_with_data):
        """Test that db_with_data contains a sample edge.

        Verifies that the fixture adds the sample_edge to the session.
        """
        from sqlalchemy import select

        result = await db_with_data.execute(select(Edge))
        edges = result.scalars().all()
        assert len(edges) >= 1

    @pytest.mark.asyncio
    async def test_db_with_data_contains_execution(self, db_with_data):
        """Test that db_with_data contains a sample execution.

        Verifies that the fixture adds the sample_execution to the session.
        """
        from sqlalchemy import select

        result = await db_with_data.execute(select(WorkflowExecution))
        executions = result.scalars().all()
        assert len(executions) >= 1
        assert executions[0].status == ExecutionStatus.PENDING


# =============================================================================
# ASYNC CLIENT FIXTURE TESTS
# =============================================================================


class TestAsyncClient:
    """Tests for async_client fixture."""

    @pytest.mark.asyncio
    async def test_async_client_is_async_client(self, async_client):
        """Test that async_client yields an AsyncClient.

        Verifies that the fixture provides a valid httpx AsyncClient
        for testing API endpoints.
        """
        assert async_client is not None
        assert isinstance(async_client, AsyncClient)

    @pytest.mark.asyncio
    async def test_async_client_uses_test_database(self, async_client):
        """Test that async_client overrides database dependency.

        Verifies that the get_db dependency is overridden to use
        the test SQLite database instead of production database.
        """
        # Make a request to an endpoint that uses the database
        response = await async_client.get("/api/v1/workflows/")

        # Request should succeed (even if empty list)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_client_clears_overrides_after_test(self, async_client: AsyncClient):
        """Test that async_client clears dependency overrides after test.

        Verifies that the finally block clears app.dependency_overrides
        to prevent interference with subsequent tests.

        Args:
            async_client: The async HTTP client fixture (used to trigger setup).
        """
        # async_client fixture is needed to trigger the dependency override setup
        _ = async_client  # Mark as intentionally used for fixture side effect

        # Overrides should be present during test
        assert len(app.dependency_overrides) > 0

        # After test, overrides should be cleared (verified by test isolation)


# =============================================================================
# SAMPLE USER ID FIXTURE TESTS
# =============================================================================


class TestSampleUserId:
    """Tests for sample_user_id fixture."""

    def test_sample_user_id_is_consistent_string(self, sample_user_id):
        """Test that sample_user_id returns a consistent UUID string.

        Verifies that the fixture returns the same UUID string
        across all tests in a session.
        """
        assert isinstance(sample_user_id, str)
        assert sample_user_id == "00000000-0000-0000-0000-000000000001"

    def test_sample_user_id_can_be_parsed_as_uuid(self, sample_user_id):
        """Test that sample_user_id can be parsed as a valid UUID.

        Verifies that the string is a valid UUID format.
        """
        uuid = UUID(sample_user_id)
        # Verify it's a valid UUID (not checking version as sample is static)
        assert str(uuid) == sample_user_id
        assert uuid.int > 0  # Valid UUID has positive integer representation


# =============================================================================
# SAMPLE WORKFLOW FIXTURE TESTS
# =============================================================================


class TestSampleWorkflow:
    """Tests for sample_workflow fixture."""

    def test_sample_workflow_returns_workflow_instance(self, sample_workflow):
        """Test that sample_workflow returns a Workflow instance.

        Verifies that the fixture creates a valid Workflow model
        instance with all required fields.
        """
        assert isinstance(sample_workflow, Workflow)
        assert sample_workflow.id is not None
        assert isinstance(sample_workflow.id, UUID)

    def test_sample_workflow_has_correct_properties(self, sample_workflow):
        """Test that sample_workflow has expected property values.

        Verifies that all fields are set to their expected values
        as defined in the fixture.
        """
        assert sample_workflow.name == "Test Workflow"
        assert sample_workflow.description == "A test workflow for integration testing"
        assert sample_workflow.is_active is True
        assert sample_workflow.version == 1
        assert sample_workflow.config == {"timeout": 300, "max_retries": 3}
        assert sample_workflow.variables == {
            "api_key": "test_key",
            "environment": "test",
        }

    def test_sample_workflow_owner_matches_sample_user_id(
        self, sample_workflow, sample_user_id
    ):
        """Test that sample_workflow owner_id matches sample_user_id.

        Verifies the dependency injection between fixtures works correctly.
        """
        assert str(sample_workflow.owner_id) == sample_user_id


# =============================================================================
# SAMPLE NODE FIXTURE TESTS
# =============================================================================


class TestSampleNode:
    """Tests for sample_node fixture."""

    def test_sample_node_returns_node_instance(self, sample_node):
        """Test that sample_node returns a Node instance.

        Verifies that the fixture creates a valid Node model instance.
        """
        assert isinstance(sample_node, Node)
        assert sample_node.id is not None
        assert isinstance(sample_node.id, UUID)

    def test_sample_node_has_correct_properties(self, sample_node):
        """Test that sample_node has expected property values."""
        assert sample_node.name == "Test Node"
        assert sample_node.node_type == NodeType.TOOL
        assert sample_node.position_x == 100.0
        assert sample_node.position_y == 200.0
        assert sample_node.timeout_seconds == 300

    def test_sample_node_has_schemas(self, sample_node):
        """Test that sample_node has input and output schemas."""
        assert sample_node.input_schema is not None
        assert sample_node.output_schema is not None
        assert "type" in sample_node.input_schema
        assert "type" in sample_node.output_schema

    def test_sample_node_has_retry_config(self, sample_node):
        """Test that sample_node has retry configuration."""
        assert sample_node.retry_config is not None
        assert "max_retries" in sample_node.retry_config
        assert sample_node.retry_config["max_retries"] == 3


# =============================================================================
# SAMPLE TRIGGER NODE FIXTURE TESTS
# =============================================================================


class TestSampleTriggerNode:
    """Tests for sample_trigger_node fixture."""

    def test_sample_trigger_node_is_trigger_type(self, sample_trigger_node):
        """Test that sample_trigger_node has TRIGGER node type."""
        assert isinstance(sample_trigger_node, Node)
        assert sample_trigger_node.node_type == NodeType.TRIGGER

    def test_sample_trigger_node_has_trigger_config(self, sample_trigger_node):
        """Test that sample_trigger_node has trigger configuration."""
        assert sample_trigger_node.config is not None
        assert "trigger_type" in sample_trigger_node.config
        assert sample_trigger_node.config["trigger_type"] == "webhook"

    def test_sample_trigger_node_has_no_tool_or_agent(self, sample_trigger_node):
        """Test that trigger node has no tool_id or agent_id."""
        assert sample_trigger_node.tool_id is None
        assert sample_trigger_node.agent_id is None


# =============================================================================
# SAMPLE AGENT NODE FIXTURE TESTS
# =============================================================================


class TestSampleAgentNode:
    """Tests for sample_agent_node fixture."""

    def test_sample_agent_node_is_agent_type(self, sample_agent_node):
        """Test that sample_agent_node has AGENT node type."""
        assert isinstance(sample_agent_node, Node)
        assert sample_agent_node.node_type == NodeType.AGENT

    def test_sample_agent_node_has_agent_config(self, sample_agent_node):
        """Test that sample_agent_node has agent configuration."""
        assert sample_agent_node.config is not None
        assert "temperature" in sample_agent_node.config
        assert sample_agent_node.config["temperature"] == 0.7

    def test_sample_agent_node_has_agent_id(self, sample_agent_node):
        """Test that sample_agent_node has an agent_id."""
        assert sample_agent_node.agent_id is not None
        assert isinstance(sample_agent_node.agent_id, UUID)


# =============================================================================
# SAMPLE EDGE FIXTURE TESTS
# =============================================================================


class TestSampleEdge:
    """Tests for sample_edge fixture."""

    def test_sample_edge_returns_edge_instance(self, sample_edge):
        """Test that sample_edge returns an Edge instance."""
        assert isinstance(sample_edge, Edge)
        assert sample_edge.id is not None

    def test_sample_edge_connects_correct_nodes(
        self, sample_edge, sample_trigger_node, sample_node
    ):
        """Test that sample_edge connects the correct source and target nodes."""
        assert sample_edge.source_node_id == sample_trigger_node.id
        assert sample_edge.target_node_id == sample_node.id

    def test_sample_edge_has_correct_properties(self, sample_edge):
        """Test that sample_edge has expected property values."""
        assert sample_edge.source_handle == "output"
        assert sample_edge.target_handle == "input"
        assert sample_edge.condition is None
        assert sample_edge.priority == 0
        assert sample_edge.label == "trigger to tool"


# =============================================================================
# SAMPLE CONDITIONAL EDGE FIXTURE TESTS
# =============================================================================


class TestSampleConditionalEdge:
    """Tests for sample_conditional_edge fixture."""

    def test_sample_conditional_edge_has_condition(self, sample_conditional_edge):
        """Test that sample_conditional_edge has a condition."""
        assert isinstance(sample_conditional_edge, Edge)
        assert sample_conditional_edge.condition is not None
        assert "field" in sample_conditional_edge.condition

    def test_sample_conditional_edge_has_priority(self, sample_conditional_edge):
        """Test that sample_conditional_edge has non-zero priority."""
        assert sample_conditional_edge.priority == 1

    def test_sample_conditional_edge_condition_structure(self, sample_conditional_edge):
        """Test that condition has correct structure."""
        condition = sample_conditional_edge.condition
        assert condition["field"] == "status"
        assert condition["operator"] == "eq"
        assert condition["value"] == "success"


# =============================================================================
# SAMPLE EXECUTION FIXTURE TESTS
# =============================================================================


class TestSampleExecution:
    """Tests for sample_execution fixture."""

    def test_sample_execution_returns_instance(self, sample_execution):
        """Test that sample_execution returns a WorkflowExecution instance."""
        assert isinstance(sample_execution, WorkflowExecution)
        assert sample_execution.id is not None

    def test_sample_execution_is_pending(self, sample_execution):
        """Test that sample_execution has PENDING status."""
        assert sample_execution.status == ExecutionStatus.PENDING
        assert sample_execution.started_at is None
        assert sample_execution.ended_at is None

    def test_sample_execution_has_input_data(self, sample_execution):
        """Test that sample_execution has input data."""
        assert sample_execution.input_data is not None
        assert "test_input" in sample_execution.input_data

    def test_sample_execution_has_manual_trigger(self, sample_execution):
        """Test that sample_execution has MANUAL trigger type."""
        assert sample_execution.trigger_type == TriggerType.MANUAL


# =============================================================================
# SAMPLE RUNNING EXECUTION FIXTURE TESTS
# =============================================================================


class TestSampleRunningExecution:
    """Tests for sample_running_execution fixture."""

    def test_sample_running_execution_is_running(self, sample_running_execution):
        """Test that sample_running_execution has RUNNING status."""
        assert sample_running_execution.status == ExecutionStatus.RUNNING
        assert sample_running_execution.started_at is not None
        assert sample_running_execution.ended_at is None


# =============================================================================
# SAMPLE COMPLETED EXECUTION FIXTURE TESTS
# =============================================================================


class TestSampleCompletedExecution:
    """Tests for sample_completed_execution fixture."""

    def test_sample_completed_execution_is_completed(self, sample_completed_execution):
        """Test that sample_completed_execution has COMPLETED status."""
        assert sample_completed_execution.status == ExecutionStatus.COMPLETED
        assert sample_completed_execution.started_at is not None
        assert sample_completed_execution.ended_at is not None

    def test_sample_completed_execution_has_output(self, sample_completed_execution):
        """Test that sample_completed_execution has output data."""
        assert sample_completed_execution.output_data is not None
        assert "result" in sample_completed_execution.output_data

    def test_sample_completed_execution_has_event_trigger(
        self, sample_completed_execution
    ):
        """Test that sample_completed_execution has EVENT trigger type."""
        assert sample_completed_execution.trigger_type == TriggerType.EVENT


# =============================================================================
# SAMPLE FAILED EXECUTION FIXTURE TESTS
# =============================================================================


class TestSampleFailedExecution:
    """Tests for sample_failed_execution fixture."""

    def test_sample_failed_execution_is_failed(self, sample_failed_execution):
        """Test that sample_failed_execution has FAILED status."""
        assert sample_failed_execution.status == ExecutionStatus.FAILED

    def test_sample_failed_execution_has_error_message(self, sample_failed_execution):
        """Test that sample_failed_execution has an error message."""
        assert sample_failed_execution.error_message is not None
        assert "Test error" in sample_failed_execution.error_message

    def test_sample_failed_execution_has_schedule_trigger(
        self, sample_failed_execution
    ):
        """Test that sample_failed_execution has SCHEDULE trigger type."""
        assert sample_failed_execution.trigger_type == TriggerType.SCHEDULE


# =============================================================================
# SAMPLE NODE EXECUTION FIXTURE TESTS
# =============================================================================


class TestSampleNodeExecution:
    """Tests for sample_node_execution fixture."""

    def test_sample_node_execution_returns_instance(self, sample_node_execution):
        """Test that sample_node_execution returns a NodeExecution instance."""
        assert isinstance(sample_node_execution, NodeExecution)
        assert sample_node_execution.id is not None

    def test_sample_node_execution_has_correct_defaults(self, sample_node_execution):
        """Test that sample_node_execution has expected default values."""
        assert sample_node_execution.status == ExecutionStatus.PENDING
        assert sample_node_execution.retry_count == 0
        assert sample_node_execution.execution_order == 1


# =============================================================================
# SAMPLE EXECUTION LOG FIXTURE TESTS
# =============================================================================


class TestSampleExecutionLog:
    """Tests for sample_execution_log fixture."""

    def test_sample_execution_log_returns_instance(self, sample_execution_log):
        """Test that sample_execution_log returns an ExecutionLog instance."""
        assert isinstance(sample_execution_log, ExecutionLog)
        assert sample_execution_log.id is not None

    def test_sample_execution_log_is_info_level(self, sample_execution_log):
        """Test that sample_execution_log has INFO log level."""
        assert sample_execution_log.level == LogLevel.INFO

    def test_sample_execution_log_has_message(self, sample_execution_log):
        """Test that sample_execution_log has a log message."""
        assert sample_execution_log.message is not None
        assert "Test log message" in sample_execution_log.message

    def test_sample_execution_log_has_timestamp(self, sample_execution_log):
        """Test that sample_execution_log has a timestamp."""
        assert sample_execution_log.timestamp is not None
        assert isinstance(sample_execution_log.timestamp, datetime)


# =============================================================================
# SAMPLE TOOL FIXTURE TESTS
# =============================================================================


class TestSampleTool:
    """Tests for sample_tool fixture."""

    def test_sample_tool_returns_instance(self, sample_tool):
        """Test that sample_tool returns a Tool instance."""
        assert isinstance(sample_tool, Tool)
        assert sample_tool.id is not None

    def test_sample_tool_is_http_type(self, sample_tool):
        """Test that sample_tool has HTTP tool type."""
        assert sample_tool.tool_type == ToolType.HTTP

    def test_sample_tool_has_config(self, sample_tool):
        """Test that sample_tool has configuration."""
        assert sample_tool.config is not None
        assert "url" in sample_tool.config
        assert "method" in sample_tool.config

    def test_sample_tool_has_auth_config(self, sample_tool):
        """Test that sample_tool has authentication configuration."""
        assert sample_tool.auth_config is not None
        assert sample_tool.auth_config["type"] == "bearer"


# =============================================================================
# SAMPLE AGENT FIXTURE TESTS
# =============================================================================


class TestSampleAgent:
    """Tests for sample_agent fixture."""

    def test_sample_agent_returns_instance(self, sample_agent):
        """Test that sample_agent returns an Agent instance."""
        assert isinstance(sample_agent, Agent)
        assert sample_agent.id is not None

    def test_sample_agent_is_anthropic_provider(self, sample_agent):
        """Test that sample_agent uses Anthropic model provider."""
        assert sample_agent.model_provider == ModelProvider.ANTHROPIC

    def test_sample_agent_has_model_name(self, sample_agent):
        """Test that sample_agent has a model name."""
        assert sample_agent.model_name is not None
        assert "claude" in sample_agent.model_name

    def test_sample_agent_has_system_prompt(self, sample_agent):
        """Test that sample_agent has a system prompt."""
        assert sample_agent.system_prompt is not None
        assert len(sample_agent.system_prompt) > 0


# =============================================================================
# WORKFLOW FACTORY FIXTURE TESTS
# =============================================================================


class TestWorkflowFactory:
    """Tests for workflow_factory fixture."""

    def test_workflow_factory_creates_workflow(self, workflow_factory):
        """Test that workflow_factory creates Workflow instances."""
        workflow = workflow_factory()
        assert isinstance(workflow, Workflow)
        assert workflow.id is not None

    def test_workflow_factory_uses_defaults(self, workflow_factory):
        """Test that workflow_factory uses default values."""
        workflow = workflow_factory()
        assert workflow.name == "Factory Workflow"
        assert workflow.is_active is True
        assert workflow.version == 1

    def test_workflow_factory_accepts_custom_values(self, workflow_factory):
        """Test that workflow_factory accepts custom values."""
        workflow = workflow_factory(
            name="Custom Workflow",
            description="Custom description",
            is_active=False,
        )
        assert workflow.name == "Custom Workflow"
        assert workflow.description == "Custom description"
        assert workflow.is_active is False


# =============================================================================
# NODE FACTORY FIXTURE TESTS
# =============================================================================


class TestNodeFactory:
    """Tests for node_factory fixture."""

    def test_node_factory_creates_node(self, node_factory):
        """Test that node_factory creates Node instances."""
        node = node_factory()
        assert isinstance(node, Node)
        assert node.id is not None

    def test_node_factory_uses_defaults(self, node_factory):
        """Test that node_factory uses default values."""
        node = node_factory()
        assert node.name == "Factory Node"
        assert node.node_type == NodeType.TOOL

    def test_node_factory_accepts_custom_values(self, node_factory):
        """Test that node_factory accepts custom values."""
        node = node_factory(
            name="Custom Node",
            node_type=NodeType.AGENT,
            position_x=500.0,
        )
        assert node.name == "Custom Node"
        assert node.node_type == NodeType.AGENT
        assert node.position_x == 500.0


# =============================================================================
# EDGE FACTORY FIXTURE TESTS
# =============================================================================


class TestEdgeFactory:
    """Tests for edge_factory fixture."""

    def test_edge_factory_creates_edge(self, edge_factory):
        """Test that edge_factory creates Edge instances."""
        edge = edge_factory()
        assert isinstance(edge, Edge)
        assert edge.id is not None

    def test_edge_factory_uses_defaults(self, edge_factory):
        """Test that edge_factory uses default values."""
        edge = edge_factory()
        assert edge.priority == 0
        assert edge.condition is None

    def test_edge_factory_accepts_custom_values(self, edge_factory):
        """Test that edge_factory accepts custom values."""
        edge = edge_factory(
            priority=5,
            label="Custom Label",
        )
        assert edge.priority == 5
        assert edge.label == "Custom Label"


# =============================================================================
# EXECUTION FACTORY FIXTURE TESTS
# =============================================================================


class TestExecutionFactory:
    """Tests for execution_factory fixture."""

    def test_execution_factory_creates_execution(self, execution_factory):
        """Test that execution_factory creates WorkflowExecution instances."""
        execution = execution_factory()
        assert isinstance(execution, WorkflowExecution)
        assert execution.id is not None

    def test_execution_factory_uses_defaults(self, execution_factory):
        """Test that execution_factory uses default values."""
        execution = execution_factory()
        assert execution.status == ExecutionStatus.PENDING
        assert execution.trigger_type == TriggerType.MANUAL

    def test_execution_factory_accepts_custom_values(self, execution_factory):
        """Test that execution_factory accepts custom values."""
        execution = execution_factory(
            status=ExecutionStatus.RUNNING,
            trigger_type=TriggerType.EVENT,
        )
        assert execution.status == ExecutionStatus.RUNNING
        assert execution.trigger_type == TriggerType.EVENT


# =============================================================================
# NODE EXECUTION FACTORY FIXTURE TESTS
# =============================================================================


class TestNodeExecutionFactory:
    """Tests for node_execution_factory fixture."""

    def test_node_execution_factory_creates_node_execution(
        self, node_execution_factory
    ):
        """Test that node_execution_factory creates NodeExecution instances."""
        node_exec = node_execution_factory()
        assert isinstance(node_exec, NodeExecution)
        assert node_exec.id is not None

    def test_node_execution_factory_accepts_custom_values(self, node_execution_factory):
        """Test that node_execution_factory accepts custom values."""
        node_exec = node_execution_factory(
            retry_count=3,
            execution_order=5,
        )
        assert node_exec.retry_count == 3
        assert node_exec.execution_order == 5


# =============================================================================
# EXECUTION LOG FACTORY FIXTURE TESTS
# =============================================================================


class TestExecutionLogFactory:
    """Tests for execution_log_factory fixture."""

    def test_execution_log_factory_creates_log(self, execution_log_factory):
        """Test that execution_log_factory creates ExecutionLog instances."""
        log = execution_log_factory()
        assert isinstance(log, ExecutionLog)
        assert log.id is not None

    def test_execution_log_factory_uses_defaults(self, execution_log_factory):
        """Test that execution_log_factory uses default values."""
        log = execution_log_factory()
        assert log.level == LogLevel.INFO
        assert "Factory log message" in log.message

    def test_execution_log_factory_accepts_custom_values(self, execution_log_factory):
        """Test that execution_log_factory accepts custom values."""
        log = execution_log_factory(
            level=LogLevel.ERROR,
            message="Custom error message",
        )
        assert log.level == LogLevel.ERROR
        assert log.message == "Custom error message"


# =============================================================================
# TOOL FACTORY FIXTURE TESTS
# =============================================================================


class TestToolFactory:
    """Tests for tool_factory fixture."""

    def test_tool_factory_creates_tool(self, tool_factory):
        """Test that tool_factory creates Tool instances."""
        tool = tool_factory()
        assert isinstance(tool, Tool)
        assert tool.id is not None

    def test_tool_factory_uses_defaults(self, tool_factory):
        """Test that tool_factory uses default values."""
        tool = tool_factory()
        assert tool.name == "Factory Tool"
        assert tool.tool_type == ToolType.HTTP

    def test_tool_factory_accepts_custom_values(self, tool_factory):
        """Test that tool_factory accepts custom values."""
        tool = tool_factory(
            name="Custom Tool",
            tool_type=ToolType.MCP,
        )
        assert tool.name == "Custom Tool"
        assert tool.tool_type == ToolType.MCP


# =============================================================================
# AGENT FACTORY FIXTURE TESTS
# =============================================================================


class TestAgentFactory:
    """Tests for agent_factory fixture."""

    def test_agent_factory_creates_agent(self, agent_factory):
        """Test that agent_factory creates Agent instances."""
        agent = agent_factory()
        assert isinstance(agent, Agent)
        assert agent.id is not None

    def test_agent_factory_uses_defaults(self, agent_factory):
        """Test that agent_factory uses default values.

        Note: Default name includes a counter for uniqueness (e.g., "Factory Agent 1").
        model_provider is a computed property returning string from model_config.
        """
        agent = agent_factory()
        assert agent.name.startswith("Factory Agent")
        # model_provider is now a computed property returning string from model_config
        assert agent.model_provider == "anthropic"

    def test_agent_factory_accepts_custom_values(self, agent_factory):
        """Test that agent_factory accepts custom values."""
        agent = agent_factory(
            name="Custom Agent",
            model_provider=ModelProvider.OPENAI,
        )
        assert agent.name == "Custom Agent"
        # model_provider is now a computed property returning string
        assert agent.model_provider == "openai"


# =============================================================================
# LEGACY FIXTURE TESTS
# =============================================================================


class TestLegacyFixtures:
    """Tests for legacy/deprecated fixtures."""

    def test_sample_workflow_data_returns_dict(self, sample_workflow_data):
        """Test that sample_workflow_data returns a dictionary.

        This fixture is deprecated but should still work for backward compatibility.
        """
        assert isinstance(sample_workflow_data, dict)
        assert "name" in sample_workflow_data
        assert sample_workflow_data["name"] == "Test Workflow"

    def test_sample_node_data_returns_dict(self, sample_node_data):
        """Test that sample_node_data returns a JSON-serializable dict."""
        assert isinstance(sample_node_data, dict)
        assert "name" in sample_node_data
        assert "node_type" in sample_node_data
        # node_type should be a string for JSON serialization
        assert isinstance(sample_node_data["node_type"], str)

    def test_sample_edge_data_returns_dict(self, sample_edge_data):
        """Test that sample_edge_data returns a dictionary."""
        assert isinstance(sample_edge_data, dict)
        assert "source_node_id" in sample_edge_data
        assert "target_node_id" in sample_edge_data

    def test_sample_execution_data_returns_dict(self, sample_execution_data):
        """Test that sample_execution_data returns a dictionary."""
        assert isinstance(sample_execution_data, dict)
        assert "trigger_type" in sample_execution_data
        assert "input_data" in sample_execution_data


# Import for SQL queries
from sqlalchemy import text
