"""Base executor interface and factory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.enums import ToolType


class ToolExecutionResult:
    """Result of tool execution."""

    def __init__(
        self,
        success: bool,
        output: dict[str, Any] | None = None,
        error: str | None = None,
        execution_time_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize execution result."""
        self.success = success
        self.output = output or {}
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class ToolExecutor(ABC):
    """Abstract base class for tool executors."""

    @abstractmethod
    async def execute(
        self,
        config: dict[str, Any],
        input_data: dict[str, Any],
        auth_config: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        """Execute the tool with given input."""
        ...

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate tool configuration."""
        ...


class ToolExecutorFactory:
    """Factory for creating type-specific tool executors."""

    _executors: dict[str, type[ToolExecutor]] = {}

    @classmethod
    def register(cls, tool_type: str, executor_class: type[ToolExecutor]) -> None:
        """Register an executor for a tool type."""
        if tool_type in cls._executors:
            raise ValueError(f"Executor for {tool_type} already registered")

        cls._executors[tool_type] = executor_class

    @classmethod
    def create(cls, tool_type: ToolType | str) -> ToolExecutor:
        """Create an executor instance for the given tool type."""
        type_str = tool_type.value if isinstance(tool_type, ToolType) else tool_type

        if type_str not in cls._executors:
            raise ValueError(
                f"Unsupported tool type: {type_str}. "
                f"Supported types: {list(cls._executors.keys())}"
            )

        executor_class = cls._executors[type_str]
        return executor_class()

    @classmethod
    def supported_types(cls) -> list[str]:
        """Get list of supported tool types."""
        return list(cls._executors.keys())


__all__ = [
    "ToolExecutionResult",
    "ToolExecutor",
    "ToolExecutorFactory",
]
