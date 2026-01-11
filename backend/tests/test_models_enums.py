"""Tests for domain enum definitions.

TAG: [SPEC-001] [DATABASE] [ENUMS]
REQ: REQ-004 - Domain Enum Definitions
AC: AC-007 - Enum Definitions
"""

import pytest


class TestNodeType:
    """Test NodeType enum values and behavior."""

    def test_nodetype_has_trigger_value(self) -> None:
        """NodeType should have 'trigger' value."""
        from app.models.enums import NodeType

        assert NodeType.TRIGGER == "trigger"
        assert NodeType.TRIGGER.value == "trigger"

    def test_nodetype_has_tool_value(self) -> None:
        """NodeType should have 'tool' value."""
        from app.models.enums import NodeType

        assert NodeType.TOOL == "tool"
        assert NodeType.TOOL.value == "tool"

    def test_nodetype_has_agent_value(self) -> None:
        """NodeType should have 'agent' value."""
        from app.models.enums import NodeType

        assert NodeType.AGENT == "agent"
        assert NodeType.AGENT.value == "agent"

    def test_nodetype_has_condition_value(self) -> None:
        """NodeType should have 'condition' value."""
        from app.models.enums import NodeType

        assert NodeType.CONDITION == "condition"
        assert NodeType.CONDITION.value == "condition"

    def test_nodetype_has_adapter_value(self) -> None:
        """NodeType should have 'adapter' value."""
        from app.models.enums import NodeType

        assert NodeType.ADAPTER == "adapter"
        assert NodeType.ADAPTER.value == "adapter"

    def test_nodetype_has_parallel_value(self) -> None:
        """NodeType should have 'parallel' value."""
        from app.models.enums import NodeType

        assert NodeType.PARALLEL == "parallel"
        assert NodeType.PARALLEL.value == "parallel"

    def test_nodetype_has_aggregator_value(self) -> None:
        """NodeType should have 'aggregator' value."""
        from app.models.enums import NodeType

        assert NodeType.AGGREGATOR == "aggregator"
        assert NodeType.AGGREGATOR.value == "aggregator"

    def test_nodetype_is_string_compatible(self) -> None:
        """NodeType should serialize to string value."""
        from app.models.enums import NodeType

        assert str(NodeType.TRIGGER) == "trigger"
        assert f"{NodeType.TOOL}" == "tool"


class TestToolType:
    """Test ToolType enum values and behavior."""

    def test_tooltype_has_data_fetcher_value(self) -> None:
        """ToolType should have 'data_fetcher' value."""
        from app.models.enums import ToolType

        assert ToolType.DATA_FETCHER == "data_fetcher"
        assert ToolType.DATA_FETCHER.value == "data_fetcher"

    def test_tooltype_has_technical_indicator_value(self) -> None:
        """ToolType should have 'technical_indicator' value."""
        from app.models.enums import ToolType

        assert ToolType.TECHNICAL_INDICATOR == "technical_indicator"
        assert ToolType.TECHNICAL_INDICATOR.value == "technical_indicator"

    def test_tooltype_has_market_screener_value(self) -> None:
        """ToolType should have 'market_screener' value."""
        from app.models.enums import ToolType

        assert ToolType.MARKET_SCREENER == "market_screener"
        assert ToolType.MARKET_SCREENER.value == "market_screener"

    def test_tooltype_has_code_analyzer_value(self) -> None:
        """ToolType should have 'code_analyzer' value."""
        from app.models.enums import ToolType

        assert ToolType.CODE_ANALYZER == "code_analyzer"
        assert ToolType.CODE_ANALYZER.value == "code_analyzer"

    def test_tooltype_has_notification_value(self) -> None:
        """ToolType should have 'notification' value."""
        from app.models.enums import ToolType

        assert ToolType.NOTIFICATION == "notification"
        assert ToolType.NOTIFICATION.value == "notification"

    def test_tooltype_is_string_compatible(self) -> None:
        """ToolType should serialize to string value."""
        from app.models.enums import ToolType

        assert str(ToolType.DATA_FETCHER) == "data_fetcher"


class TestModelProvider:
    """Test ModelProvider enum values and behavior."""

    def test_modelprovider_has_anthropic_value(self) -> None:
        """ModelProvider should have 'anthropic' value."""
        from app.models.enums import ModelProvider

        assert ModelProvider.ANTHROPIC == "anthropic"
        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_modelprovider_has_openai_value(self) -> None:
        """ModelProvider should have 'openai' value."""
        from app.models.enums import ModelProvider

        assert ModelProvider.OPENAI == "openai"
        assert ModelProvider.OPENAI.value == "openai"

    def test_modelprovider_has_glm_value(self) -> None:
        """ModelProvider should have 'glm' value."""
        from app.models.enums import ModelProvider

        assert ModelProvider.GLM == "glm"
        assert ModelProvider.GLM.value == "glm"

    def test_modelprovider_is_string_compatible(self) -> None:
        """ModelProvider should serialize to string value."""
        from app.models.enums import ModelProvider

        assert str(ModelProvider.ANTHROPIC) == "anthropic"


class TestExecutionStatus:
    """Test ExecutionStatus enum values and behavior."""

    def test_executionstatus_has_pending_value(self) -> None:
        """ExecutionStatus should have 'pending' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.PENDING == "pending"
        assert ExecutionStatus.PENDING.value == "pending"

    def test_executionstatus_has_running_value(self) -> None:
        """ExecutionStatus should have 'running' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.RUNNING.value == "running"

    def test_executionstatus_has_completed_value(self) -> None:
        """ExecutionStatus should have 'completed' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.COMPLETED.value == "completed"

    def test_executionstatus_has_failed_value(self) -> None:
        """ExecutionStatus should have 'failed' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.FAILED == "failed"
        assert ExecutionStatus.FAILED.value == "failed"

    def test_executionstatus_has_skipped_value(self) -> None:
        """ExecutionStatus should have 'skipped' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.SKIPPED == "skipped"
        assert ExecutionStatus.SKIPPED.value == "skipped"

    def test_executionstatus_has_cancelled_value(self) -> None:
        """ExecutionStatus should have 'cancelled' value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus.CANCELLED == "cancelled"
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_executionstatus_is_string_compatible(self) -> None:
        """ExecutionStatus should serialize to string value."""
        from app.models.enums import ExecutionStatus

        assert str(ExecutionStatus.PENDING) == "pending"


class TestAuthMode:
    """Test AuthMode enum values and behavior."""

    def test_authmode_has_oauth_value(self) -> None:
        """AuthMode should have 'oauth' value."""
        from app.models.enums import AuthMode

        assert AuthMode.OAUTH == "oauth"
        assert AuthMode.OAUTH.value == "oauth"

    def test_authmode_has_standalone_value(self) -> None:
        """AuthMode should have 'standalone' value."""
        from app.models.enums import AuthMode

        assert AuthMode.STANDALONE == "standalone"
        assert AuthMode.STANDALONE.value == "standalone"

    def test_authmode_has_sdk_value(self) -> None:
        """AuthMode should have 'sdk' value."""
        from app.models.enums import AuthMode

        assert AuthMode.SDK == "sdk"
        assert AuthMode.SDK.value == "sdk"

    def test_authmode_has_glm_value(self) -> None:
        """AuthMode should have 'glm' value."""
        from app.models.enums import AuthMode

        assert AuthMode.GLM == "glm"
        assert AuthMode.GLM.value == "glm"

    def test_authmode_is_string_compatible(self) -> None:
        """AuthMode should serialize to string value."""
        from app.models.enums import AuthMode

        assert str(AuthMode.OAUTH) == "oauth"


class TestTriggerType:
    """Test TriggerType enum values and behavior."""

    def test_triggertype_has_schedule_value(self) -> None:
        """TriggerType should have 'schedule' value."""
        from app.models.enums import TriggerType

        assert TriggerType.SCHEDULE == "schedule"
        assert TriggerType.SCHEDULE.value == "schedule"

    def test_triggertype_has_event_value(self) -> None:
        """TriggerType should have 'event' value."""
        from app.models.enums import TriggerType

        assert TriggerType.EVENT == "event"
        assert TriggerType.EVENT.value == "event"

    def test_triggertype_has_manual_value(self) -> None:
        """TriggerType should have 'manual' value."""
        from app.models.enums import TriggerType

        assert TriggerType.MANUAL == "manual"
        assert TriggerType.MANUAL.value == "manual"

    def test_triggertype_is_string_compatible(self) -> None:
        """TriggerType should serialize to string value."""
        from app.models.enums import TriggerType

        assert str(TriggerType.SCHEDULE) == "schedule"


class TestEnumFromString:
    """Test enum deserialization from string values."""

    def test_nodetype_from_string(self) -> None:
        """NodeType should deserialize from string value."""
        from app.models.enums import NodeType

        assert NodeType("trigger") == NodeType.TRIGGER
        assert NodeType("tool") == NodeType.TOOL

    def test_tooltype_from_string(self) -> None:
        """ToolType should deserialize from string value."""
        from app.models.enums import ToolType

        assert ToolType("data_fetcher") == ToolType.DATA_FETCHER

    def test_modelprovider_from_string(self) -> None:
        """ModelProvider should deserialize from string value."""
        from app.models.enums import ModelProvider

        assert ModelProvider("anthropic") == ModelProvider.ANTHROPIC

    def test_executionstatus_from_string(self) -> None:
        """ExecutionStatus should deserialize from string value."""
        from app.models.enums import ExecutionStatus

        assert ExecutionStatus("pending") == ExecutionStatus.PENDING

    def test_authmode_from_string(self) -> None:
        """AuthMode should deserialize from string value."""
        from app.models.enums import AuthMode

        assert AuthMode("oauth") == AuthMode.OAUTH

    def test_triggertype_from_string(self) -> None:
        """TriggerType should deserialize from string value."""
        from app.models.enums import TriggerType

        assert TriggerType("schedule") == TriggerType.SCHEDULE


class TestEnumValueError:
    """Test that invalid enum values raise ValueError."""

    def test_invalid_nodetype_raises_valueerror(self) -> None:
        """Invalid NodeType value should raise ValueError."""
        from app.models.enums import NodeType

        with pytest.raises(ValueError):
            NodeType("invalid_value")

    def test_invalid_tooltype_raises_valueerror(self) -> None:
        """Invalid ToolType value should raise ValueError."""
        from app.models.enums import ToolType

        with pytest.raises(ValueError):
            ToolType("invalid_value")
