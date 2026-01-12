"""Tests for Execution Tracking Models (WorkflowExecution, NodeExecution, ExecutionLog).

TAG: [SPEC-005] [DATABASE] [EXECUTION] [TRACKING]
REQ: REQ-001 - WorkflowExecution Model Definition
REQ: REQ-002 - NodeExecution Model Definition
REQ: REQ-003 - ExecutionLog Model Definition
REQ: REQ-004 - Workflow-WorkflowExecution Relationship
REQ: REQ-005 - WorkflowExecution-NodeExecution Relationship (CASCADE)
REQ: REQ-006 - WorkflowExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-007 - NodeExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-008 - State Transition Helpers
REQ: REQ-009 - Duration Properties
"""

import uuid
from datetime import UTC, datetime, timedelta

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
from app.models.enums import ExecutionStatus, LogLevel, NodeType, TriggerType

# Test will use SQLite for unit testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ============================================================================
# LogLevel Enum Tests
# ============================================================================


class TestLogLevelEnum:
    """Test LogLevel enum values for execution logs."""

    def test_loglevel_debug_exists(self) -> None:
        """LogLevel should have DEBUG value."""
        assert LogLevel.DEBUG.value == "debug"

    def test_loglevel_info_exists(self) -> None:
        """LogLevel should have INFO value."""
        assert LogLevel.INFO.value == "info"

    def test_loglevel_warning_exists(self) -> None:
        """LogLevel should have WARNING value."""
        assert LogLevel.WARNING.value == "warning"

    def test_loglevel_error_exists(self) -> None:
        """LogLevel should have ERROR value."""
        assert LogLevel.ERROR.value == "error"

    def test_loglevel_str_method(self) -> None:
        """LogLevel __str__ should return value."""
        assert str(LogLevel.DEBUG) == "debug"
        assert str(LogLevel.INFO) == "info"
        assert str(LogLevel.WARNING) == "warning"
        assert str(LogLevel.ERROR) == "error"

    def test_loglevel_exportable(self) -> None:
        """LogLevel should be importable from app.models."""
        from app.models import LogLevel as ImportedLogLevel

        assert ImportedLogLevel is LogLevel


# ============================================================================
# WorkflowExecution Model Structure Tests
# ============================================================================


class TestWorkflowExecutionModelStructure:
    """Test WorkflowExecution model class structure."""

    def test_workflowexecution_class_exists(self) -> None:
        """WorkflowExecution class should exist in models.execution module."""
        from app.models.execution import WorkflowExecution

        assert WorkflowExecution is not None

    def test_workflowexecution_has_tablename(self) -> None:
        """WorkflowExecution should have __tablename__ = 'workflow_executions'."""
        from app.models.execution import WorkflowExecution

        assert WorkflowExecution.__tablename__ == "workflow_executions"

    def test_workflowexecution_has_id_attribute(self) -> None:
        """WorkflowExecution should have id attribute (from UUIDMixin)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "id")

    def test_workflowexecution_has_workflow_id_attribute(self) -> None:
        """WorkflowExecution should have workflow_id attribute (FK to workflows)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "workflow_id")

    def test_workflowexecution_has_trigger_type_attribute(self) -> None:
        """WorkflowExecution should have trigger_type attribute."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "trigger_type")

    def test_workflowexecution_has_status_attribute(self) -> None:
        """WorkflowExecution should have status attribute."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "status")

    def test_workflowexecution_has_started_at_attribute(self) -> None:
        """WorkflowExecution should have started_at attribute."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "started_at")

    def test_workflowexecution_has_ended_at_attribute(self) -> None:
        """WorkflowExecution should have ended_at attribute."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "ended_at")

    def test_workflowexecution_has_input_data_attribute(self) -> None:
        """WorkflowExecution should have input_data attribute (JSONB)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "input_data")

    def test_workflowexecution_has_output_data_attribute(self) -> None:
        """WorkflowExecution should have output_data attribute (JSONB, nullable)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "output_data")

    def test_workflowexecution_has_error_message_attribute(self) -> None:
        """WorkflowExecution should have error_message attribute."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "error_message")

    def test_workflowexecution_has_context_attribute(self) -> None:
        """WorkflowExecution should have context attribute (JSONB)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "context")

    def test_workflowexecution_has_metadata_attribute(self) -> None:
        """WorkflowExecution should have metadata_ attribute (JSONB)."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "metadata_")

    def test_workflowexecution_has_timestamp_attributes(self) -> None:
        """WorkflowExecution should have created_at and updated_at attributes."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "created_at")
        assert hasattr(WorkflowExecution, "updated_at")

    def test_workflowexecution_has_workflow_relationship(self) -> None:
        """WorkflowExecution should have workflow relationship."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "workflow")

    def test_workflowexecution_has_node_executions_relationship(self) -> None:
        """WorkflowExecution should have node_executions relationship."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "node_executions")

    def test_workflowexecution_has_logs_relationship(self) -> None:
        """WorkflowExecution should have logs relationship."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "logs")

    def test_workflowexecution_has_duration_seconds_property(self) -> None:
        """WorkflowExecution should have duration_seconds property."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "duration_seconds")

    def test_workflowexecution_has_is_terminal_property(self) -> None:
        """WorkflowExecution should have is_terminal property."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "is_terminal")

    def test_workflowexecution_has_start_method(self) -> None:
        """WorkflowExecution should have start() method."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "start")
        assert callable(WorkflowExecution.start)

    def test_workflowexecution_has_complete_method(self) -> None:
        """WorkflowExecution should have complete() method."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "complete")
        assert callable(WorkflowExecution.complete)

    def test_workflowexecution_has_fail_method(self) -> None:
        """WorkflowExecution should have fail() method."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "fail")
        assert callable(WorkflowExecution.fail)

    def test_workflowexecution_has_cancel_method(self) -> None:
        """WorkflowExecution should have cancel() method."""
        from app.models.execution import WorkflowExecution

        assert hasattr(WorkflowExecution, "cancel")
        assert callable(WorkflowExecution.cancel)


# ============================================================================
# NodeExecution Model Structure Tests
# ============================================================================


class TestNodeExecutionModelStructure:
    """Test NodeExecution model class structure."""

    def test_nodeexecution_class_exists(self) -> None:
        """NodeExecution class should exist in models.execution module."""
        from app.models.execution import NodeExecution

        assert NodeExecution is not None

    def test_nodeexecution_has_tablename(self) -> None:
        """NodeExecution should have __tablename__ = 'node_executions'."""
        from app.models.execution import NodeExecution

        assert NodeExecution.__tablename__ == "node_executions"

    def test_nodeexecution_has_id_attribute(self) -> None:
        """NodeExecution should have id attribute (from UUIDMixin)."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "id")

    def test_nodeexecution_has_workflow_execution_id_attribute(self) -> None:
        """NodeExecution should have workflow_execution_id attribute (FK)."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "workflow_execution_id")

    def test_nodeexecution_has_node_id_attribute(self) -> None:
        """NodeExecution should have node_id attribute (FK to nodes)."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "node_id")

    def test_nodeexecution_has_status_attribute(self) -> None:
        """NodeExecution should have status attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "status")

    def test_nodeexecution_has_started_at_attribute(self) -> None:
        """NodeExecution should have started_at attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "started_at")

    def test_nodeexecution_has_ended_at_attribute(self) -> None:
        """NodeExecution should have ended_at attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "ended_at")

    def test_nodeexecution_has_input_data_attribute(self) -> None:
        """NodeExecution should have input_data attribute (JSONB)."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "input_data")

    def test_nodeexecution_has_output_data_attribute(self) -> None:
        """NodeExecution should have output_data attribute (JSONB, nullable)."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "output_data")

    def test_nodeexecution_has_error_message_attribute(self) -> None:
        """NodeExecution should have error_message attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "error_message")

    def test_nodeexecution_has_error_traceback_attribute(self) -> None:
        """NodeExecution should have error_traceback attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "error_traceback")

    def test_nodeexecution_has_retry_count_attribute(self) -> None:
        """NodeExecution should have retry_count attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "retry_count")

    def test_nodeexecution_has_execution_order_attribute(self) -> None:
        """NodeExecution should have execution_order attribute."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "execution_order")

    def test_nodeexecution_has_timestamp_attributes(self) -> None:
        """NodeExecution should have created_at and updated_at attributes."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "created_at")
        assert hasattr(NodeExecution, "updated_at")

    def test_nodeexecution_has_workflow_execution_relationship(self) -> None:
        """NodeExecution should have workflow_execution relationship."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "workflow_execution")

    def test_nodeexecution_has_node_relationship(self) -> None:
        """NodeExecution should have node relationship."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "node")

    def test_nodeexecution_has_logs_relationship(self) -> None:
        """NodeExecution should have logs relationship."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "logs")

    def test_nodeexecution_has_duration_seconds_property(self) -> None:
        """NodeExecution should have duration_seconds property."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "duration_seconds")

    def test_nodeexecution_has_can_retry_property(self) -> None:
        """NodeExecution should have can_retry property."""
        from app.models.execution import NodeExecution

        assert hasattr(NodeExecution, "can_retry")


# ============================================================================
# ExecutionLog Model Structure Tests
# ============================================================================


class TestExecutionLogModelStructure:
    """Test ExecutionLog model class structure."""

    def test_executionlog_class_exists(self) -> None:
        """ExecutionLog class should exist in models.execution module."""
        from app.models.execution import ExecutionLog

        assert ExecutionLog is not None

    def test_executionlog_has_tablename(self) -> None:
        """ExecutionLog should have __tablename__ = 'execution_logs'."""
        from app.models.execution import ExecutionLog

        assert ExecutionLog.__tablename__ == "execution_logs"

    def test_executionlog_has_id_attribute(self) -> None:
        """ExecutionLog should have id attribute (from UUIDMixin)."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "id")

    def test_executionlog_has_workflow_execution_id_attribute(self) -> None:
        """ExecutionLog should have workflow_execution_id attribute (FK)."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "workflow_execution_id")

    def test_executionlog_has_node_execution_id_attribute(self) -> None:
        """ExecutionLog should have node_execution_id attribute (FK, nullable)."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "node_execution_id")

    def test_executionlog_has_level_attribute(self) -> None:
        """ExecutionLog should have level attribute (LogLevel enum)."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "level")

    def test_executionlog_has_message_attribute(self) -> None:
        """ExecutionLog should have message attribute."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "message")

    def test_executionlog_has_data_attribute(self) -> None:
        """ExecutionLog should have data attribute (JSONB, nullable)."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "data")

    def test_executionlog_has_timestamp_attribute(self) -> None:
        """ExecutionLog should have timestamp attribute."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "timestamp")

    def test_executionlog_has_workflow_execution_relationship(self) -> None:
        """ExecutionLog should have workflow_execution relationship."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "workflow_execution")

    def test_executionlog_has_node_execution_relationship(self) -> None:
        """ExecutionLog should have node_execution relationship."""
        from app.models.execution import ExecutionLog

        assert hasattr(ExecutionLog, "node_execution")


# ============================================================================
# Database Fixtures
# ============================================================================


# Create mock models for testing FK references
_test_models_defined = False
_MockUserClass = None


def get_mock_classes():
    """Get or create mock model classes for testing."""
    global _test_models_defined, _MockUserClass

    if not _test_models_defined:
        from typing import ClassVar

        from app.models.base import Base, UUIDMixin

        class TestUserExecution(UUIDMixin, Base):
            """Mock User model for testing FK references."""

            __tablename__ = "users"
            __table_args__: ClassVar[dict[str, bool]] = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        _MockUserClass = TestUserExecution
        _test_models_defined = True

    return _MockUserClass


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
# WorkflowExecution Model Behavior Tests
# ============================================================================


class TestWorkflowExecutionModelBehavior:
    """Test WorkflowExecution model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_workflowexecution_creation_with_required_fields(
        self, db_session
    ) -> None:
        """WorkflowExecution should be creatable with required fields."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        # Create parent workflow
        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.id is not None
        assert execution.workflow_id == workflow.id
        assert str(execution.trigger_type) == "manual"
        assert str(execution.status) == "pending"

    @pytest.mark.asyncio
    async def test_workflowexecution_status_default_pending(self, db_session) -> None:
        """WorkflowExecution status should default to PENDING."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.status == ExecutionStatus.PENDING

    @pytest.mark.asyncio
    async def test_workflowexecution_input_data_default(self, db_session) -> None:
        """WorkflowExecution input_data should default to empty dict."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.input_data == {}

    @pytest.mark.asyncio
    async def test_workflowexecution_context_default(self, db_session) -> None:
        """WorkflowExecution context should default to empty dict."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.context == {}

    @pytest.mark.asyncio
    async def test_workflowexecution_metadata_default(self, db_session) -> None:
        """WorkflowExecution metadata_ should default to empty dict."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.metadata_ == {}

    @pytest.mark.asyncio
    async def test_workflowexecution_started_at_nullable(self, db_session) -> None:
        """WorkflowExecution started_at should be nullable."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.started_at is None
        assert execution.ended_at is None

    @pytest.mark.asyncio
    async def test_workflowexecution_output_data_nullable(self, db_session) -> None:
        """WorkflowExecution output_data should be nullable."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.output_data is None

    @pytest.mark.asyncio
    async def test_workflowexecution_error_message_nullable(self, db_session) -> None:
        """WorkflowExecution error_message should be nullable."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.error_message is None

    @pytest.mark.asyncio
    async def test_workflowexecution_timestamps(self, db_session) -> None:
        """WorkflowExecution should have auto-generated timestamps."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()
        await db_session.refresh(execution)

        assert execution.created_at is not None
        assert execution.updated_at is not None


# ============================================================================
# WorkflowExecution State Transition Tests
# ============================================================================


class TestWorkflowExecutionStateTransitions:
    """Test WorkflowExecution state transition methods."""

    @pytest.mark.asyncio
    async def test_start_method_transitions_to_running(self, db_session) -> None:
        """start() should change status to RUNNING and set started_at."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        execution.start()

        assert execution.status == ExecutionStatus.RUNNING
        assert execution.started_at is not None

    @pytest.mark.asyncio
    async def test_start_method_fails_if_not_pending(self, db_session) -> None:
        """start() should raise ValueError if not in PENDING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
        )
        db_session.add(execution)
        await db_session.commit()

        with pytest.raises(ValueError, match="Cannot start execution"):
            execution.start()

    @pytest.mark.asyncio
    async def test_complete_method_transitions_to_completed(self, db_session) -> None:
        """complete() should change status to COMPLETED and set ended_at."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.commit()

        output = {"result": "success"}
        execution.complete(output_data=output)

        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.ended_at is not None
        assert execution.output_data == output

    @pytest.mark.asyncio
    async def test_complete_method_fails_if_not_running(self, db_session) -> None:
        """complete() should raise ValueError if not in RUNNING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        with pytest.raises(ValueError, match="Cannot complete execution"):
            execution.complete()

    @pytest.mark.asyncio
    async def test_fail_method_transitions_to_failed(self, db_session) -> None:
        """fail() should change status to FAILED and set error_message."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.commit()

        execution.fail("Something went wrong")

        assert execution.status == ExecutionStatus.FAILED
        assert execution.ended_at is not None
        assert execution.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_fail_method_fails_if_not_running(self, db_session) -> None:
        """fail() should raise ValueError if not in RUNNING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        with pytest.raises(ValueError, match="Cannot fail execution"):
            execution.fail("Error")

    @pytest.mark.asyncio
    async def test_cancel_method_from_pending(self, db_session) -> None:
        """cancel() should work from PENDING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        execution.cancel()

        assert execution.status == ExecutionStatus.CANCELLED
        assert execution.ended_at is not None

    @pytest.mark.asyncio
    async def test_cancel_method_from_running(self, db_session) -> None:
        """cancel() should work from RUNNING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        db_session.add(execution)
        await db_session.commit()

        execution.cancel()

        assert execution.status == ExecutionStatus.CANCELLED
        assert execution.ended_at is not None

    @pytest.mark.asyncio
    async def test_cancel_method_fails_if_already_terminal(self, db_session) -> None:
        """cancel() should raise ValueError if already in terminal state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
        )
        db_session.add(execution)
        await db_session.commit()

        with pytest.raises(ValueError, match="Cannot cancel execution"):
            execution.cancel()


# ============================================================================
# WorkflowExecution Property Tests
# ============================================================================


class TestWorkflowExecutionProperties:
    """Test WorkflowExecution computed properties."""

    @pytest.mark.asyncio
    async def test_duration_seconds_returns_none_without_times(
        self, db_session
    ) -> None:
        """duration_seconds should return None if started_at or ended_at is None."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.duration_seconds is None

    @pytest.mark.asyncio
    async def test_duration_seconds_calculates_correctly(self, db_session) -> None:
        """duration_seconds should calculate correct duration."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        started = datetime.now(UTC)
        ended = started + timedelta(seconds=30)

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
            started_at=started,
            ended_at=ended,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.duration_seconds == 30.0

    @pytest.mark.asyncio
    async def test_is_terminal_for_pending(self, db_session) -> None:
        """is_terminal should return False for PENDING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is False

    @pytest.mark.asyncio
    async def test_is_terminal_for_running(self, db_session) -> None:
        """is_terminal should return False for RUNNING state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is False

    @pytest.mark.asyncio
    async def test_is_terminal_for_completed(self, db_session) -> None:
        """is_terminal should return True for COMPLETED state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is True

    @pytest.mark.asyncio
    async def test_is_terminal_for_failed(self, db_session) -> None:
        """is_terminal should return True for FAILED state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.FAILED,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is True

    @pytest.mark.asyncio
    async def test_is_terminal_for_cancelled(self, db_session) -> None:
        """is_terminal should return True for CANCELLED state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.CANCELLED,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is True

    @pytest.mark.asyncio
    async def test_is_terminal_for_skipped(self, db_session) -> None:
        """is_terminal should return True for SKIPPED state."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.SKIPPED,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.is_terminal is True


# ============================================================================
# NodeExecution Model Behavior Tests
# ============================================================================


class TestNodeExecutionModelBehavior:
    """Test NodeExecution model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_nodeexecution_creation_with_required_fields(
        self, db_session
    ) -> None:
        """NodeExecution should be creatable with required fields."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.id is not None
        assert node_execution.workflow_execution_id == execution.id
        assert node_execution.node_id == node.id
        assert node_execution.execution_order == 1

    @pytest.mark.asyncio
    async def test_nodeexecution_status_default_pending(self, db_session) -> None:
        """NodeExecution status should default to PENDING."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.status == ExecutionStatus.PENDING

    @pytest.mark.asyncio
    async def test_nodeexecution_retry_count_default(self, db_session) -> None:
        """NodeExecution retry_count should default to 0."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.retry_count == 0

    @pytest.mark.asyncio
    async def test_nodeexecution_input_data_default(self, db_session) -> None:
        """NodeExecution input_data should default to empty dict."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.input_data == {}

    @pytest.mark.asyncio
    async def test_nodeexecution_nullable_fields(self, db_session) -> None:
        """NodeExecution nullable fields should be None by default."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.started_at is None
        assert node_execution.ended_at is None
        assert node_execution.output_data is None
        assert node_execution.error_message is None
        assert node_execution.error_traceback is None

    @pytest.mark.asyncio
    async def test_nodeexecution_duration_seconds(self, db_session) -> None:
        """NodeExecution duration_seconds should calculate correctly."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        started = datetime.now(UTC)
        ended = started + timedelta(seconds=15)

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            started_at=started,
            ended_at=ended,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.duration_seconds == 15.0

    @pytest.mark.asyncio
    async def test_nodeexecution_duration_seconds_returns_none_without_times(
        self, db_session
    ) -> None:
        """NodeExecution duration_seconds should return None without started_at or ended_at."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        # Only started_at is set, not ended_at
        started = datetime.now(UTC)
        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            started_at=started,
            # ended_at is None
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        # Should return None when ended_at is not set
        assert node_execution.duration_seconds is None

    @pytest.mark.asyncio
    async def test_nodeexecution_can_retry_when_failed(self, db_session) -> None:
        """NodeExecution can_retry should return True when failed and retries available."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TRIGGER,
            retry_config={"max_retries": 3, "delay": 1},
        )
        db_session.add(node)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            status=ExecutionStatus.FAILED,
            retry_count=1,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        # Eagerly load the node relationship
        await db_session.refresh(node_execution, ["node"])

        assert node_execution.can_retry is True

    @pytest.mark.asyncio
    async def test_nodeexecution_can_retry_uses_default_max_without_retry_config(
        self, db_session
    ) -> None:
        """NodeExecution can_retry should use default max_retries=3 when node has no retry_config."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        # Node without retry_config
        node = Node(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TRIGGER,
            # No retry_config set
        )
        db_session.add(node)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            status=ExecutionStatus.FAILED,
            retry_count=2,  # Less than default max of 3
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        # Eagerly load the node relationship
        await db_session.refresh(node_execution, ["node"])

        # Should use default max_retries=3
        assert node_execution.can_retry is True

    @pytest.mark.asyncio
    async def test_nodeexecution_cannot_retry_when_max_reached(
        self, db_session
    ) -> None:
        """NodeExecution can_retry should return False when max retries reached."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        node = Node(
            workflow_id=workflow.id,
            name="Test Node",
            node_type=NodeType.TRIGGER,
            retry_config={"max_retries": 3, "delay": 1},
        )
        db_session.add(node)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            status=ExecutionStatus.FAILED,
            retry_count=3,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        # Eagerly load the node relationship
        await db_session.refresh(node_execution, ["node"])

        assert node_execution.can_retry is False

    @pytest.mark.asyncio
    async def test_nodeexecution_cannot_retry_if_not_failed(self, db_session) -> None:
        """NodeExecution can_retry should return False if not in FAILED state."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
            status=ExecutionStatus.COMPLETED,
        )
        db_session.add(node_execution)
        await db_session.commit()
        await db_session.refresh(node_execution)

        assert node_execution.can_retry is False


# ============================================================================
# ExecutionLog Model Behavior Tests
# ============================================================================


class TestExecutionLogModelBehavior:
    """Test ExecutionLog model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_executionlog_creation_with_required_fields(self, db_session) -> None:
        """ExecutionLog should be creatable with required fields."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Workflow started",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.workflow_execution_id == execution.id
        assert str(log.level) == "info"
        assert log.message == "Workflow started"

    @pytest.mark.asyncio
    async def test_executionlog_timestamp_auto_generated(self, db_session) -> None:
        """ExecutionLog timestamp should be auto-generated."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Test log",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.timestamp is not None

    @pytest.mark.asyncio
    async def test_executionlog_node_execution_nullable(self, db_session) -> None:
        """ExecutionLog node_execution_id should be nullable."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Workflow-level log",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.node_execution_id is None

    @pytest.mark.asyncio
    async def test_executionlog_with_node_execution(self, db_session) -> None:
        """ExecutionLog should support node_execution_id."""
        from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            node_execution_id=node_execution.id,
            level=LogLevel.DEBUG,
            message="Node-level log",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.node_execution_id == node_execution.id

    @pytest.mark.asyncio
    async def test_executionlog_data_nullable(self, db_session) -> None:
        """ExecutionLog data should be nullable."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Log without data",
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.data is None

    @pytest.mark.asyncio
    async def test_executionlog_with_data(self, db_session) -> None:
        """ExecutionLog should support JSONB data."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        data = {"key": "value", "count": 42}
        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Log with data",
            data=data,
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.data == data

    @pytest.mark.asyncio
    async def test_executionlog_all_levels(self, db_session) -> None:
        """ExecutionLog should support all LogLevel values."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]
        for level in levels:
            log = ExecutionLog(
                workflow_execution_id=execution.id,
                level=level,
                message=f"Log at {level.value} level",
            )
            db_session.add(log)

        await db_session.commit()

        # Verify all logs were created using relationship
        await db_session.refresh(execution, ["logs"])
        assert len(execution.logs) == 4


# ============================================================================
# Relationship Tests
# ============================================================================


class TestExecutionRelationships:
    """Test relationships between execution models."""

    def test_workflow_has_executions_relationship(self) -> None:
        """Workflow should have executions relationship."""
        from app.models.workflow import Workflow

        assert hasattr(Workflow, "executions")

    @pytest.mark.asyncio
    async def test_workflow_executions_relationship_works(self, db_session) -> None:
        """Workflow.executions relationship should return WorkflowExecutions."""
        from app.models.execution import WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        await db_session.refresh(workflow, ["executions"])

        assert len(workflow.executions) == 1
        assert workflow.executions[0].id == execution.id


# ============================================================================
# CASCADE Delete Tests
# ============================================================================


class TestExecutionCascadeDeletes:
    """Test CASCADE delete behavior for execution models."""

    @pytest.mark.asyncio
    async def test_nodeexecution_cascade_delete_with_workflowexecution(
        self, db_session
    ) -> None:
        """NodeExecutions should be deleted when WorkflowExecution is deleted."""
        from app.models.execution import NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()

        node_execution_id = node_execution.id

        # Delete WorkflowExecution
        await db_session.delete(execution)
        await db_session.commit()

        db_session.expire_all()

        # Verify NodeExecution is deleted via ORM cascade
        from sqlalchemy import select

        result = await db_session.execute(
            select(NodeExecution).where(NodeExecution.id == node_execution_id)
        )
        deleted = result.scalar_one_or_none()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_executionlog_cascade_delete_with_workflowexecution(
        self, db_session
    ) -> None:
        """ExecutionLogs should be deleted when WorkflowExecution is deleted."""
        from app.models.execution import ExecutionLog, WorkflowExecution
        from app.models.workflow import Workflow

        workflow = Workflow(owner_id=uuid.uuid4(), name="Test Workflow")
        db_session.add(workflow)
        await db_session.commit()

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            level=LogLevel.INFO,
            message="Test log",
        )
        db_session.add(log)
        await db_session.commit()

        log_id = log.id

        # Delete WorkflowExecution
        await db_session.delete(execution)
        await db_session.commit()

        db_session.expire_all()

        # Verify ExecutionLog is deleted via ORM cascade
        from sqlalchemy import select

        result = await db_session.execute(
            select(ExecutionLog).where(ExecutionLog.id == log_id)
        )
        deleted = result.scalar_one_or_none()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_executionlog_cascade_delete_with_nodeexecution(
        self, db_session
    ) -> None:
        """ExecutionLogs linked to NodeExecution should be deleted with it."""
        from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
        from app.models.workflow import Node, Workflow

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

        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_type=TriggerType.MANUAL,
        )
        db_session.add(execution)
        await db_session.commit()

        node_execution = NodeExecution(
            workflow_execution_id=execution.id,
            node_id=node.id,
            execution_order=1,
        )
        db_session.add(node_execution)
        await db_session.commit()

        log = ExecutionLog(
            workflow_execution_id=execution.id,
            node_execution_id=node_execution.id,
            level=LogLevel.DEBUG,
            message="Node-level log",
        )
        db_session.add(log)
        await db_session.commit()

        log_id = log.id

        # Delete NodeExecution
        await db_session.delete(node_execution)
        await db_session.commit()

        db_session.expire_all()

        # Verify ExecutionLog is deleted via ORM cascade
        from sqlalchemy import select

        result = await db_session.execute(
            select(ExecutionLog).where(ExecutionLog.id == log_id)
        )
        deleted = result.scalar_one_or_none()
        assert deleted is None


# ============================================================================
# Model Export Tests
# ============================================================================


class TestExecutionModelExports:
    """Test that execution models are properly exported from __init__.py."""

    def test_workflowexecution_exported_from_init(self) -> None:
        """WorkflowExecution should be importable from app.models."""
        from app.models import WorkflowExecution

        assert WorkflowExecution is not None

    def test_nodeexecution_exported_from_init(self) -> None:
        """NodeExecution should be importable from app.models."""
        from app.models import NodeExecution

        assert NodeExecution is not None

    def test_executionlog_exported_from_init(self) -> None:
        """ExecutionLog should be importable from app.models."""
        from app.models import ExecutionLog

        assert ExecutionLog is not None

    def test_loglevel_exported_from_init(self) -> None:
        """LogLevel should be importable from app.models."""
        from app.models import LogLevel

        assert LogLevel is not None
