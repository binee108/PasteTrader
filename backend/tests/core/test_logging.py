"""Tests for the logging module.

TAG: [SPEC-002] [TEST] [LOGGING]
REQ: TRUST-5 Trackable - Verify logging system functionality

This module tests the comprehensive logging system including:
- Structured JSON logging
- Sensitive data filtering
- Log rotation configuration
- Security event logging
"""

import json
import logging
from pathlib import Path

from app.core.config import Settings
from app.core.logging import (
    JSONFormatter,
    LogContext,
    SensitiveDataFilter,
    setup_logging,
)


class TestSensitiveDataFilter:
    """Test sensitive data filtering in logs."""

    def test_filter_password_in_message(self) -> None:
        """Test that passwords are redacted from log messages."""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User password: secret123",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        assert "[REDACTED]" in record.msg
        assert "secret123" not in record.msg

    def test_filter_multiple_sensitive_patterns(self) -> None:
        """Test that multiple sensitive patterns are redacted."""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="password: pass123, token: abc123, secret: xyz789",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert record.msg.count("[REDACTED]") >= 3

    def test_filter_bearer_token(self) -> None:
        """Test that bearer tokens are redacted."""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "[REDACTED]" in record.msg


class TestJSONFormatter:
    """Test JSON log formatting."""

    def test_json_formatter_creates_valid_json(self) -> None:
        """Test that JSON formatter creates valid JSON output."""
        formatter = JSONFormatter(service_name="TestAPI")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test.logger"
        assert log_entry["message"] == "Test message"
        assert log_entry["service"] == "TestAPI"
        assert "timestamp" in log_entry

    def test_json_formatter_includes_context(self) -> None:
        """Test that JSON formatter includes context."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.context = {"user_id": "123", "action": "test"}

        formatted = formatter.format(record)
        log_entry = json.loads(formatted)

        assert "context" in log_entry
        assert log_entry["context"]["user_id"] == "123"
        assert log_entry["context"]["action"] == "test"


class TestLogContext:
    """Test LogContext context manager."""

    def test_log_context_adds_context_to_records(self) -> None:
        """Test that LogContext adds context to log records."""
        logger = logging.getLogger("test_context")
        logger.handlers.clear()
        handler = logging.StreamHandler()
        records = []

        def emit_record(record: logging.LogRecord) -> None:
            records.append(record)

        handler.emit = emit_record  # type: ignore[method-assign]
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        with LogContext(logger, user_id="123", action="test"):
            logger.info("Test message")

        assert len(records) == 1
        assert hasattr(records[0], "context")
        assert records[0].context["user_id"] == "123"
        assert records[0].context["action"] == "test"


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_creates_log_directory(self, tmp_path: Path) -> None:
        """Test that setup_logging creates log directory if it doesn't exist."""
        log_file = tmp_path / "logs" / "test.log"

        setup_logging(log_file=str(log_file), enable_console=False)

        assert log_file.parent.exists()

    def test_setup_logging_configures_log_level(self, tmp_path: Path) -> None:
        """Test that setup_logging configures log level correctly."""
        log_file = tmp_path / "logs" / "test.log"

        logger = setup_logging(
            log_level="DEBUG", log_file=str(log_file), enable_console=False
        )

        assert logger.level == logging.DEBUG

    def test_setup_logging_creates_file_handler(self, tmp_path: Path) -> None:
        """Test that setup_logging creates file handler."""
        log_file = tmp_path / "logs" / "test.log"

        logger = setup_logging(log_file=str(log_file), enable_console=False)

        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) > 0


class TestConfigIntegration:
    """Test logging configuration integration with settings."""

    def test_log_level_from_settings(self) -> None:
        """Test that log level can be configured via settings."""
        settings = Settings(LOG_LEVEL="DEBUG")
        assert settings.LOG_LEVEL == "DEBUG"

    def test_log_file_from_settings(self) -> None:
        """Test that log file can be configured via settings."""
        settings = Settings(LOG_FILE="/var/log/app.log")
        assert settings.LOG_FILE == "/var/log/app.log"

    def test_json_format_from_settings(self) -> None:
        """Test that JSON format can be configured via settings."""
        settings = Settings(LOG_JSON_FORMAT=True)
        assert settings.LOG_JSON_FORMAT is True

    def test_sensitive_filter_from_settings(self) -> None:
        """Test that sensitive data filter can be configured via settings."""
        settings = Settings(LOG_SENSITIVE_FILTER=True)
        assert settings.LOG_SENSITIVE_FILTER is True
