"""Tests for workflow execution exceptions.

TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS] [TEST]
REQ: REQ-011-001 - Exception handling
"""

import pytest

from app.services.workflow.exceptions import (
    ConditionEvaluationError,
    ExecutionCancelledError,
    ExecutionError,
    NodeExecutionError,
    NodeTimeoutError,
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
