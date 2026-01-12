"""Tests for Workflow, Node, and Edge models.

TAG: [SPEC-003] [DATABASE] [WORKFLOW] [NODE] [EDGE]
REQ: REQ-001 - Workflow Model Definition
REQ: REQ-002 - Node Model Definition
REQ: REQ-003 - Edge Model Definition
REQ: REQ-004 - Workflow-Node Relationship (CASCADE)
REQ: REQ-005 - Node-Edge Relationship (CASCADE)
REQ: REQ-006 - Optimistic Locking Support
REQ: REQ-007 - Edge Uniqueness Constraint
REQ: REQ-009 - Self-Loop Prevention
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import String
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import NodeType

# Test will use SQLite for unit testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============================================================================
# NodeType Enum Tests
# ============================================================================


class TestNodeTypeEnum:
    """Test NodeType enum values for workflow nodes."""

    def test_nodetype_trigger_exists(self) -> None:
        """NodeType should have TRIGGER value."""
        assert NodeType.TRIGGER.value == "trigger"

    def test_nodetype_tool_exists(self) -> None:
        """NodeType should have TOOL value."""
        assert NodeType.TOOL.value == "tool"

    def test_nodetype_agent_exists(self) -> None:
        """NodeType should have AGENT value."""
        assert NodeType.AGENT.value == "agent"

    def test_nodetype_condition_exists(self) -> None:
        """NodeType should have CONDITION value."""
        assert NodeType.CONDITION.value == "condition"

    def test_nodetype_adapter_exists(self) -> None:
        """NodeType should have ADAPTER value."""
        assert NodeType.ADAPTER.value == "adapter"

    def test_nodetype_aggregator_exists(self) -> None:
        """NodeType should have AGGREGATOR value."""
        assert NodeType.AGGREGATOR.value == "aggregator"


# ============================================================================
# Workflow Model Structure Tests
# ============================================================================


class TestWorkflowModelStructure:
    """Test Workflow model class structure."""

    def test_workflow_class_exists(self) -> None:
        """Workflow class should exist in models.workflow module."""
        from app.models.workflow import Workflow

        assert Workflow is not None

    def test_workflow_has_tablename(self) -> None:
        """Workflow should have __tablename__ = 'workflows'."""
        from app.models.workflow import Workflow

        assert Workflow.__tablename__ == "workflows"

    def test_workflow_has_id_attribute(self) -> None:
        """Workflow should have id attribute (from UUIDMixin)."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "id")

    def test_workflow_has_owner_id_attribute(self) -> None:
        """Workflow should have owner_id attribute."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "owner_id")

    def test_workflow_has_name_attribute(self) -> None:
        """Workflow should have name attribute."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "name")

    def test_workflow_has_description_attribute(self) -> None:
        """Workflow should have description attribute."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "description")

    def test_workflow_has_config_attribute(self) -> None:
        """Workflow should have config attribute (JSONB)."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "config")

    def test_workflow_has_variables_attribute(self) -> None:
        """Workflow should have variables attribute (JSONB)."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "variables")

    def test_workflow_has_is_active_attribute(self) -> None:
        """Workflow should have is_active attribute."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "is_active")

    def test_workflow_has_version_attribute(self) -> None:
        """Workflow should have version attribute for optimistic locking."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "version")

    def test_workflow_has_timestamp_attributes(self) -> None:
        """Workflow should have created_at and updated_at attributes."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "created_at")
        assert hasattr(Workflow, "updated_at")

    def test_workflow_has_soft_delete_attribute(self) -> None:
        """Workflow should have deleted_at attribute (SoftDeleteMixin)."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "deleted_at")

    def test_workflow_has_nodes_relationship(self) -> None:
        """Workflow should have nodes relationship."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "nodes")

    def test_workflow_has_edges_relationship(self) -> None:
        """Workflow should have edges relationship."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "edges")


# ============================================================================
# Node Model Structure Tests
# ============================================================================


class TestNodeModelStructure:
    """Test Node model class structure."""

    def test_node_class_exists(self) -> None:
        """Node class should exist in models.workflow module."""
        from app.models.workflow import Node

        assert Node is not None

    def test_node_has_tablename(self) -> None:
        """Node should have __tablename__ = 'nodes'."""
        from app.models.workflow import Node

        assert Node.__tablename__ == "nodes"

    def test_node_has_id_attribute(self) -> None:
        """Node should have id attribute (from UUIDMixin)."""
        from app.models.workflow import Node

        assert hasattr(Node, "id")

    def test_node_has_workflow_id_attribute(self) -> None:
        """Node should have workflow_id attribute (FK to workflows)."""
        from app.models.workflow import Node

        assert hasattr(Node, "workflow_id")

    def test_node_has_name_attribute(self) -> None:
        """Node should have name attribute."""
        from app.models.workflow import Node

        assert hasattr(Node, "name")

    def test_node_has_node_type_attribute(self) -> None:
        """Node should have node_type attribute."""
        from app.models.workflow import Node

        assert hasattr(Node, "node_type")

    def test_node_has_position_x_attribute(self) -> None:
        """Node should have position_x attribute (float)."""
        from app.models.workflow import Node

        assert hasattr(Node, "position_x")

    def test_node_has_position_y_attribute(self) -> None:
        """Node should have position_y attribute (float)."""
        from app.models.workflow import Node

        assert hasattr(Node, "position_y")

    def test_node_has_config_attribute(self) -> None:
        """Node should have config attribute (JSONB)."""
        from app.models.workflow import Node

        assert hasattr(Node, "config")

    def test_node_has_input_schema_attribute(self) -> None:
        """Node should have input_schema attribute (JSONB, nullable)."""
        from app.models.workflow import Node

        assert hasattr(Node, "input_schema")

    def test_node_has_output_schema_attribute(self) -> None:
        """Node should have output_schema attribute (JSONB, nullable)."""
        from app.models.workflow import Node

        assert hasattr(Node, "output_schema")

    def test_node_has_tool_id_attribute(self) -> None:
        """Node should have tool_id attribute (FK to tools, nullable)."""
        from app.models.workflow import Node

        assert hasattr(Node, "tool_id")

    def test_node_has_agent_id_attribute(self) -> None:
        """Node should have agent_id attribute (FK to agents, nullable)."""
        from app.models.workflow import Node

        assert hasattr(Node, "agent_id")

    def test_node_has_timeout_seconds_attribute(self) -> None:
        """Node should have timeout_seconds attribute."""
        from app.models.workflow import Node

        assert hasattr(Node, "timeout_seconds")

    def test_node_has_retry_config_attribute(self) -> None:
        """Node should have retry_config attribute (JSONB)."""
        from app.models.workflow import Node

        assert hasattr(Node, "retry_config")

    def test_node_has_timestamp_attributes(self) -> None:
        """Node should have created_at and updated_at attributes."""
        from app.models.workflow import Node

        assert hasattr(Node, "created_at")
        assert hasattr(Node, "updated_at")

    def test_node_has_workflow_relationship(self) -> None:
        """Node should have workflow relationship."""
        from app.models.workflow import Node

        assert hasattr(Node, "workflow")


# ============================================================================
# Edge Model Structure Tests
# ============================================================================


class TestEdgeModelStructure:
    """Test Edge model class structure."""

    def test_edge_class_exists(self) -> None:
        """Edge class should exist in models.workflow module."""
        from app.models.workflow import Edge

        assert Edge is not None

    def test_edge_has_tablename(self) -> None:
        """Edge should have __tablename__ = 'edges'."""
        from app.models.workflow import Edge

        assert Edge.__tablename__ == "edges"

    def test_edge_has_id_attribute(self) -> None:
        """Edge should have id attribute (from UUIDMixin)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "id")

    def test_edge_has_workflow_id_attribute(self) -> None:
        """Edge should have workflow_id attribute (FK to workflows)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "workflow_id")

    def test_edge_has_source_node_id_attribute(self) -> None:
        """Edge should have source_node_id attribute (FK to nodes)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "source_node_id")

    def test_edge_has_target_node_id_attribute(self) -> None:
        """Edge should have target_node_id attribute (FK to nodes)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "target_node_id")

    def test_edge_has_source_handle_attribute(self) -> None:
        """Edge should have source_handle attribute (nullable)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "source_handle")

    def test_edge_has_target_handle_attribute(self) -> None:
        """Edge should have target_handle attribute (nullable)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "target_handle")

    def test_edge_has_condition_attribute(self) -> None:
        """Edge should have condition attribute (JSONB, nullable)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "condition")

    def test_edge_has_priority_attribute(self) -> None:
        """Edge should have priority attribute."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "priority")

    def test_edge_has_label_attribute(self) -> None:
        """Edge should have label attribute (nullable)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "label")

    def test_edge_has_created_at_attribute(self) -> None:
        """Edge should have created_at attribute (only created_at, no updated_at)."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "created_at")

    def test_edge_has_workflow_relationship(self) -> None:
        """Edge should have workflow relationship."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "workflow")

    def test_edge_has_source_node_relationship(self) -> None:
        """Edge should have source_node relationship."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "source_node")

    def test_edge_has_target_node_relationship(self) -> None:
        """Edge should have target_node relationship."""
        from app.models.workflow import Edge

        assert hasattr(Edge, "target_node")


# ============================================================================
# Database Fixtures
# ============================================================================


# Create mock models for testing FK references
_test_models_defined = False
_MockUserClass = None
_MockToolClass = None
_MockAgentClass = None


def get_mock_classes():
    """Get or create mock model classes for testing."""
    global _test_models_defined, _MockUserClass, _MockToolClass, _MockAgentClass

    if not _test_models_defined:
        from typing import ClassVar

        from app.models.base import Base, UUIDMixin

        class TestUserWorkflow(UUIDMixin, Base):
            """Mock User model for testing FK references."""

            __tablename__ = "users"
            __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        class Tool(UUIDMixin, Base):
            """Mock Tool model for testing FK references."""

            __tablename__ = "tools"
            __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        class Agent(UUIDMixin, Base):
            """Mock Agent model for testing FK references."""

            __tablename__ = "agents"
            __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        _MockUserClass = TestUserWorkflow
        _MockToolClass = Tool
        _MockAgentClass = Agent
        _test_models_defined = True

    return _MockUserClass, _MockToolClass, _MockAgentClass


@pytest_asyncio.fixture
async def db_session():
    """Create async session for testing with tables created."""

    # Get mock classes to satisfy FK constraints
    get_mock_classes()

    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ============================================================================
# Workflow Model Behavior Tests
# ============================================================================


class TestWorkflowModelBehavior:
    """Test Workflow model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_workflow_creation_with_required_fields(self, db_session) -> None:
        """Workflow should be creatable with required fields."""
        from app.models.workflow import Workflow

        owner_id = uuid.uuid4()
        workflow = Workflow(
            owner_id=owner_id,
            name="Test Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.id is not None
        assert workflow.owner_id == owner_id
        assert workflow.name == "Test Workflow"

    @pytest.mark.asyncio
    async def test_workflow_creation_with_all_fields(self, db_session) -> None:
        """Workflow should be creatable with all fields."""
        from app.models.workflow import Workflow

        owner_id = uuid.uuid4()
        workflow = Workflow(
            owner_id=owner_id,
            name="Complete Workflow",
            description="A workflow with all fields",
            config={"timeout": 3600},
            variables={"api_key": "secret"},
            is_active=False,
            version=5,
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.description == "A workflow with all fields"
        assert workflow.config == {"timeout": 3600}
        assert workflow.variables == {"api_key": "secret"}
        assert workflow.is_active is False
        assert workflow.version == 5

    @pytest.mark.asyncio
    async def test_workflow_config_default(self, db_session) -> None:
        """Workflow config should default to empty dict."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Default Config Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.config == {}

    @pytest.mark.asyncio
    async def test_workflow_variables_default(self, db_session) -> None:
        """Workflow variables should default to empty dict."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Default Variables Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.variables == {}

    @pytest.mark.asyncio
    async def test_workflow_is_active_default(self, db_session) -> None:
        """Workflow is_active should default to True."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Default Active Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.is_active is True

    @pytest.mark.asyncio
    async def test_workflow_version_default(self, db_session) -> None:
        """Workflow version should default to 1."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Default Version Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.version == 1

    @pytest.mark.asyncio
    async def test_workflow_soft_delete(self, db_session) -> None:
        """Workflow should support soft delete."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Deletable Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.deleted_at is None
        assert workflow.is_deleted is False

        workflow.soft_delete()
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.deleted_at is not None
        assert workflow.is_deleted is True

    @pytest.mark.asyncio
    async def test_workflow_timestamps(self, db_session) -> None:
        """Workflow should have auto-generated timestamps."""
        from app.models.workflow import Workflow

        workflow = Workflow(
            owner_id=uuid.uuid4(),
            name="Timestamped Workflow",
        )
        db_session.add(workflow)
        await db_session.commit()
        await db_session.refresh(workflow)

        assert workflow.created_at is not None
        assert workflow.updated_at is not None


# ============================================================================
# Node Model Behavior Tests
# ============================================================================


class TestNodeModelBehavior:
    """Test Node model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_node_creation_with_required_fields(self, db_session) -> None:
        """Node should be creatable with required fields."""
        from app.models.workflow import Node, Workflow

        # Create parent workflow
        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.id is not None
        assert node.workflow_id == workflow.id
        assert node.name == "Test Node"
        assert str(node.node_type) == "trigger"

    @pytest.mark.asyncio
    async def test_node_with_trigger_type(self, db_session) -> None:
        """Node with TRIGGER type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Trigger Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "trigger"

    @pytest.mark.asyncio
    async def test_node_with_tool_type(self, db_session) -> None:
        """Node with TOOL type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Tool Node",
            node_type=NodeType.TOOL,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "tool"

    @pytest.mark.asyncio
    async def test_node_with_agent_type(self, db_session) -> None:
        """Node with AGENT type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Agent Node",
            node_type=NodeType.AGENT,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "agent"

    @pytest.mark.asyncio
    async def test_node_with_condition_type(self, db_session) -> None:
        """Node with CONDITION type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Condition Node",
            node_type=NodeType.CONDITION,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "condition"

    @pytest.mark.asyncio
    async def test_node_with_adapter_type(self, db_session) -> None:
        """Node with ADAPTER type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Adapter Node",
            node_type=NodeType.ADAPTER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "adapter"

    @pytest.mark.asyncio
    async def test_node_with_aggregator_type(self, db_session) -> None:
        """Node with AGGREGATOR type should work correctly."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Aggregator Node",
            node_type=NodeType.AGGREGATOR,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert str(node.node_type) == "aggregator"

    @pytest.mark.asyncio
    async def test_node_position_defaults(self, db_session) -> None:
        """Node position_x and position_y should default to 0.0."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Positioned Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.position_x == 0.0
        assert node.position_y == 0.0

    @pytest.mark.asyncio
    async def test_node_position_float_values(self, db_session) -> None:
        """Node position_x and position_y should accept float values."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Positioned Node",
            node_type=NodeType.TRIGGER,
            position_x=100.5,
            position_y=200.75,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.position_x == 100.5
        assert node.position_y == 200.75

    @pytest.mark.asyncio
    async def test_node_config_default(self, db_session) -> None:
        """Node config should default to empty dict."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Config Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.config == {}

    @pytest.mark.asyncio
    async def test_node_input_output_schema_nullable(self, db_session) -> None:
        """Node input_schema and output_schema should be nullable."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Schema Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.input_schema is None
        assert node.output_schema is None

    @pytest.mark.asyncio
    async def test_node_input_output_schema_values(self, db_session) -> None:
        """Node input_schema and output_schema should store JSONB values."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        input_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        output_schema = {"type": "object", "properties": {"result": {"type": "string"}}}

        node = Node(
            workflow_id=workflow.id,
            name="Schema Node",
            node_type=NodeType.TOOL,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.input_schema == input_schema
        assert node.output_schema == output_schema

    @pytest.mark.asyncio
    async def test_node_timeout_seconds_default(self, db_session) -> None:
        """Node timeout_seconds should default to 300."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Timeout Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.timeout_seconds == 300

    @pytest.mark.asyncio
    async def test_node_retry_config_default(self, db_session) -> None:
        """Node retry_config should default to {'max_retries': 3, 'delay': 1}."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Retry Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.retry_config == {"max_retries": 3, "delay": 1}

    @pytest.mark.asyncio
    async def test_node_tool_id_nullable(self, db_session) -> None:
        """Node tool_id should be nullable."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Tool Node",
            node_type=NodeType.TOOL,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.tool_id is None

    @pytest.mark.asyncio
    async def test_node_agent_id_nullable(self, db_session) -> None:
        """Node agent_id should be nullable."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Agent Node",
            node_type=NodeType.AGENT,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.agent_id is None

    @pytest.mark.asyncio
    async def test_node_timestamps(self, db_session) -> None:
        """Node should have auto-generated timestamps."""
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Timestamped Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()
        await db_session.refresh(node)

        assert node.created_at is not None
        assert node.updated_at is not None

    @pytest.mark.asyncio
    async def test_node_cascade_delete_with_workflow(self, db_session) -> None:
        """Nodes should be deleted when parent workflow is deleted via ORM cascade."""
        from sqlalchemy import text

        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Cascade Node",
            node_type=NodeType.TRIGGER,
        )
        db_session.add(node)
        await db_session.commit()

        node_id = node.id

        # Delete workflow - ORM cascade should delete nodes
        await db_session.delete(workflow)
        await db_session.commit()

        # Expire all to clear cache and verify with raw SQL
        db_session.expire_all()

        # Verify node is deleted using raw SQL to bypass ORM cache
        result = await db_session.execute(
            text("SELECT id FROM nodes WHERE id = :node_id"),
            {"node_id": str(node_id)},
        )
        deleted_node = result.scalar_one_or_none()
        assert deleted_node is None


# ============================================================================
# Edge Model Behavior Tests
# ============================================================================


class TestEdgeModelBehavior:
    """Test Edge model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_edge_creation_with_required_fields(self, db_session) -> None:
        """Edge should be creatable with required fields."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.id is not None
        assert edge.workflow_id == workflow.id
        assert edge.source_node_id == source.id
        assert edge.target_node_id == target.id

    @pytest.mark.asyncio
    async def test_edge_condition_nullable(self, db_session) -> None:
        """Edge condition should be nullable."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.condition is None

    @pytest.mark.asyncio
    async def test_edge_condition_jsonb(self, db_session) -> None:
        """Edge condition should store JSONB values."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.CONDITION
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        condition = {"operator": "equals", "field": "status", "value": "success"}
        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
            condition=condition,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.condition == condition

    @pytest.mark.asyncio
    async def test_edge_priority_default(self, db_session) -> None:
        """Edge priority should default to 0."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.priority == 0

    @pytest.mark.asyncio
    async def test_edge_source_target_handle_nullable(self, db_session) -> None:
        """Edge source_handle and target_handle should be nullable."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.source_handle is None
        assert edge.target_handle is None

    @pytest.mark.asyncio
    async def test_edge_source_target_handle_values(self, db_session) -> None:
        """Edge source_handle and target_handle should store values."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.CONDITION
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
            source_handle="output-true",
            target_handle="input-main",
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.source_handle == "output-true"
        assert edge.target_handle == "input-main"

    @pytest.mark.asyncio
    async def test_edge_label_nullable(self, db_session) -> None:
        """Edge label should be nullable."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.label is None

    @pytest.mark.asyncio
    async def test_edge_label_value(self, db_session) -> None:
        """Edge label should store value."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
            label="on success",
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.label == "on success"

    @pytest.mark.asyncio
    async def test_edge_created_at_timestamp(self, db_session) -> None:
        """Edge should have auto-generated created_at timestamp."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()
        await db_session.refresh(edge)

        assert edge.created_at is not None

    @pytest.mark.asyncio
    async def test_edge_cascade_delete_with_workflow(self, db_session) -> None:
        """Edges should be deleted when parent workflow is deleted via ORM cascade."""
        from sqlalchemy import text

        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Source", node_type=NodeType.TRIGGER
        )
        target = Node(workflow_id=workflow.id, name="Target", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
        )
        db_session.add(edge)
        await db_session.commit()

        edge_id = edge.id

        # Delete workflow - ORM cascade should delete edges
        await db_session.delete(workflow)
        await db_session.commit()

        # Expire all to clear cache and verify with raw SQL
        db_session.expire_all()

        # Verify edge is deleted using raw SQL to bypass ORM cache
        result = await db_session.execute(
            text("SELECT id FROM edges WHERE id = :edge_id"),
            {"edge_id": str(edge_id)},
        )
        deleted_edge = result.scalar_one_or_none()
        assert deleted_edge is None

    @pytest.mark.asyncio
    async def test_edge_source_node_fk_cascade_schema(self, db_session) -> None:
        """Edge source_node_id FK should have ON DELETE CASCADE defined.

        This test verifies the schema definition. The actual CASCADE behavior
        is enforced by PostgreSQL; SQLite may not enforce FKs by default.
        """

        from app.models.workflow import Edge

        # Verify Edge model has source_node_id attribute
        assert hasattr(Edge, "source_node_id")

        # Get the FK constraint from the model's table
        edge_table = Edge.__table__
        source_fk = None
        for fk in edge_table.foreign_keys:
            if fk.parent.name == "source_node_id":
                source_fk = fk
                break

        # Verify FK exists and has CASCADE ondelete
        assert source_fk is not None
        assert source_fk.ondelete == "CASCADE"

    @pytest.mark.asyncio
    async def test_edge_target_node_fk_cascade_schema(self, db_session) -> None:
        """Edge target_node_id FK should have ON DELETE CASCADE defined.

        This test verifies the schema definition. The actual CASCADE behavior
        is enforced by PostgreSQL; SQLite may not enforce FKs by default.
        """
        from app.models.workflow import Edge

        # Verify Edge model has target_node_id attribute
        assert hasattr(Edge, "target_node_id")

        # Get the FK constraint from the model's table
        edge_table = Edge.__table__
        target_fk = None
        for fk in edge_table.foreign_keys:
            if fk.parent.name == "target_node_id":
                target_fk = fk
                break

        # Verify FK exists and has CASCADE ondelete
        assert target_fk is not None
        assert target_fk.ondelete == "CASCADE"


# ============================================================================
# Edge Constraint Tests (PostgreSQL specific)
# Note: These tests may behave differently in SQLite vs PostgreSQL
# ============================================================================


class TestEdgeConstraints:
    """Test Edge model constraints."""

    @pytest.mark.asyncio
    async def test_edge_unique_constraint_different_edges(self, db_session) -> None:
        """Different edge combinations should be allowed."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node1 = Node(workflow_id=workflow.id, name="Node 1", node_type=NodeType.TRIGGER)
        node2 = Node(workflow_id=workflow.id, name="Node 2", node_type=NodeType.TOOL)
        node3 = Node(workflow_id=workflow.id, name="Node 3", node_type=NodeType.AGENT)
        db_session.add_all([node1, node2, node3])
        await db_session.commit()

        edge1 = Edge(
            workflow_id=workflow.id,
            source_node_id=node1.id,
            target_node_id=node2.id,
        )
        edge2 = Edge(
            workflow_id=workflow.id,
            source_node_id=node2.id,
            target_node_id=node3.id,
        )
        db_session.add_all([edge1, edge2])
        await db_session.commit()

        # Both edges should exist
        assert edge1.id is not None
        assert edge2.id is not None

    @pytest.mark.asyncio
    async def test_edge_same_nodes_different_handles(self, db_session) -> None:
        """Same source/target with different handles should be allowed."""
        from app.models.workflow import Edge, Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        source = Node(
            workflow_id=workflow.id, name="Condition", node_type=NodeType.CONDITION
        )
        target = Node(workflow_id=workflow.id, name="Tool", node_type=NodeType.TOOL)
        db_session.add_all([source, target])
        await db_session.commit()

        edge1 = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
            source_handle="true",
        )
        edge2 = Edge(
            workflow_id=workflow.id,
            source_node_id=source.id,
            target_node_id=target.id,
            source_handle="false",
        )
        db_session.add_all([edge1, edge2])
        await db_session.commit()

        # Both edges should exist
        assert edge1.id is not None
        assert edge2.id is not None


# ============================================================================
# Model Export Tests
# ============================================================================


class TestModelExports:
    """Test that models are properly exported from __init__.py."""

    def test_workflow_exported_from_init(self) -> None:
        """Workflow should be importable from app.models."""
        from app.models import Workflow

        assert Workflow is not None

    def test_node_exported_from_init(self) -> None:
        """Node should be importable from app.models."""
        from app.models import Node

        assert Node is not None

    def test_edge_exported_from_init(self) -> None:
        """Edge should be importable from app.models."""
        from app.models import Edge

        assert Edge is not None
