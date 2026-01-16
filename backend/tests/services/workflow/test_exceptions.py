"""Tests for workflow execution exceptions.

TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
REQ: REQ-011-001 - Exception handling
"""

import pytest

from app.services.workflow.exceptions import (
    ConditionEvaluationError,
    CycleDetectedError,
    DAGValidationError,
    ExecutionCancelledError,
    ExecutionError,
    GraphTooLargeError,
    InvalidNodeReferenceError,
    NodeExecutionError,
    NodeTimeoutError,
    ValidationTimeoutError,
)


class TestExecutionError:
    """Tests for ExecutionError base exception.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
    """

    def test_execution_error_creation(self) -> None:
        """Test creating ExecutionError with message.

        TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
        """
        error = ExecutionError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"


class TestNodeTimeoutError:
    """Tests for NodeTimeoutError.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
    """

    def test_node_timeout_error_creation(self) -> None:
        """Test creating NodeTimeoutError with node_id and timeout.

        TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        node_id = uuid4()
        timeout = 30.0

        error = NodeTimeoutError(node_id=node_id, timeout_seconds=timeout)

        assert str(node_id)[:8] in str(error)
        assert "30.0" in str(error)
        assert error.node_id == node_id
        assert error.timeout_seconds == timeout


class TestNodeExecutionError:
    """Tests for NodeExecutionError.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
    """

    def test_node_execution_error_creation(self) -> None:
        """Test creating NodeExecutionError with node_id and message.

        TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        node_id = uuid4()
        original_error = ValueError("Original error")

        error = NodeExecutionError(
            node_id=node_id, message="Node failed", original_error=original_error
        )

        assert str(node_id)[:8] in str(error)
        assert "Node failed" in str(error)
        assert error.node_id == node_id
        assert error.message == "Node failed"
        assert error.original_error == original_error


class TestExecutionCancelledError:
    """Tests for ExecutionCancelledError.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
    """

    def test_execution_cancelled_error_creation(self) -> None:
        """Test creating ExecutionCancelledError with execution_id.

        TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        execution_id = uuid4()
        error = ExecutionCancelledError(execution_id=execution_id)

        assert str(execution_id)[:8] in str(error)
        assert error.execution_id == execution_id


class TestConditionEvaluationError:
    """Tests for ConditionEvaluationError.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
    """

    def test_condition_evaluation_error_creation(self) -> None:
        """Test creating ConditionEvaluationError with node_id and reason.

        TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        node_id = uuid4()
        error = ConditionEvaluationError(node_id=node_id, reason="Invalid condition")

        assert str(node_id)[:8] in str(error)
        assert "Invalid condition" in str(error)
        assert error.node_id == node_id
        assert error.reason == "Invalid condition"


# ============================================================================
# SPEC-010 DAG Validation Exception Tests
# ============================================================================


class TestDAGValidationError:
    """Tests for DAGValidationError base exception.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
    """

    def test_dag_validation_error_creation(self) -> None:
        """Test creating DAGValidationError with message and error_code.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        error = DAGValidationError(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details={"node_count": 5},
        )

        assert str(error) == "Validation failed"
        assert error.message == "Validation failed"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details == {"node_count": 5}

    def test_dag_validation_error_without_details(self) -> None:
        """Test creating DAGValidationError without details.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        error = DAGValidationError(message="Simple error", error_code="SIMPLE_ERROR")

        assert error.details == {}


class TestCycleDetectedError:
    """Tests for CycleDetectedError.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
    """

    def test_cycle_detected_error_creation(self) -> None:
        """Test creating CycleDetectedError with cycle path.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        node1 = uuid4()
        node2 = uuid4()
        node3 = uuid4()

        error = CycleDetectedError(cycle_path=[node1, node2, node3])

        assert "Cycle detected" in str(error)
        assert error.error_code == "CYCLE_DETECTED"
        assert len(error.cycle_path) == 3
        assert error.details["cycle_path"] == [str(node1), str(node2), str(node3)]


class TestInvalidNodeReferenceError:
    """Tests for InvalidNodeReferenceError.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
    """

    def test_invalid_node_reference_error_creation(self) -> None:
        """Test creating InvalidNodeReferenceError with missing node IDs.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        from uuid import uuid4

        node1 = uuid4()
        node2 = uuid4()

        error = InvalidNodeReferenceError(node_ids=[node1, node2])

        assert "Invalid node references" in str(error)
        assert error.error_code == "NODE_NOT_FOUND"
        assert len(error.missing_nodes) == 2
        assert error.details["missing_nodes"] == [str(node1), str(node2)]


class TestGraphTooLargeError:
    """Tests for GraphTooLargeError.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
    """

    def test_graph_too_large_error_creation(self) -> None:
        """Test creating GraphTooLargeError with current and limit.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        error = GraphTooLargeError(current=1500, limit=1000, metric="nodes")

        assert "Graph too large" in str(error)
        assert "1500 nodes (limit: 1000)" in str(error)
        assert error.error_code == "GRAPH_TOO_LARGE"
        assert error.current == 1500
        assert error.limit == 1000
        assert error.metric == "nodes"
        assert error.details == {"current": 1500, "limit": 1000, "metric": "nodes"}

    def test_graph_too_large_error_default_metric(self) -> None:
        """Test creating GraphTooLargeError with default metric.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        error = GraphTooLargeError(current=500, limit=300)

        assert error.metric == "nodes"


class TestValidationTimeoutError:
    """Tests for ValidationTimeoutError.

    TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
    """

    def test_validation_timeout_error_creation(self) -> None:
        """Test creating ValidationTimeoutError with timeout duration.

        TAG: [SPEC-010] [DAG] [EXCEPTIONS] [TEST]
        """
        error = ValidationTimeoutError(timeout_seconds=30.5)

        assert "Validation timeout after 30.5s" in str(error)
        assert error.error_code == "VALIDATION_TIMEOUT"
        assert error.timeout_seconds == 30.5
        assert error.details == {"timeout_seconds": 30.5}
