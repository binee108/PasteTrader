"""Validation tests for Pydantic schemas.

TAG: [SPEC-007] [TESTS] [SCHEMAS] [VALIDATION]
REQ: REQ-001 - Workflow Schema Validation Tests
REQ: REQ-002 - Execution Schema Validation Tests
REQ: REQ-003 - Base Schema Validation Tests
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.enums import ExecutionStatus, LogLevel, NodeType, TriggerType
from app.schemas.base import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from app.schemas.execution import (
    ExecutionContext,
    ExecutionLogBase,
    ExecutionMetadata,
    ExecutionStatistics,
    NodeExecutionBase,
    WorkflowExecutionBase,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
)
from app.schemas.workflow import (
    EdgeBase,
    NodeBase,
    RetryConfig,
    WorkflowBase,
    WorkflowCreate,
    WorkflowGraphUpdate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

# =============================================================================
# Base Schema Tests
# =============================================================================


class TestBaseSchemas:
    """Test suite for base schemas."""

    def test_pagination_params_valid(self):
        """Test valid pagination parameters."""
        params = PaginationParams(page=1, size=20)
        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0

    def test_pagination_params_offset_calculation(self):
        """Test offset calculation."""
        params = PaginationParams(page=3, size=10)
        assert params.offset == 20  # (3 - 1) * 10

    def test_pagination_params_defaults(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20

    def test_pagination_params_invalid_page(self):
        """Test invalid page number raises validation error."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0, size=20)

    def test_pagination_params_invalid_size(self):
        """Test invalid size raises validation error."""
        with pytest.raises(ValidationError):
            PaginationParams(page=1, size=0)

        with pytest.raises(ValidationError):
            PaginationParams(page=1, size=101)

    def test_paginated_response_create(self):
        """Test paginated response creation."""
        items = [{"id": 1}, {"id": 2}]
        response = PaginatedResponse.create(items=items, total=10, page=1, size=2)

        assert response.items == items
        assert response.total == 10
        assert response.page == 1
        assert response.size == 2
        assert response.pages == 5  # (10 + 2 - 1) // 2

    def test_error_response_valid(self):
        """Test valid error response."""
        error = ErrorResponse(error="TestError", message="Test error message")
        assert error.error == "TestError"
        assert error.message == "Test error message"

    def test_success_response_valid(self):
        """Test valid success response."""
        success = SuccessResponse(success=True, message="Operation successful")
        assert success.success is True
        assert success.message == "Operation successful"

    def test_message_response_valid(self):
        """Test valid message response."""
        message = MessageResponse(message="Test message")
        assert message.message == "Test message"


# =============================================================================
# Workflow Schema Tests
# =============================================================================


class TestWorkflowSchemas:
    """Test suite for workflow schemas."""

    def test_workflow_base_valid(self):
        """Test valid workflow base schema."""
        workflow = WorkflowBase(
            name="Test Workflow",
            description="Test description",
            config={"key": "value"},
            variables={"var": "value"},
            is_active=True,
        )
        assert workflow.name == "Test Workflow"
        assert workflow.is_active is True

    def test_workflow_base_defaults(self):
        """Test workflow base default values."""
        workflow = WorkflowBase(name="Test")
        assert workflow.config == {}
        assert workflow.variables == {}
        assert workflow.is_active is True
        assert workflow.description is None

    def test_workflow_create_valid(self):
        """Test valid workflow creation schema."""
        workflow = WorkflowCreate(
            name="Test Workflow",
            config={},
            variables={},
            is_active=True,
        )
        # Note: owner_id is set by the API endpoint, not in the schema
        assert workflow.name == "Test Workflow"
        assert workflow.is_active is True

    def test_workflow_update_valid(self):
        """Test valid workflow update schema."""
        workflow = WorkflowUpdate(
            version=1,
            name="Updated Name",
            is_active=False,
        )
        assert workflow.version == 1
        assert workflow.name == "Updated Name"

    def test_workflow_update_all_optional(self):
        """Test workflow update with minimal fields."""
        workflow = WorkflowUpdate(version=1)
        assert workflow.version == 1

    def test_workflow_response_valid(self, workflow_factory):
        """Test valid workflow response schema."""
        workflow = workflow_factory()
        response = WorkflowResponse.model_validate(workflow)
        assert response.id == workflow.id
        assert response.name == workflow.name
        assert response.version == workflow.version

    def test_workflow_list_response_valid(self, workflow_factory):
        """Test valid workflow list response."""
        workflow = workflow_factory()
        response = WorkflowListResponse.model_validate(workflow)
        assert response.id == workflow.id
        assert response.node_count == 0
        assert response.edge_count == 0

    def test_node_base_valid(self):
        """Test valid node base schema."""
        node = NodeBase(
            name="Test Node",
            node_type=NodeType.TOOL,
            position_x=100.0,
            position_y=200.0,
            tool_id=uuid4(),
        )
        assert node.name == "Test Node"
        assert node.node_type == NodeType.TOOL

    def test_node_base_defaults(self):
        """Test node base default values."""
        node = NodeBase(
            name="Test",
            node_type=NodeType.TRIGGER,
        )
        assert node.position_x == 0.0
        assert node.position_y == 0.0
        assert node.config == {}
        assert node.timeout_seconds == 300

    def test_node_base_tool_type_requires_tool_id(self):
        """Test that tool nodes require tool_id."""
        with pytest.raises(ValidationError):
            NodeBase(
                name="Tool Node",
                node_type=NodeType.TOOL,
                tool_id=None,
            )

    def test_node_base_agent_type_requires_agent_id(self):
        """Test that agent nodes require agent_id."""
        with pytest.raises(ValidationError):
            NodeBase(
                name="Agent Node",
                node_type=NodeType.AGENT,
                agent_id=None,
            )

    def test_retry_config_valid(self):
        """Test valid retry config."""
        config = RetryConfig(
            max_retries=5,
            delay=2.0,
            backoff_multiplier=2.0,
        )
        assert config.max_retries == 5
        assert config.delay == 2.0
        assert config.backoff_multiplier == 2.0

    def test_retry_config_defaults(self):
        """Test retry config default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.delay == 1.0
        assert config.backoff_multiplier == 1.0

    def test_retry_config_invalid_max_retries(self):
        """Test invalid max_retries raises validation error."""
        with pytest.raises(ValidationError):
            RetryConfig(max_retries=11)  # Max is 10

    def test_retry_config_invalid_delay(self):
        """Test invalid delay raises validation error."""
        with pytest.raises(ValidationError):
            RetryConfig(delay=-1.0)  # Must be >= 0

        with pytest.raises(ValidationError):
            RetryConfig(delay=301.0)  # Max is 300

    def test_edge_base_valid(self):
        """Test valid edge base schema."""
        edge = EdgeBase(
            source_node_id=uuid4(),
            target_node_id=uuid4(),
        )
        assert edge.source_handle is None
        assert edge.target_handle is None
        assert edge.priority == 0

    def test_edge_base_self_loop_validation(self):
        """Test that self-loops are rejected."""
        node_id = uuid4()
        with pytest.raises(ValidationError, match="Self-loops are not allowed"):
            EdgeBase(
                source_node_id=node_id,
                target_node_id=node_id,  # Same node
            )

    def test_edge_base_with_full_data(self):
        """Test edge with all fields."""
        edge = EdgeBase(
            source_node_id=uuid4(),
            target_node_id=uuid4(),
            source_handle="output_1",
            target_handle="input_1",
            condition={"type": "expression", "value": "data.status == 'success'"},
            priority=10,
            label="Success path",
        )
        assert edge.source_handle == "output_1"
        assert edge.target_handle == "input_1"
        assert edge.priority == 10
        assert edge.label == "Success path"


# =============================================================================
# Execution Schema Tests
# =============================================================================


class TestExecutionSchemas:
    """Test suite for execution schemas."""

    def test_execution_context_valid(self):
        """Test valid execution context."""
        context = ExecutionContext(
            variables={"user_id": "123"},
            secrets={"API_KEY": "{{vault:key}}"},
            environment={"LOG_LEVEL": "debug"},
        )
        assert context.variables["user_id"] == "123"
        assert context.secrets["API_KEY"] == "{{vault:key}}"

    def test_execution_context_defaults(self):
        """Test execution context default values."""
        context = ExecutionContext()
        assert context.variables == {}
        assert context.secrets == {}
        assert context.environment == {}

    def test_execution_metadata_valid(self):
        """Test valid execution metadata."""
        metadata = ExecutionMetadata(
            triggered_by="user:test@example.com",
            priority=10,
            tags=["production", "high-priority"],
            correlation_id="req-abc123",
        )
        assert metadata.triggered_by == "user:test@example.com"
        assert len(metadata.tags) == 2

    def test_execution_metadata_invalid_tag_length(self):
        """Test that tags with excessive length are rejected."""
        long_tag = "a" * 51  # Max is 50
        with pytest.raises(ValidationError, match="tag must be 50 characters or less"):
            ExecutionMetadata(tags=[long_tag])

    def test_execution_metadata_invalid_priority(self):
        """Test invalid priority range."""
        with pytest.raises(ValidationError):
            ExecutionMetadata(priority=101)  # Max is 100

        with pytest.raises(ValidationError):
            ExecutionMetadata(priority=-101)  # Min is -100

    def test_workflow_execution_base_valid(self):
        """Test valid workflow execution base."""
        execution = WorkflowExecutionBase(
            workflow_id=uuid4(),
            trigger_type=TriggerType.MANUAL,
            input_data={"test": "data"},
        )
        assert execution.trigger_type == TriggerType.MANUAL
        assert execution.input_data == {"test": "data"}

    def test_workflow_execution_create_valid(self):
        """Test valid workflow execution creation."""
        execution = WorkflowExecutionCreate(
            workflow_id=uuid4(),
            trigger_type=TriggerType.EVENT,
            input_data={"event": "data"},
            context=ExecutionContext(),
            metadata_=ExecutionMetadata(),
        )
        assert execution.trigger_type == TriggerType.EVENT

    def test_node_execution_base_valid(self):
        """Test valid node execution base."""
        node_exec = NodeExecutionBase(
            node_id=uuid4(),
            execution_order=0,
            input_data={"key": "value"},
        )
        assert node_exec.execution_order == 0

    def test_execution_log_base_valid(self):
        """Test valid execution log base."""
        log = ExecutionLogBase(
            level=LogLevel.INFO,
            message="Test log message",
            data={"key": "value"},
        )
        assert log.level == LogLevel.INFO
        assert log.message == "Test log message"

    def test_execution_log_base_invalid_message_empty(self):
        """Test that empty message is rejected."""
        with pytest.raises(ValidationError):
            ExecutionLogBase(
                level=LogLevel.INFO,
                message="",  # Empty not allowed
            )

    def test_execution_log_base_invalid_message_too_long(self):
        """Test that overly long message is rejected."""
        long_message = "a" * 10001  # Max is 10000
        with pytest.raises(ValidationError):
            ExecutionLogBase(
                level=LogLevel.INFO,
                message=long_message,
            )

    def test_execution_statistics_valid(self):
        """Test valid execution statistics."""
        stats = ExecutionStatistics(
            total_executions=100,
            completed=80,
            failed=10,
            running=5,
            pending=5,
            cancelled=0,
            avg_duration_seconds=30.5,
            success_rate=0.89,
        )
        assert stats.total_executions == 100
        assert stats.success_rate == 0.89

    def test_execution_statistics_success_rate_calculation(self):
        """Test that success rate is properly bounded."""
        stats = ExecutionStatistics(
            total_executions=10,
            completed=10,
            failed=0,
            running=0,
            pending=0,
            cancelled=0,
            success_rate=1.0,
        )
        assert stats.success_rate == 1.0


# =============================================================================
# Computed Field Tests
# =============================================================================


class TestComputedFields:
    """Test suite for computed fields in schemas."""

    def test_workflow_execution_response_duration_seconds(self):
        """Test duration_seconds computed field."""
        from datetime import timedelta

        now = datetime.now(UTC)
        execution = WorkflowExecutionResponse(
            id=uuid4(),
            workflow_id=uuid4(),
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
            started_at=now,
            ended_at=now + timedelta(seconds=30),  # 30 seconds later
            created_at=now,
            updated_at=now,
            input_data={},
            context={},
            metadata_={},
        )
        assert execution.duration_seconds == 30.0

    def test_workflow_execution_response_duration_none(self):
        """Test duration_seconds when timestamps missing."""
        execution = WorkflowExecutionResponse(
            id=uuid4(),
            workflow_id=uuid4(),
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.PENDING,
            started_at=None,
            ended_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            input_data={},
            context={},
            metadata_={},
        )
        assert execution.duration_seconds is None

    def test_workflow_execution_response_is_terminal(self):
        """Test is_terminal computed field."""
        now = datetime.now(UTC)

        # Terminal status
        execution = WorkflowExecutionResponse(
            id=uuid4(),
            workflow_id=uuid4(),
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            created_at=now,
            updated_at=now,
            input_data={},
            context={},
            metadata_={},
        )
        assert execution.is_terminal is True

        # Non-terminal status
        execution_running = WorkflowExecutionResponse(
            id=uuid4(),
            workflow_id=uuid4(),
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.RUNNING,
            started_at=now,
            ended_at=None,
            created_at=now,
            updated_at=now,
            input_data={},
            context={},
            metadata_={},
        )
        assert execution_running.is_terminal is False


# =============================================================================
# Graph Update Schema Tests
# =============================================================================


class TestGraphUpdateSchema:
    """Test suite for workflow graph update schema."""

    def test_workflow_graph_update_valid(self):
        """Test valid workflow graph update."""
        graph = WorkflowGraphUpdate(
            version=1,
            nodes=[],
            edges=[],
        )
        assert graph.version == 1
        assert graph.nodes == []
        assert graph.edges == []

    def test_workflow_graph_update_with_data(self):
        """Test workflow graph update with nodes and edges."""
        node1_id = uuid4()
        node2_id = uuid4()

        graph = WorkflowGraphUpdate(
            version=1,
            nodes=[
                {
                    "name": "Node 1",
                    "node_type": NodeType.TOOL,
                    "position_x": 100.0,
                    "position_y": 200.0,
                    "tool_id": uuid4(),
                },
                {
                    "name": "Node 2",
                    "node_type": NodeType.AGENT,
                    "position_x": 300.0,
                    "position_y": 400.0,
                    "agent_id": uuid4(),
                },
            ],
            edges=[
                {
                    "source_node_id": node1_id,
                    "target_node_id": node2_id,
                }
            ],
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_workflow_graph_update_defaults(self):
        """Test workflow graph update default values."""
        graph = WorkflowGraphUpdate(version=1)
        assert graph.nodes == []
        assert graph.edges == []
