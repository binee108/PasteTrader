"""Processor Schemas.

TAG: [SPEC-012] [PROCESSOR] [SCHEMAS]
REQ: REQ-012-003, REQ-012-004 - Input/Output Validation with Pydantic

Complete input/output schemas for all processor types.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Tool Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [TOOL]
# REQ: REQ-012-010
# ============================================================================

class ToolProcessorInput(BaseModel):
    """Input schema for tool processors.

    TAG: [SPEC-012] [SCHEMA] [TOOL] [INPUT]

    Attributes:
        tool_id: Unique identifier for the tool to execute
        parameters: Tool-specific parameters for execution
        timeout_seconds: Maximum execution time in seconds (1-300)
    """
    model_config = ConfigDict(strict=True)

    tool_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class ToolProcessorOutput(BaseModel):
    """Output schema for tool processors.

    TAG: [SPEC-012] [SCHEMA] [TOOL] [OUTPUT]

    Attributes:
        result: Result data from tool execution
        execution_duration_ms: Tool execution time in milliseconds
        tool_metadata: Additional metadata from the tool
    """
    result: Any
    execution_duration_ms: float
    tool_metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Agent Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [AGENT]
# REQ: REQ-012-011
# ============================================================================

class AgentProcessorInput(BaseModel):
    """Input schema for agent processors.

    TAG: [SPEC-012] [SCHEMA] [AGENT] [INPUT]

    Attributes:
        agent_id: Unique identifier for the AI agent
        prompt_variables: Variables for prompt template substitution
        max_tokens: Maximum tokens in LLM response (1-128000)
        temperature: LLM temperature parameter (0.0-2.0)
    """
    model_config = ConfigDict(strict=True)

    agent_id: str
    prompt_variables: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AgentProcessorOutput(BaseModel):
    """Output schema for agent processors.

    TAG: [SPEC-012] [SCHEMA] [AGENT] [OUTPUT]

    Attributes:
        response: Text response from the AI agent
        structured_output: Parsed structured output (if applicable)
        token_usage: Token usage statistics from LLM provider
        model_used: Name/ID of the LLM model used
    """
    response: str
    structured_output: dict[str, Any] | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    model_used: str


# ============================================================================
# Condition Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [CONDITION]
# REQ: REQ-012-012
# ============================================================================

class ConditionExpression(BaseModel):
    """Single condition expression for evaluation.

    TAG: [SPEC-012] [SCHEMA] [CONDITION] [EXPRESSION]

    Attributes:
        name: Unique name for this condition
        expression: Boolean expression to evaluate
        target_node: Node ID to route to if condition is true
    """
    name: str
    expression: str
    target_node: str


class ConditionProcessorInput(BaseModel):
    """Input schema for condition processors.

    TAG: [SPEC-012] [SCHEMA] [CONDITION] [INPUT]

    Attributes:
        conditions: List of conditions to evaluate in order
        evaluation_context: Context data for expression evaluation
    """
    model_config = ConfigDict(strict=True)

    conditions: list[ConditionExpression]
    evaluation_context: dict[str, Any] = Field(default_factory=dict)


class ConditionProcessorOutput(BaseModel):
    """Output schema for condition processors.

    TAG: [SPEC-012] [SCHEMA] [CONDITION] [OUTPUT]

    Attributes:
        selected_branch: Name of the condition that matched
        target_node: Node ID to route to next
        evaluated_conditions: Results of all condition evaluations
    """
    selected_branch: str
    target_node: str
    evaluated_conditions: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# Adapter Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [ADAPTER]
# REQ: REQ-012-013
# ============================================================================

class AdapterProcessorInput(BaseModel):
    """Input schema for adapter processors.

    TAG: [SPEC-012] [SCHEMA] [ADAPTER] [INPUT]

    Attributes:
        transformation_type: Type of transformation to apply
        source_data: Input data to transform
        transformation_config: Configuration for the transformation
    """
    model_config = ConfigDict(strict=True)

    transformation_type: str
    source_data: Any
    transformation_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("transformation_type")
    @classmethod
    def validate_transformation_type(cls, v: str) -> str:
        """Validate transformation type is supported."""
        valid_types = {
            "field_mapping",
            "type_conversion",
            "aggregation",
            "filtering",
            "custom",
        }
        if v not in valid_types:
            raise ValueError(
                f"Invalid transformation_type: {v}. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
        return v


class AdapterProcessorOutput(BaseModel):
    """Output schema for adapter processors.

    TAG: [SPEC-012] [SCHEMA] [ADAPTER] [OUTPUT]

    Attributes:
        transformed_data: Result of the transformation
        transformation_applied: Type of transformation that was applied
        records_processed: Number of records processed (for collections)
    """
    transformed_data: Any
    transformation_applied: str
    records_processed: int = 0


# ============================================================================
# Trigger Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [TRIGGER]
# REQ: REQ-012-014
# ============================================================================

class TriggerProcessorInput(BaseModel):
    """Input schema for trigger processors.

    TAG: [SPEC-012] [SCHEMA] [TRIGGER] [INPUT]

    Attributes:
        trigger_type: Type of trigger (schedule, webhook, manual)
        trigger_payload: Data payload from the trigger source
        trigger_metadata: Additional metadata about the trigger
    """
    model_config = ConfigDict(strict=True)

    trigger_type: str
    trigger_payload: dict[str, Any] = Field(default_factory=dict)
    trigger_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger_type(cls, v: str) -> str:
        """Validate trigger type is supported."""
        valid_types = {"schedule", "webhook", "manual"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid trigger_type: {v}. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
        return v


class TriggerProcessorOutput(BaseModel):
    """Output schema for trigger processors.

    TAG: [SPEC-012] [SCHEMA] [TRIGGER] [OUTPUT]

    Attributes:
        initialized: Whether initialization was successful
        context_variables: Initial context variables set by trigger
        trigger_timestamp: When the trigger was activated
    """
    initialized: bool = True
    context_variables: dict[str, Any] = Field(default_factory=dict)
    trigger_timestamp: datetime


# ============================================================================
# Aggregator Processor Schemas
# TAG: [SPEC-012] [SCHEMA] [AGGREGATOR]
# REQ: REQ-012-015
# ============================================================================

class AggregatorProcessorInput(BaseModel):
    """Input schema for aggregator processors.

    TAG: [SPEC-012] [SCHEMA] [AGGREGATOR] [INPUT]

    Attributes:
        strategy: Aggregation strategy to use
        input_sources: Data from multiple input sources
        aggregation_config: Configuration for the aggregation
    """
    model_config = ConfigDict(strict=True)

    strategy: str
    input_sources: dict[str, Any]
    aggregation_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate aggregation strategy is supported."""
        valid_strategies = {"merge", "list", "reduce", "custom"}
        if v not in valid_strategies:
            raise ValueError(
                f"Invalid strategy: {v}. "
                f"Must be one of: {', '.join(sorted(valid_strategies))}"
            )
        return v


class AggregatorProcessorOutput(BaseModel):
    """Output schema for aggregator processors.

    TAG: [SPEC-012] [SCHEMA] [AGGREGATOR] [OUTPUT]

    Attributes:
        aggregated_result: Result of the aggregation
        source_count: Number of sources that were aggregated
        strategy_used: The strategy that was applied
    """
    aggregated_result: Any
    source_count: int
    strategy_used: str
