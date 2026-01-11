"""Domain enum definitions for PasteTrader.

TAG: [SPEC-001] [DATABASE] [ENUMS]
REQ: REQ-004 - Domain Enum Definitions

This module defines all enum types used across the application for
type-safe representation of domain-specific values.
"""

from enum import Enum


class NodeType(str, Enum):
    """Workflow node classification types.

    Defines the types of nodes that can exist in a workflow graph.
    Each node type has specific behavior and configuration options.
    """

    TRIGGER = "trigger"
    TOOL = "tool"
    AGENT = "agent"
    CONDITION = "condition"
    ADAPTER = "adapter"
    PARALLEL = "parallel"
    AGGREGATOR = "aggregator"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


class ToolType(str, Enum):
    """Tool classification types.

    Defines the categories of tools available in the system.
    Each tool type represents a specific functionality domain.
    """

    DATA_FETCHER = "data_fetcher"
    TECHNICAL_INDICATOR = "technical_indicator"
    MARKET_SCREENER = "market_screener"
    CODE_ANALYZER = "code_analyzer"
    NOTIFICATION = "notification"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


class ModelProvider(str, Enum):
    """LLM provider identification.

    Defines the supported LLM providers for agent execution.
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GLM = "glm"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


class ExecutionStatus(str, Enum):
    """Workflow execution state.

    Defines the possible states of a workflow or node execution.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


class AuthMode(str, Enum):
    """API authentication modes.

    Defines the authentication methods supported for external API access.
    """

    OAUTH = "oauth"
    STANDALONE = "standalone"
    SDK = "sdk"
    GLM = "glm"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


class TriggerType(str, Enum):
    """Workflow trigger types.

    Defines how a workflow can be initiated.
    """

    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


__all__ = [
    "NodeType",
    "ToolType",
    "ModelProvider",
    "ExecutionStatus",
    "AuthMode",
    "TriggerType",
]
