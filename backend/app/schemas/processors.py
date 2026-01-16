"""Processor Schemas.

TAG: [SPEC-012] [PROCESSOR] [SCHEMAS]

Processor input/output schemas will be fully implemented in TASK-006.
"""

from pydantic import BaseModel, Field


class ToolProcessorInput(BaseModel):
    """Input schema for tool processors.

    TAG: [SPEC-012] [SCHEMA] [TOOL]
    """
    tool_id: str
    parameters: dict = Field(default_factory=dict)


class ToolProcessorOutput(BaseModel):
    """Output schema for tool processors.

    TAG: [SPEC-012] [SCHEMA] [TOOL]
    """
    result: dict


class AgentProcessorInput(BaseModel):
    """Input schema for agent processors.

    TAG: [SPEC-012] [SCHEMA] [AGENT]
    """
    agent_id: str
    prompt_variables: dict = Field(default_factory=dict)


class AgentProcessorOutput(BaseModel):
    """Output schema for agent processors.

    TAG: [SPEC-012] [SCHEMA] [AGENT]
    """
    response: str


class ConditionProcessorInput(BaseModel):
    """Input schema for condition processors.

    TAG: [SPEC-012] [SCHEMA] [CONDITION]
    """
    conditions: list[dict]
    evaluation_context: dict = Field(default_factory=dict)


class ConditionProcessorOutput(BaseModel):
    """Output schema for condition processors.

    TAG: [SPEC-012] [SCHEMA] [CONDITION]
    """
    selected_branch: str


class AdapterProcessorInput(BaseModel):
    """Input schema for adapter processors.

    TAG: [SPEC-012] [SCHEMA] [ADAPTER]
    """
    transformation_type: str
    source_data: dict


class AdapterProcessorOutput(BaseModel):
    """Output schema for adapter processors.

    TAG: [SPEC-012] [SCHEMA] [ADAPTER]
    """
    transformed_data: dict


class TriggerProcessorInput(BaseModel):
    """Input schema for trigger processors.

    TAG: [SPEC-012] [SCHEMA] [TRIGGER]
    """
    trigger_type: str


class TriggerProcessorOutput(BaseModel):
    """Output schema for trigger processors.

    TAG: [SPEC-012] [SCHEMA] [TRIGGER]
    """
    initialized: bool = True


class AggregatorProcessorInput(BaseModel):
    """Input schema for aggregator processors.

    TAG: [SPEC-012] [SCHEMA] [AGGREGATOR]
    """
    strategy: str
    input_sources: dict


class AggregatorProcessorOutput(BaseModel):
    """Output schema for aggregator processors.

    TAG: [SPEC-012] [SCHEMA] [AGGREGATOR]
    """
    aggregated_result: dict
