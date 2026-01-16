"""Tests for processor error classes.

TAG: [SPEC-012] [PROCESSOR] [TEST] [ERRORS]
REQ: REQ-012-006, REQ-012-007 - Error Context and Propagation
"""

import pytest
from datetime import datetime, UTC


class TestProcessorErrorHierarchy:
    """Test that all error classes inherit properly."""

    def test_processor_error_base_class(self):
        """Test ProcessorError base exception."""
        from app.services.workflow.processors.errors import ProcessorError

        error = ProcessorError("Base error")
        assert isinstance(error, Exception)
        assert str(error) == "Base error"

    def test_processor_validation_error_inheritance(self):
        """Test ProcessorValidationError inherits from ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorValidationError,
        )

        error = ProcessorValidationError(
            processor="TestProcessor",
            errors=[{"field": "test", "message": "Invalid value"}],
        )

        assert isinstance(error, ProcessorError)
        assert error.processor == "TestProcessor"
        assert len(error.errors) == 1
        assert "TestProcessor" in str(error)

    def test_processor_execution_error_inheritance(self):
        """Test ProcessorExecutionError inherits from ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorExecutionError,
        )

        error = ProcessorExecutionError(
            processor="AgentProcessor",
            node_id="node-123",
            message="LLM timeout",
            retry_count=3,
        )

        assert isinstance(error, ProcessorError)
        assert error.processor == "AgentProcessor"
        assert error.node_id == "node-123"
        assert error.retry_count == 3
        assert "AgentProcessor" in str(error)
        assert "node-123" in str(error)
        assert "retries: 3" in str(error)

    def test_processor_timeout_error_inheritance(self):
        """Test ProcessorTimeoutError inherits from ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorTimeoutError,
        )

        error = ProcessorTimeoutError(
            processor="ToolProcessor",
            node_id="node-456",
            timeout_seconds=30,
        )

        assert isinstance(error, ProcessorError)
        assert error.processor == "ToolProcessor"
        assert error.node_id == "node-456"
        assert error.timeout_seconds == 30
        assert "ToolProcessor" in str(error)
        assert "30s" in str(error)

    def test_processor_configuration_error_inheritance(self):
        """Test ProcessorConfigurationError inherits from ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorConfigurationError,
        )

        error = ProcessorConfigurationError(
            processor="ConditionProcessor",
            message="Invalid condition expression",
        )

        assert isinstance(error, ProcessorError)
        assert error.processor == "ConditionProcessor"
        # Note: error.message contains the full formatted message
        assert "Invalid condition expression" in error.message
        assert "ConditionProcessor" in str(error)

    def test_processor_not_found_error_inheritance(self):
        """Test ProcessorNotFoundError inherits from ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorNotFoundError,
        )

        error = ProcessorNotFoundError("Unknown processor type: 'magic'")

        assert isinstance(error, ProcessorError)
        assert "Unknown processor type" in str(error)


class TestProcessorErrorStringRepresentations:
    """Test error message formatting."""

    def test_validation_error_message_format(self):
        """Test validation error message includes processor and errors."""
        from app.services.workflow.processors.errors import ProcessorValidationError

        error = ProcessorValidationError(
            processor="ToolProcessor",
            errors=[
                {"field": "tool_id", "message": "Required field"},
                {"field": "parameters", "message": "Invalid type"},
            ],
        )

        error_str = str(error)
        assert "ToolProcessor" in error_str
        assert "Required field" in error_str or "errors" in error_str

    def test_execution_error_message_format(self):
        """Test execution error message includes all context."""
        from app.services.workflow.processors.errors import ProcessorExecutionError

        error = ProcessorExecutionError(
            processor="AgentProcessor",
            node_id="node-789",
            message="API rate limit exceeded",
            retry_count=2,
        )

        error_str = str(error)
        assert "AgentProcessor" in error_str
        assert "node-789" in error_str
        assert "retries: 2" in error_str
        assert "API rate limit exceeded" in error_str

    def test_timeout_error_message_format(self):
        """Test timeout error message includes timeout value."""
        from app.services.workflow.processors.errors import ProcessorTimeoutError

        error = ProcessorTimeoutError(
            processor="ToolProcessor",
            node_id="node-999",
            timeout_seconds=60,
        )

        error_str = str(error)
        assert "ToolProcessor" in error_str
        assert "node-999" in error_str
        assert "60s" in error_str

    def test_configuration_error_message_format(self):
        """Test configuration error message format."""
        from app.services.workflow.processors.errors import ProcessorConfigurationError

        error = ProcessorConfigurationError(
            processor="AdapterProcessor",
            message="Missing transformation config",
        )

        error_str = str(error)
        assert "AdapterProcessor" in error_str
        assert "Missing transformation config" in error_str


class TestProcessorErrorRaising:
    """Test errors can be raised and caught properly."""

    def test_raise_validation_error(self):
        """Test ProcessorValidationError can be raised."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorValidationError,
        )

        with pytest.raises(ProcessorValidationError) as exc_info:
            raise ProcessorValidationError(
                processor="TestProcessor",
                errors=[{"field": "test"}],
            )

        assert isinstance(exc_info.value, ProcessorError)
        assert exc_info.value.processor == "TestProcessor"

    def test_raise_execution_error(self):
        """Test ProcessorExecutionError can be raised."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorExecutionError,
        )

        with pytest.raises(ProcessorExecutionError) as exc_info:
            raise ProcessorExecutionError(
                processor="TestProcessor",
                node_id="test-node",
                message="Execution failed",
            )

        assert isinstance(exc_info.value, ProcessorError)
        assert exc_info.value.node_id == "test-node"

    def test_catch_base_processor_error(self):
        """Test all processor errors can be caught as ProcessorError."""
        from app.services.workflow.processors.errors import (
            ProcessorError,
            ProcessorValidationError,
            ProcessorExecutionError,
            ProcessorTimeoutError,
        )

        errors_to_test = [
            ProcessorValidationError(processor="Test", errors=[]),
            ProcessorExecutionError(
                processor="Test", node_id="node", message="fail"
            ),
            ProcessorTimeoutError(
                processor="Test", node_id="node", timeout_seconds=30
            ),
        ]

        for error in errors_to_test:
            try:
                raise error
            except ProcessorError:
                pass  # Expected
            except Exception as e:
                pytest.fail(f"Should have been caught as ProcessorError: {type(e)}")


class TestProcessorErrorChaining:
    """Test error chaining for debugging."""

    def test_execution_error_with_cause(self):
        """Test ProcessorExecutionError can wrap other exceptions."""
        from app.services.workflow.processors.errors import ProcessorExecutionError

        original_error = ValueError("Original error message")

        try:
            raise ProcessorExecutionError(
                processor="TestProcessor",
                node_id="test-node",
                message="Wrapped error",
            ) from original_error
        except ProcessorExecutionError as e:
            assert e.__cause__ is original_error
            assert str(e.__cause__) == "Original error message"

    def test_error_context_preservation(self):
        """Test error context is preserved when re-raising."""
        from app.services.workflow.processors.errors import ProcessorExecutionError

        try:
            try:
                raise ValueError("Deep error")
            except ValueError as ve:
                raise ProcessorExecutionError(
                    processor="TestProcessor",
                    node_id="node-1",
                    message="Higher level error",
                ) from ve
        except ProcessorExecutionError as final_error:
            assert final_error.__cause__ is not None
            assert isinstance(final_error.__cause__, ValueError)
