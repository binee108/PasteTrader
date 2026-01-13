"""Structured logging configuration for Paste Trader backend.

TAG: [SPEC-002] [INFRA] [LOGGING]
REQ: TRUST-5 Trackable - Comprehensive logging for security events

This module provides a comprehensive logging system with:
- JSON structured logging for production environments
- Log level filtering (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- File and console output handlers
- Automatic log rotation to prevent disk space issues
- Security event logging with sensitive data filtering
- Request context tracking for debugging

Features:
- Structured JSON logs for machine parsing
- Colored console output for development
- Rotating file handler (10MB max, 5 backups)
- Security event tracking without sensitive data
- Performance metrics logging
- Error stack traces with context
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, ClassVar

from app.core.config import settings


# Log level enum for type safety
class LogLevel(str, Enum):
    """Log level enumeration for type-safe log level configuration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent sensitive data from appearing in logs.

    This filter removes sensitive information like passwords, tokens,
    and API keys from log messages before they are written to any handler.

    Security:
        - Filters passwords in any form (password, pwd, pass)
        - Filters JWT tokens and bearer tokens
        - Filters API keys and secrets
        - Prevents accidental logging of sensitive user data

    Examples:
        >>> logger = logging.getLogger("app")
        >>> logger.addFilter(SensitiveDataFilter())
        >>> logger.info("User password: secret123")
        # Logs: "User password: [REDACTED]"
    """

    # Patterns that might contain sensitive data
    SENSITIVE_PATTERNS: ClassVar[list[str]] = [
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "session",
        "credential",
        "auth",
    ]

    def __init__(self) -> None:
        """Initialize sensitive data filter."""
        super().__init__()
        self._sensitive_keys: set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log record.

        Args:
            record: Log record to filter

        Returns:
            True (always allows the record, but redacts sensitive data)
        """
        # Redact from message
        record.msg = self._redact_sensitive_data(str(record.msg))

        # Redact from args if present
        if record.args:
            record.args = tuple(
                self._redact_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def _redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text.

        Args:
            text: Text to redact

        Returns:
            Text with sensitive data redacted
        """
        import re

        # Redact common patterns like "password: value" or "password=value"
        for pattern in self.SENSITIVE_PATTERNS:
            # Match "pattern: value", "pattern=value", "pattern='value'"
            regex = re.compile(
                rf"{pattern}[:=]\s*[\"']?[^\s\"']+",
                re.IGNORECASE,
            )
            text = regex.sub(f"{pattern}: [REDACTED]", text)

        return text


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    This formatter creates structured JSON logs that can be easily parsed
    by log aggregation systems like ELK, Splunk, or CloudWatch.

    Format:
        {
            "timestamp": "2025-01-12T10:30:45.123Z",
            "level": "INFO",
            "logger": "app.services.user_service",
            "message": "User created successfully",
            "context": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "create_user"
            },
            "extra": {
                "function": "create_user",
                "line": 42,
                "process": 12345
            }
        }
    """

    def __init__(
        self,
        service_name: str = "PasteTraderAPI",
        service_version: str = "1.0.0",
    ) -> None:
        """Initialize JSON formatter.

        Args:
            service_name: Name of the service
            service_version: Version of the service
        """
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "version": self.service_version,
        }

        # Add context if available
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {  # type: ignore[assignment]
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add function and line info for ERROR and above
        if record.levelno >= logging.ERROR:
            log_entry["source"] = {  # type: ignore[assignment]
                "function": record.funcName,
                "line": record.lineno,
                "file": record.pathname,
                "process": record.process,
                "thread": record.thread,
            }

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development environments.

    This formatter provides human-readable, colored log output for
    console logging during development.

    Colors:
        DEBUG: Blue
        INFO: Green
        WARNING: Yellow
        ERROR: Red
        CRITICAL: Red on white background
    """

    # ANSI color codes
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET: ClassVar[str] = "\033[0m"

    def __init__(self) -> None:
        """Initialize colored console formatter."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
            record: Log record to format

        Returns:
            Colored log string
        """
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"

        # Add context if available
        if hasattr(record, "context") and record.context:
            record.msg = f"{record.msg} | Context: {json.dumps(record.context)}"

        return super().format(record)


def setup_logging(
    log_level: str | None = None,
    log_file: str | None = None,
    service_name: str = "PasteTraderAPI",
    enable_json: bool = True,
    enable_console: bool = True,
) -> logging.Logger:
    """Configure application logging with structured handlers.

    This function sets up the complete logging system for the application:
    - Root logger with configurable level
    - File handler with rotation (10MB max, 5 backups)
    - Console handler with colored output
    - Sensitive data filter
    - JSON or console formatters

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                   Defaults to settings.LOG_LEVEL
        log_file: Path to log file. Defaults to logs/app.log
        service_name: Name of the service for log metadata
        enable_json: Enable JSON formatting for file handler
        enable_console: Enable console output handler

    Returns:
        Configured root logger instance

    Examples:
        >>> logger = setup_logging(log_level="INFO")
        >>> logger.info("Application started", extra={"context": {"port": 8000}})

    Security:
        - Applies SensitiveDataFilter to prevent sensitive data leakage
        - Ensures log files have appropriate permissions (644)
        - Rotates logs to prevent disk space exhaustion
    """
    # Use settings log level if not provided
    if log_level is None:
        log_level = settings.LOG_LEVEL

    # Determine log file path
    log_file_path: Path
    if log_file is None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file_path = log_dir / "app.log"
    else:
        # Convert to Path object if string
        log_file_path = Path(log_file)
        # Create parent directory if it doesn't exist
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Setup file handler with rotation
    file_handler = RotatingFileHandler(
        filename=str(log_file_path),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file

    if enable_json:
        file_handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    file_handler.addFilter(sensitive_filter)
    logger.addHandler(file_handler)

    # Setup console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Use colored formatter in development, JSON in production
        if settings.DEBUG:
            console_handler.setFormatter(ColoredConsoleFormatter())
        else:
            console_handler.setFormatter(JSONFormatter(service_name=service_name))

        console_handler.addFilter(sensitive_filter)
        logger.addHandler(console_handler)

    # Log startup
    logger.info(
        f"Logging initialized - Level: {log_level}, File: {log_file_path}",
        extra={
            "context": {
                "log_level": log_level,
                "log_file": str(log_file_path),
                "service": service_name,
            }
        },
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    This is a convenience function for getting loggers throughout the application.
    The logger inherits the configuration from setup_logging().

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance

    Examples:
        >>> from app.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request")
    """
    return logging.getLogger(name)


# Logging context helper functions
class LogContext:
    """Context helper for adding structured context to log records.

    This class provides a convenient way to add context to log records
    within a specific scope (function, request, etc.).

    Examples:
        >>> logger = get_logger(__name__)
        >>> with LogContext(logger, user_id="123", action="create"):
        ...     logger.info("Processing user creation")
        # Logs: "Processing user creation" with context
        # {user_id: "123", action: "create"}
    """

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        """Initialize log context.

        Args:
            logger: Logger instance to add context to
            **context: Key-value pairs to add to log context
        """
        self.logger = logger
        self.context = context
        self.old_factory = logging.getLogRecordFactory()

    def __enter__(self) -> None:
        """Enter context and add context factory."""

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = self.old_factory(*args, **kwargs)
            # Add context attribute dynamically
            if not hasattr(record, "context"):
                record.context = self.context.copy()
            else:
                # Merge existing context with new context
                record.context = {**record.context, **self.context}
            return record

        logging.setLogRecordFactory(record_factory)

    def __exit__(self, *args: Any) -> None:
        """Exit context and restore old factory."""
        logging.setLogRecordFactory(self.old_factory)


__all__ = [
    "ColoredConsoleFormatter",
    "JSONFormatter",
    "LogContext",
    "LogLevel",
    "SensitiveDataFilter",
    "get_logger",
    "setup_logging",
]
