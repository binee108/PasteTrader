"""pytest configuration and fixtures for integration testing.

TAG: [SPEC-001] [TESTING] [PYTEST] [FIXTURES]
REQ: REQ-001 - pytest Configuration with Async Support
REQ: REQ-002 - Test Database Session Fixture
REQ: REQ-003 - Test Database Engine Fixture (SQLite In-Memory)
REQ: REQ-004 - Test Data Fixtures (workflow, nodes, edges, executions)
REQ: REQ-005 - Cleanup After Tests
REQ: REQ-006 - Transaction Rollback for Isolated Tests

This module provides comprehensive pytest fixtures for integration testing
including async database sessions with transaction rollback, sample data fixtures,
and factory patterns for creating test models.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from starlette.types import ASGIApp

# Import app (required for async_client fixture)
from app.main import app

try:
    from app.models import Base
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
    from app.models.schedule import Schedule
    from app.models.tool import Tool
    from app.models.tool_spec009 import Spec009Base
    from app.models.user import User
    from app.models.workflow import Edge, Node, Workflow
except ImportError:
    Base = None
    Agent = None
    ExecutionStatus = None
    LogLevel = None
    ModelProvider = None
    NodeType = None
    ToolType = None
    TriggerType = None
    ExecutionLog = None
    NodeExecution = None
    WorkflowExecution = None
    Schedule = None
    Tool = None
    Spec009Base = None
    Edge = None
    Node = None
    Workflow = None

# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "asyncio: marks tests as async (pytest-asyncio)",
    )


# =============================================================================
# ASYNC ENGINE FIXTURES (SQLite In-Memory for Tests)
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def async_engine() -> AsyncGenerator[AsyncEngine]:
    """Create an async SQLite in-memory engine for testing.

    This fixture creates a new database engine for each test function.
    All tables are created on setup and dropped on teardown.

    Yields:
        AsyncEngine: SQLAlchemy async engine backed by SQLite in-memory.

    Example:
        async def test_something(async_engine):
            async with async_engine.connect() as conn:
                result = await conn.execute(select(Workflow))
    """
    # Create SQLite in-memory database for fast isolated tests
    # Note: Foreign keys are not enforced in SQLite for better test performance
    # Cascade deletes are handled by SQLAlchemy ORM cascade configuration
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

    # Create all tables (both Base and Spec009Base)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Spec009Base.metadata.create_all)

    try:
        yield engine
    finally:
        # Drop all tables and dispose engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Spec009Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session_maker(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the test engine.

    This fixture provides a session factory that creates new sessions
    bound to the in-memory SQLite database for testing.

    Args:
        async_engine: The test engine fixture.

    Returns:
        async_sessionmaker: Factory for creating async sessions.

    Example:
        def test_something(async_session_maker):
            async with async_session_maker() as session:
                workflow = Workflow(name="Test", owner_id=uuid4())
                session.add(workflow)
                await session.commit()
    """
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


# =============================================================================
# DATABASE SESSION FIXTURES WITH TRANSACTION ROLLBACK
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def db_session(
    async_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Provide a database session with automatic rollback after each test.

    This fixture creates a new session that wraps all operations in a
    transaction. The transaction is rolled back after the test, ensuring
    tests don't affect each other and the database is clean for each test.

    The fixture uses nested transactions (SAVEPOINT) to allow for
    commit operations within tests while still rolling back at the end.

    Args:
        async_session_maker: Factory for creating async sessions.

    Yields:
        AsyncSession: Database session with automatic rollback.

    Example:
        async def test_create_workflow(db_session):
            workflow = Workflow(name="Test", owner_id=uuid4())
            db_session.add(workflow)
            await db_session.commit()
            # Changes will be rolled back after test
    """
    async with async_session_maker() as session:
        # Begin nested transaction for isolation
        session.begin_nested()

        # If the test calls session.commit(), this event will restart the nested transaction
        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(session_sync: Session, transaction) -> None:
            if transaction.nested and not transaction._parent.nested:
                session_sync.expire_all()
                session_sync.begin_nested()

        try:
            yield session
        finally:
            # Rollback all changes (including committed ones)
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def db_with_data(
    db_session: AsyncSession,
    sample_workflow: Workflow,
    sample_node: Node,
    sample_edge: Edge,
    sample_execution: WorkflowExecution,
) -> AsyncSession:
    """Provide a database session pre-populated with sample data.

    This fixture builds on db_session and adds commonly used test data
    before yielding the session. Useful for tests that need a basic
    workflow structure to operate on.

    Args:
        db_session: The base database session.
        sample_workflow: A sample workflow instance.
        sample_node: A sample node instance.
        sample_edge: A sample edge instance.
        sample_execution: A sample execution instance.

    Returns:
        AsyncSession: Database session with pre-populated data.

    Example:
        async def test_workflow_execution(db_with_data):
            result = await db_with_data.execute(select(WorkflowExecution))
            assert result.scalar_one_or_none() is not None
    """
    # Add all sample data
    db_session.add(sample_workflow)
    db_session.add(sample_node)
    db_session.add(sample_edge)
    db_session.add(sample_execution)

    await db_session.flush()
    return db_session


# =============================================================================
# HTTP CLIENT FIXTURES
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Async HTTP client for testing API endpoints.

    Uses ASGI transport to test the FastAPI app without running a server.
    Overrides the database dependency to use the test SQLite database
    instead of the production PostgreSQL database.

    Args:
        db_session: The test database session fixture using SQLite in-memory.

    Yields:
        AsyncClient: HTTP client configured for testing.

    Example:
        async def test_get_workflow(async_client):
            response = await async_client.get("/api/v1/workflows/")
            assert response.status_code == 200
    """
    from app.db.session import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        """Override database dependency to use test session."""
        yield db_session

    # Override the get_db dependency to use the test database session
    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=cast("ASGIApp", app))
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        # Clean up dependency overrides after the test
        app.dependency_overrides.clear()


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_user_id() -> str:
    """Provide a consistent user ID for testing."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_workflow(sample_user_id: str) -> Workflow:
    """Create a sample Workflow instance for testing.

    Args:
        sample_user_id: User ID to use as workflow owner.

    Returns:
        Workflow: Sample workflow instance (not persisted).

    Example:
        def test_workflow_properties(sample_workflow):
            assert sample_workflow.name == "Test Workflow"
            assert sample_workflow.is_active is True
    """
    return Workflow(
        id=uuid4(),
        owner_id=sample_user_id,
        name="Test Workflow",
        description="A test workflow for integration testing",
        config={"timeout": 300, "max_retries": 3},
        variables={"api_key": "test_key", "environment": "test"},
        is_active=True,
        version=1,
    )


@pytest.fixture
def sample_node(sample_workflow: Workflow) -> Node:
    """Create a sample Node instance for testing.

    Args:
        sample_workflow: The workflow this node belongs to.

    Returns:
        Node: Sample node instance (not persisted).

    Example:
        def test_node_properties(sample_node):
            assert sample_node.name == "Test Node"
            assert sample_node.node_type == NodeType.TOOL
    """
    return Node(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        name="Test Node",
        node_type=NodeType.TOOL,
        position_x=100.0,
        position_y=200.0,
        config={"tool_config": "value"},
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"output": {"type": "string"}}},
        tool_id=uuid4(),
        agent_id=None,
        timeout_seconds=300,
        retry_config={"max_retries": 3, "delay": 1.0, "backoff_multiplier": 2.0},
    )


@pytest.fixture
def sample_trigger_node(sample_workflow: Workflow) -> Node:
    """Create a sample trigger Node instance for testing.

    Args:
        sample_workflow: The workflow this node belongs to.

    Returns:
        Node: Sample trigger node instance (not persisted).
    """
    return Node(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        name="Trigger Node",
        node_type=NodeType.TRIGGER,
        position_x=0.0,
        position_y=100.0,
        config={"trigger_type": "webhook"},
        input_schema=None,
        output_schema=None,
        tool_id=None,
        agent_id=None,
        timeout_seconds=60,
        retry_config={"max_retries": 0, "delay": 0},
    )


@pytest.fixture
def sample_agent_node(sample_workflow: Workflow) -> Node:
    """Create a sample agent Node instance for testing.

    Args:
        sample_workflow: The workflow this node belongs to.

    Returns:
        Node: Sample agent node instance (not persisted).
    """
    return Node(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        name="Agent Node",
        node_type=NodeType.AGENT,
        position_x=200.0,
        position_y=100.0,
        config={"temperature": 0.7, "max_tokens": 1000},
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        tool_id=None,
        agent_id=uuid4(),
        timeout_seconds=120,
        retry_config={"max_retries": 2, "delay": 1.0},
    )


@pytest.fixture
def sample_edge(
    sample_workflow: Workflow, sample_trigger_node: Node, sample_node: Node
) -> Edge:
    """Create a sample Edge instance for testing.

    Args:
        sample_workflow: The workflow this edge belongs to.
        sample_trigger_node: The source node for this edge.
        sample_node: The target node for this edge.

    Returns:
        Edge: Sample edge instance (not persisted).

    Example:
        def test_edge_properties(sample_edge):
            assert sample_edge.source_node_id == sample_trigger_node.id
            assert sample_edge.target_node_id == sample_node.id
    """
    return Edge(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        source_node_id=sample_trigger_node.id,
        target_node_id=sample_node.id,
        source_handle="output",
        target_handle="input",
        condition=None,
        priority=0,
        label="trigger to tool",
    )


@pytest.fixture
def sample_conditional_edge(
    sample_workflow: Workflow, sample_node: Node, sample_agent_node: Node
) -> Edge:
    """Create a sample conditional Edge for testing.

    Args:
        sample_workflow: The workflow this edge belongs to.
        sample_node: The source node.
        sample_agent_node: The target node.

    Returns:
        Edge: Sample conditional edge instance (not persisted).
    """
    return Edge(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        source_node_id=sample_node.id,
        target_node_id=sample_agent_node.id,
        source_handle="success",
        target_handle="input",
        condition={"field": "status", "operator": "eq", "value": "success"},
        priority=1,
        label="on success",
    )


@pytest.fixture
def sample_execution(sample_workflow: Workflow) -> WorkflowExecution:
    """Create a sample WorkflowExecution instance for testing.

    Args:
        sample_workflow: The workflow being executed.

    Returns:
        WorkflowExecution: Sample execution instance (not persisted).

    Example:
        def test_execution_properties(sample_execution):
            assert sample_execution.status == ExecutionStatus.PENDING
            assert sample_execution.trigger_type == TriggerType.MANUAL
    """
    return WorkflowExecution(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        trigger_type=TriggerType.MANUAL,
        status=ExecutionStatus.PENDING,
        started_at=None,
        ended_at=None,
        input_data={"test_input": "value"},
        output_data=None,
        error_message=None,
        context={"variables": {}, "secrets": {}, "environment": "test"},
        metadata_={"triggered_by": "test_user", "priority": 0, "tags": ["test"]},
    )


@pytest.fixture
def sample_running_execution(sample_workflow: Workflow) -> WorkflowExecution:
    """Create a running WorkflowExecution instance for testing.

    Args:
        sample_workflow: The workflow being executed.

    Returns:
        WorkflowExecution: Sample running execution instance.
    """
    now = datetime.now(UTC)
    return WorkflowExecution(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        trigger_type=TriggerType.MANUAL,
        status=ExecutionStatus.RUNNING,
        started_at=now,
        ended_at=None,
        input_data={"test_input": "value"},
        output_data=None,
        error_message=None,
        context={"variables": {}, "secrets": {}, "environment": "test"},
        metadata_={"triggered_by": "test_user", "priority": 0},
    )


@pytest.fixture
def sample_completed_execution(sample_workflow: Workflow) -> WorkflowExecution:
    """Create a completed WorkflowExecution instance for testing.

    Args:
        sample_workflow: The workflow being executed.

    Returns:
        WorkflowExecution: Sample completed execution instance.
    """
    now = datetime.now(UTC)
    return WorkflowExecution(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        trigger_type=TriggerType.EVENT,
        status=ExecutionStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        input_data={"test_input": "value"},
        output_data={"result": "success"},
        error_message=None,
        context={"variables": {}, "secrets": {}, "environment": "test"},
        metadata_={"triggered_by": "system", "priority": 5},
    )


@pytest.fixture
def sample_failed_execution(sample_workflow: Workflow) -> WorkflowExecution:
    """Create a failed WorkflowExecution instance for testing.

    Args:
        sample_workflow: The workflow being executed.

    Returns:
        WorkflowExecution: Sample failed execution instance.
    """
    now = datetime.now(UTC)
    return WorkflowExecution(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        trigger_type=TriggerType.SCHEDULE,
        status=ExecutionStatus.FAILED,
        started_at=now,
        ended_at=now,
        input_data={"test_input": "value"},
        output_data=None,
        error_message="Test error: Something went wrong",
        context={"variables": {}, "secrets": {}, "environment": "test"},
        metadata_={"triggered_by": "scheduler", "priority": 0},
    )


@pytest.fixture
def sample_node_execution(
    sample_execution: WorkflowExecution, sample_node: Node
) -> NodeExecution:
    """Create a sample NodeExecution instance for testing.

    Args:
        sample_execution: The parent workflow execution.
        sample_node: The node being executed.

    Returns:
        NodeExecution: Sample node execution instance (not persisted).

    Example:
        def test_node_execution(sample_node_execution):
            assert sample_node_execution.status == ExecutionStatus.PENDING
            assert sample_node_execution.retry_count == 0
    """
    return NodeExecution(
        id=uuid4(),
        workflow_execution_id=sample_execution.id,
        node_id=sample_node.id,
        status=ExecutionStatus.PENDING,
        started_at=None,
        ended_at=None,
        input_data={"node_input": "value"},
        output_data=None,
        error_message=None,
        error_traceback=None,
        retry_count=0,
        execution_order=1,
    )


@pytest.fixture
def sample_execution_log(sample_execution: WorkflowExecution) -> ExecutionLog:
    """Create a sample ExecutionLog instance for testing.

    Args:
        sample_execution: The parent workflow execution.

    Returns:
        ExecutionLog: Sample log entry (not persisted).

    Example:
        def test_execution_log(sample_execution_log):
            assert sample_execution_log.level == LogLevel.INFO
            assert "Test log message" in sample_execution_log.message
    """
    return ExecutionLog(
        id=uuid4(),
        workflow_execution_id=sample_execution.id,
        node_execution_id=None,
        level=LogLevel.INFO,
        message="Test log message",
        data={"extra": "information"},
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_tool(sample_user_id: str) -> Tool:
    """Create a sample Tool instance for testing.

    Args:
        sample_user_id: User ID to use as tool owner.

    Returns:
        Tool: Sample tool instance (not persisted).
    """
    return Tool(
        id=uuid4(),
        owner_id=sample_user_id,
        name="Test HTTP Tool",
        description="A test HTTP tool for making API requests",
        tool_type=ToolType.HTTP,
        config={
            "url": "https://api.example.com/endpoint",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
        },
        input_schema={"type": "object", "properties": {"data": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        auth_config={"type": "bearer", "token": "test_token"},
        rate_limit={"max_requests": 100, "period": 60},
        is_active=True,
        is_public=False,
    )


@pytest.fixture
def sample_agent(sample_user_id: str) -> Agent:
    """Create a sample Agent instance for testing.

    Args:
        sample_user_id: User ID to use as agent owner.

    Returns:
        Agent: Sample agent instance (not persisted).

    Note:
        model_provider and model_name are now computed properties derived from llm_config.
        Access via agent.model_provider and agent.model_name returns string values.
    """
    return Agent(
        id=uuid4(),
        owner_id=sample_user_id,
        name="Test Agent",
        description="A test AI agent for workflow automation",
        system_prompt="You are a helpful assistant for testing.",
        llm_config={
            "provider": "anthropic",
            "model": "claude-3-opus-20240229",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
        },
        is_active=True,
        is_public=False,
    )


# =============================================================================
# FIXTURE FACTORIES
# =============================================================================


@pytest.fixture
def workflow_factory(sample_user_id: str):
    """Factory for creating test Workflow objects.

    The factory function allows creating workflows with custom attributes
    while providing sensible defaults for unspecified fields.

    Args:
        sample_user_id: Default user ID for workflow owner.

    Returns:
        Callable: Factory function that creates Workflow instances.

    Example:
        def test_workflow_creation(workflow_factory):
            workflow = workflow_factory(name="Custom Workflow")
            assert workflow.name == "Custom Workflow"
            assert workflow.owner_id == sample_user_id
    """

    def _create(**kwargs):
        now = datetime.now(UTC)
        defaults = {
            "id": uuid4(),
            "owner_id": UUID(sample_user_id),
            "name": "Factory Workflow",
            "description": "Created by workflow factory",
            "config": {"url": "https://api.example.com/test"},
            "variables": {},
            "is_active": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return Workflow(**defaults)

    return _create


@pytest.fixture
def node_factory():
    """Factory for creating test Node objects.

    Returns:
        Callable: Factory function that creates Node instances.

    Example:
        def test_node_factory(node_factory):
            node = node_factory(name="Custom Node", node_type=NodeType.AGENT)
            assert node.name == "Custom Node"
            assert node.node_type == NodeType.AGENT
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "workflow_id": uuid4(),
            "name": "Factory Node",
            "node_type": NodeType.TOOL,
            "position_x": 0.0,
            "position_y": 0.0,
            "config": {"url": "https://api.example.com/test"},
            "input_schema": None,
            "output_schema": None,
            "tool_id": None,
            "agent_id": None,
            "timeout_seconds": 300,
            "retry_config": {"max_retries": 3, "delay": 1.0},
        }
        defaults.update(kwargs)
        return Node(**defaults)

    return _create


@pytest.fixture
def edge_factory():
    """Factory for creating test Edge objects.

    Returns:
        Callable: Factory function that creates Edge instances.

    Example:
        def test_edge_factory(edge_factory):
            edge = edge_factory(label="Custom Edge")
            assert edge.label == "Custom Edge"
            assert edge.priority == 0
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "workflow_id": uuid4(),
            "source_node_id": uuid4(),
            "target_node_id": uuid4(),
            "source_handle": None,
            "target_handle": None,
            "condition": None,
            "priority": 0,
            "label": None,
        }
        defaults.update(kwargs)
        return Edge(**defaults)

    return _create


@pytest.fixture
def execution_factory():
    """Factory for creating test WorkflowExecution objects.

    Returns:
        Callable: Factory function that creates WorkflowExecution instances.

    Example:
        def test_execution_factory(execution_factory):
            execution = execution_factory(status=ExecutionStatus.RUNNING)
            assert execution.status == ExecutionStatus.RUNNING
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "workflow_id": uuid4(),
            "trigger_type": TriggerType.MANUAL,
            "status": ExecutionStatus.PENDING,
            "started_at": None,
            "ended_at": None,
            "input_data": {},
            "output_data": None,
            "error_message": None,
            "context": {},
            "metadata_": {},
        }
        defaults.update(kwargs)
        return WorkflowExecution(**defaults)

    return _create


@pytest.fixture
def node_execution_factory():
    """Factory for creating test NodeExecution objects.

    Returns:
        Callable: Factory function that creates NodeExecution instances.

    Example:
        def test_node_execution_factory(node_execution_factory):
            node_exec = node_execution_factory(retry_count=2)
            assert node_exec.retry_count == 2
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "workflow_execution_id": uuid4(),
            "node_id": uuid4(),
            "status": ExecutionStatus.PENDING,
            "started_at": None,
            "ended_at": None,
            "input_data": {},
            "output_data": None,
            "error_message": None,
            "error_traceback": None,
            "retry_count": 0,
            "execution_order": 1,
        }
        defaults.update(kwargs)
        return NodeExecution(**defaults)

    return _create


@pytest.fixture
def execution_log_factory():
    """Factory for creating test ExecutionLog objects.

    Returns:
        Callable: Factory function that creates ExecutionLog instances.

    Example:
        def test_execution_log_factory(execution_log_factory):
            log = execution_log_factory(level=LogLevel.ERROR)
            assert log.level == LogLevel.ERROR
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "workflow_execution_id": uuid4(),
            "node_execution_id": None,
            "level": LogLevel.INFO,
            "message": "Factory log message",
            "data": None,
            "timestamp": datetime.now(UTC),
        }
        defaults.update(kwargs)
        return ExecutionLog(**defaults)

    return _create


@pytest.fixture
def tool_factory(sample_user_id: str):
    """Factory for creating test Tool objects.

    Args:
        sample_user_id: Default user ID for tool owner.

    Returns:
        Callable: Factory function that creates Tool instances.

    Example:
        def test_tool_factory(tool_factory):
            tool = tool_factory(name="Custom Tool", tool_type=ToolType.MCP)
            assert tool.name == "Custom Tool"
            assert tool.tool_type == ToolType.MCP
    """

    def _create(**kwargs):
        defaults = {
            "id": uuid4(),
            "owner_id": UUID(sample_user_id),
            "name": "Factory Tool",
            "description": None,
            "tool_type": ToolType.HTTP,
            "config": {"url": "https://api.example.com/test"},
            "input_schema": {},
            "output_schema": None,
            "auth_config": None,
            "rate_limit": None,
            "is_active": True,
            "is_public": False,
        }
        defaults.update(kwargs)
        return Tool(**defaults)

    return _create


@pytest.fixture
def agent_factory(sample_user_id: str):
    """Factory for creating test Agent objects.

    Args:
        sample_user_id: Default user ID for agent owner.

    Returns:
        Callable: Factory function that creates Agent instances.

    Note:
        model_provider and model_name are converted to llm_config internally.
        The Agent model uses computed properties to expose these from llm_config.
        Each created agent has a unique name by default to avoid UNIQUE constraint violations.
        The 'tools' parameter is removed from kwargs as it's a relationship, not a direct field.
        Use db_session to add Tool relationships after creating the agent.

    Example:
        def test_agent_factory(agent_factory):
            agent = agent_factory(model_provider=ModelProvider.OPENAI)
            assert agent.model_provider == "openai"
    """
    # Counter for unique names
    counter = [0]

    def _create(**kwargs):
        # Extract model_provider and model_name from kwargs (for backward compatibility)
        # These will be converted to llm_config
        model_provider = kwargs.pop("model_provider", ModelProvider.ANTHROPIC)
        model_name = kwargs.pop("model_name", "claude-3-opus-20240229")

        # Convert enum to string if needed
        provider_str = str(model_provider) if model_provider else "anthropic"

        # Build llm_config from provider and model name
        llm_config = kwargs.pop("llm_config", None)
        if llm_config is None:
            llm_config = {
                "provider": provider_str,
                "model": model_name,
            }

        # Remove 'tools' from kwargs - it's a relationship, not a direct field
        # Tests that need tools should add Tool objects via the relationship after creation
        kwargs.pop("tools", None)

        # Generate unique name if not provided
        counter[0] += 1
        default_name = f"Factory Agent {counter[0]}"

        defaults = {
            "id": uuid4(),
            "owner_id": UUID(sample_user_id),
            "name": default_name,
            "description": None,
            "system_prompt": "You are a helpful assistant.",
            "llm_config": llm_config,
            "is_active": True,
            "is_public": False,
        }
        defaults.update(kwargs)
        return Agent(**defaults)

    return _create


# =============================================================================
# LEGACY FIXTURES (for backward compatibility)
# =============================================================================


@pytest.fixture
def sample_workflow_data() -> dict:
    """Sample workflow data dictionary for testing.

    Deprecated: Use sample_workflow fixture instead.
    """
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "config": {},
        "variables": {},
        "is_active": True,
    }


@pytest.fixture
def sample_node_data() -> dict:
    """Sample node data dictionary for testing API endpoints.

    Uses JSON-serializable values for HTTP API tests.
    For ORM model tests, use sample_node fixture instead.
    """
    return {
        "name": "Test Node",
        "node_type": "tool",  # String value for JSON serialization
        "position_x": 100.0,
        "position_y": 200.0,
        "config": {},
        "input_schema": None,
        "output_schema": None,
        "tool_id": str(uuid4()),  # tool_id is required for tool nodes
        "agent_id": None,
        "timeout_seconds": 300,
        "retry_config": {"max_retries": 3, "delay": 1.0, "backoff_multiplier": 1.0},
    }


@pytest.fixture
def sample_edge_data() -> dict:
    """Sample edge data dictionary for testing.

    Deprecated: Use sample_edge fixture instead.
    """
    return {
        "source_node_id": uuid4(),
        "target_node_id": uuid4(),
        "source_handle": "output",
        "target_handle": "input",
        "condition": None,
        "priority": 0,
        "label": None,
    }


@pytest.fixture
def sample_execution_data() -> dict:
    """Sample execution data dictionary for testing.

    Deprecated: Use sample_execution fixture instead.
    """
    return {
        "workflow_id": uuid4(),
        "trigger_type": TriggerType.MANUAL,
        "input_data": {"test": "data"},
        "context": {"variables": {}, "secrets": {}, "environment": {}},
        "metadata_": {"triggered_by": "test", "priority": 0, "tags": []},
    }


# =============================================================================
# SCHEDULE FIXTURES
# =============================================================================


@pytest.fixture
def sample_schedule(sample_user_id: str, sample_workflow: Workflow):
    """Create a sample Schedule instance for testing.

    Args:
        sample_user_id: User ID to use as schedule owner.
        sample_workflow: The workflow this schedule belongs to.

    Returns:
        Schedule: Sample schedule instance (not persisted).

    Example:
        def test_schedule_properties(sample_schedule):
            assert sample_schedule.name == "Test Schedule"
            assert sample_schedule.schedule_type == ScheduleType.CRON
    """
    from app.models.enums import ScheduleType

    now = datetime.now(UTC)
    return Schedule(
        id=uuid4(),
        workflow_id=sample_workflow.id,
        user_id=UUID(sample_user_id),
        name="Test Schedule",
        description="A test schedule for integration testing",
        schedule_type=ScheduleType.CRON,
        schedule_config={"cron_expression": "0 9 * * 1-5"},
        timezone="UTC",
        is_active=True,
        job_id="test-job-id",
        next_run_at=datetime(2026, 1, 17, 9, 0, tzinfo=UTC),
        last_run_at=None,
        run_count=0,
        metadata_={},
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def schedule_factory(sample_user_id: str):
    """Factory for creating test Schedule objects.

    Args:
        sample_user_id: Default user ID for schedule owner.

    Returns:
        Callable: Factory function that creates Schedule instances.

    Example:
        def test_schedule_creation(schedule_factory):
            schedule = schedule_factory(name="Custom Schedule")
            assert schedule.name == "Custom Schedule"
    """
    from app.models.enums import ScheduleType

    def _create(**kwargs):
        workflow_id = kwargs.pop("workflow_id", uuid4())
        defaults = {
            "id": uuid4(),
            "workflow_id": workflow_id,
            "user_id": UUID(sample_user_id),
            "name": "Factory Schedule",
            "description": None,
            "schedule_type": ScheduleType.CRON,
            "schedule_config": {"cron_expression": "0 9 * * *"},
            "timezone": "UTC",
            "is_active": True,
            "job_id": None,
            "next_run_at": None,
            "last_run_at": None,
            "run_count": 0,
            "metadata_": {},
        }
        defaults.update(kwargs)
        return Schedule(**defaults)

    return _create


@pytest.fixture
def schedule_model(sample_schedule: Schedule):
    """Alias for sample_schedule for backward compatibility.

    Args:
        sample_schedule: A sample schedule instance.

    Returns:
        Schedule: Sample schedule instance.
    """
    return sample_schedule


@pytest.fixture
def schedule_service():
    """Create a ScheduleService instance for testing.

    Returns:
        ScheduleService: Service instance with mock scheduler.

    Example:
        def test_schedule_creation(schedule_service):
            result = await schedule_service.create_schedule(
                db_session, schedule_data, user_id
            )
            assert result.name == "Test Schedule"
    """
    from unittest.mock import MagicMock

    from app.services.schedule.service import ScheduleService

    # Create mock scheduler to avoid apscheduler dependency
    mock_scheduler = MagicMock()
    mock_scheduler.add_schedule_job = MagicMock()
    mock_scheduler.remove_job = MagicMock()
    mock_scheduler.pause_job = MagicMock()
    mock_scheduler.resume_job = MagicMock()
    mock_scheduler.get_job = MagicMock()

    return ScheduleService(scheduler=mock_scheduler)


@pytest.fixture
def workflow_service():
    """Create a WorkflowService instance for testing.

    Returns:
        WorkflowService: Service instance for workflow operations.

    Example:
        def test_workflow_operations(workflow_service):
            result = await workflow_service.create_workflow(
                db_session, workflow_data, user_id
            )
    """
    from app.services.workflow_service import WorkflowService

    return WorkflowService()


@pytest.fixture
def execution_service():
    """Create an ExecutionService instance for testing.

    Returns:
        ExecutionService: Service instance for execution operations.

    Example:
        def test_execution_workflow(execution_service):
            result = await execution_service.execute_workflow(
                db_session, workflow_id, execution_data
            )
    """
    from app.services.execution_service import WorkflowExecutionService

    return WorkflowExecutionService()



# =============================================================================
# AUTHENTICATION FIXTURES FOR SCHEDULE API TESTS
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for authentication.

    Returns:
        User: A test user with admin privileges.

    Example:
        async def test_with_user(test_user):
            assert test_user.email == "admin@localhost"
    """
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        id=uuid4(),
        email="admin@localhost",
        hashed_password=hash_password("test_password"),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def async_client_auth(
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[AsyncClient]:
    """Async HTTP client with authentication override for testing.

    This fixture overrides the CurrentUser dependency to provide authentication
    without requiring JWT tokens. This allows testing authenticated endpoints
    without the complexity of token management.

    Args:
        db_session: The test database session.
        test_user: The test user to authenticate as.

    Yields:
        AsyncClient: HTTP client configured with authenticated user.

    Example:
        async def test_create_schedule(async_client_auth):
            response = await async_client_auth.post("/api/v1/schedules", ...)
            assert response.status_code == 201
    """
    from app.api.deps import get_current_user
    from app.db.session import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        """Override database dependency to use test session."""
        yield db_session

    async def override_get_current_user() -> User:
        """Override authentication to return test user."""
        return test_user

    # Override the dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        transport = ASGITransport(app=cast("ASGIApp", app))
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        # Clean up dependency overrides after the test
        app.dependency_overrides.clear()
