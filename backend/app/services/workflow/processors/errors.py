"""Processor Error Classes.

TAG: [SPEC-012] [PROCESSOR] [ERRORS]
REQ: REQ-012-006, REQ-012-007 - Error Context Capture and Graceful Propagation
"""

from dataclasses import dataclass
from typing import Any


class ProcessorError(Exception):
    """Base exception for processor errors.

    TAG: [SPEC-012] [ERROR] [BASE]
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class ProcessorValidationError(ProcessorError):
    """Raised when input/output validation fails.

    TAG: [SPEC-012] [ERROR] [VALIDATION]

    Attributes:
        processor: Name of the processor class
        errors: List of validation error dictionaries
    """

    processor: str
    errors: list[dict[str, Any]]

    def __post_init__(self) -> None:
        # Initialize the base Exception with the error message
        super().__init__(f"Validation failed in {self.processor}: {self.errors}")

    def __str__(self) -> str:
        return f"Validation failed in {self.processor}: {self.errors}"


@dataclass
class ProcessorExecutionError(ProcessorError):
    """Raised when processing fails after retries.

    TAG: [SPEC-012] [ERROR] [EXECUTION]

    Attributes:
        processor: Name of the processor class
        node_id: ID of the node being processed
        message: Error message
        retry_count: Number of retry attempts made
    """

    processor: str
    node_id: str
    message: str
    retry_count: int = 0

    def __post_init__(self) -> None:
        # Initialize the base Exception with the error message
        super().__init__(
            f"Execution failed in {self.processor} "
            f"(node: {self.node_id}, retries: {self.retry_count}): {self.message}"
        )

    def __str__(self) -> str:
        return (
            f"Execution failed in {self.processor} "
            f"(node: {self.node_id}, retries: {self.retry_count}): {self.message}"
        )


@dataclass
class ProcessorTimeoutError(ProcessorError):
    """Raised when processing exceeds timeout.

    TAG: [SPEC-012] [ERROR] [TIMEOUT]

    Attributes:
        processor: Name of the processor class
        node_id: ID of the node that timed out
        timeout_seconds: Timeout limit in seconds
    """

    processor: str
    node_id: str
    timeout_seconds: int

    def __post_init__(self) -> None:
        # Initialize the base Exception with the error message
        super().__init__(
            f"Timeout in {self.processor} "
            f"(node: {self.node_id}) after {self.timeout_seconds}s"
        )

    def __str__(self) -> str:
        return (
            f"Timeout in {self.processor} "
            f"(node: {self.node_id}) after {self.timeout_seconds}s"
        )


@dataclass
class ProcessorConfigurationError(ProcessorError):
    """Raised when processor configuration is invalid.

    TAG: [SPEC-012] [ERROR] [CONFIG]

    Attributes:
        processor: Name of the processor class
        message: Configuration error description
    """

    processor: str
    message: str

    def __post_init__(self) -> None:
        # Initialize the base Exception with the error message
        super().__init__(f"Configuration error in {self.processor}: {self.message}")

    def __str__(self) -> str:
        return f"Configuration error in {self.processor}: {self.message}"


class ProcessorNotFoundError(ProcessorError):
    """Raised when requested processor type is not registered.

    TAG: [SPEC-012] [ERROR] [NOT_FOUND]
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message
