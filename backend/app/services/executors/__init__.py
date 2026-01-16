"""Tool execution engine with pluggable executors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.executors.base import ToolExecutor, ToolExecutorFactory
from app.services.executors.http_executor import HttpToolExecutor

if TYPE_CHECKING:
    from app.models.tool import Tool

# Register executors
ToolExecutorFactory.register("http", HttpToolExecutor)

__all__ = [
    "ToolExecutor",
    "ToolExecutorFactory",
]
