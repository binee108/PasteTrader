<<<<<<< HEAD
"""Agent schemas for API request/response validation.

TAG: [SPEC-009] [SCHEMAS] [AGENT]
REQ: REQ-001 - Agent CRUD Schemas
REQ: REQ-002 - Agent Tool Association Schemas

This module defines Pydantic schemas for Agent API validation.
=======
"""Pydantic schemas for Agent model.

TAG: [SPEC-009] [SCHEMAS] [AGENT]
REQ: REQ-001 - Agent Schema Definitions
REQ: REQ-002 - Model Configuration Schema
REQ: REQ-003 - Tool Management Schema
REQ: REQ-004 - Test Execution Schema

This module defines request/response schemas for Agent-related endpoints
including model configuration, tool management, and test execution.
>>>>>>> origin/main
"""

from __future__ import annotations

<<<<<<< HEAD
from typing import Any
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic v2

from pydantic import Field

from app.schemas.base import (
    BaseResponse,
    BaseSchema,
    ConfigField,
    DescriptionField,
    NameField,
    OptionalNameField,
)

# =============================================================================
# Base Schemas
# =============================================================================


class AgentBase(BaseSchema):
    """Base agent schema with common fields."""

    name: str = NameField
    description: str | None = DescriptionField
    model_provider: str = Field(
        ...,
        description="LLM provider (anthropic, openai, glm)",
        examples=["anthropic"],
    )
    model_name: str = Field(
        ...,
        description="Specific model identifier",
        examples=["claude-3-5-sonnet-20241022"],
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt for the agent",
        examples=["You are a helpful assistant."],
    )
    config: dict[str, Any] = ConfigField
    tools: list[str] = Field(
        default_factory=list,
        description="List of tool UUIDs the agent can use",
        examples=[["550e8400-e29b-41d4-a716-446655440000"]],
    )
    memory_config: dict[str, Any] | None = Field(
        default=None,
        description="Memory/context configuration",
        examples=[{"max_turns": 10, "context_window": 200000}],
    )
    is_active: bool = Field(
        default=True,
        description="Whether the agent is active and usable",
    )
    is_public: bool = Field(
        default=False,
        description="Whether the agent is publicly accessible",
    )


# =============================================================================
# Create Schemas
# =============================================================================


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""


# =============================================================================
# Update Schemas
# =============================================================================


class AgentUpdate(BaseSchema):
    """Schema for updating an agent.

    All fields are optional to support partial updates.
    """

    name: str | None = OptionalNameField
    description: str | None = Field(default=None, max_length=2000)
    model_provider: str | None = Field(default=None, description="Model provider")
    model_name: str | None = Field(default=None, description="Model name")
    system_prompt: str | None = Field(default=None, description="System prompt")
    config: dict[str, Any] | None = Field(
        default=None, description="Model configuration"
    )
    tools: list[str] | None = Field(default=None, description="Tool UUIDs")
    memory_config: dict[str, Any] | None = Field(
        default=None, description="Memory config"
    )
    is_active: bool | None = Field(default=None, description="Active status")
    is_public: bool | None = Field(default=None, description="Public status")


# =============================================================================
# Response Schemas
# =============================================================================


class AgentResponse(AgentBase, BaseResponse):
    """Schema for agent response."""

    owner_id: UUID = Field(
        ...,
        description="UUID of the agent owner",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class AgentListResponse(BaseSchema):
    """Schema for agent list items (summary view)."""

    id: UUID = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")
    model_provider: str = Field(..., description="Model provider")
    model_name: str = Field(..., description="Model name")
    is_active: bool = Field(..., description="Active status")
    is_public: bool = Field(..., description="Public status")
    created_at: str = Field(..., description="Creation timestamp")


# =============================================================================
# Agent Tool Association Schemas
# =============================================================================


class AgentToolAdd(BaseSchema):
    """Schema for adding a tool to an agent."""

    tool_id: UUID = Field(
        ...,
        description="UUID of the tool to add",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


__all__ = [
    "AgentBase",
    "AgentCreate",
    "AgentListResponse",
    "AgentResponse",
    "AgentToolAdd",
    "AgentUpdate",
    "AgentTestRequest",
    "AgentTestResponse",
]


class AgentTestRequest(BaseSchema):
    """Schema for agent test execution request."""

    input_data: dict[str, Any] = Field(
        ...,
        description="Input data to test the agent with",
        examples=[{"message": "Hello, how can you help me?"}],
    )


class AgentTestResponse(BaseSchema):
    """Schema for agent test execution response."""

    success: bool = Field(
        ...,
        description="Whether the agent execution was successful",
    )
    output: dict[str, Any] | None = Field(
        default=None,
        description="Agent output data",
=======
from datetime import datetime  # noqa: TC003 - Required at runtime for Pydantic
from typing import Any
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, Field

# =============================================================================
# Model Configuration Schema
# =============================================================================


class ModelConfig(BaseModel):
    """LLM model configuration for agents.

    Defines provider-specific settings for LLM models including
    temperature and token limits with validation constraints.

    Attributes:
        provider: LLM provider (anthropic|openai|glm)
        model: Model identifier
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens in response (1-128000)
    """

    provider: str = Field(
        ...,
        pattern="^(anthropic|openai|glm)$",
        description="LLM provider identifier",
        examples=["anthropic", "openai", "glm"],
    )
    model: str = Field(
        ...,
        description="Model identifier",
        examples=["claude-3-5-sonnet-20241022", "gpt-4o", "glm-4-plus"],
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="Sampling temperature (0=deterministic, 2=creative)",
        examples=[0.0, 0.7, 1.0, 2.0],
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens in model response",
        examples=[1, 4096, 8192, 128000],
    )


# =============================================================================
# Agent CRUD Schemas
# =============================================================================


class AgentCreate(BaseModel):
    """Schema for creating a new agent.

    All fields are required except description and tool_ids which are optional.
    The llm_config must include valid provider and model settings.

    Attributes:
        name: Agent display name (1-255 characters)
        description: Optional agent description
        system_prompt: System prompt for the agent (min 1 character)
        llm_config: LLM model configuration (aliased as model_config in API)
        tool_ids: List of tool UUIDs the agent can use
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Agent display name",
        examples=["Data Analyst", "Code Reviewer", "Research Assistant"],
    )
    description: str | None = Field(
        default=None,
        description="Optional description of agent's purpose",
        examples=["Analyzes financial data and generates reports"],
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        description="System prompt for the agent",
        examples=["You are a helpful assistant specialized in data analysis"],
    )
    llm_config: ModelConfig = Field(
        ...,
        alias="model_config",
        description="LLM model configuration",
    )
    tool_ids: list[UUID] = Field(
        default_factory=list,
        description="List of tool UUIDs the agent can use",
        examples=[["550e8400-e29b-41d4-a716-446655440001"]],
    )

    class Config:
        """Pydantic configuration for population by name."""

        populate_by_name = True


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent.

    All fields are optional to support partial updates.
    Only provided fields will be updated.

    Attributes:
        description: New description
        system_prompt: New system prompt
        llm_config: New model configuration (aliased as model_config in API)
        is_active: Active status
    """

    description: str | None = Field(
        default=None,
        description="Updated description",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Updated system prompt",
    )
    llm_config: ModelConfig | None = Field(
        default=None,
        alias="model_config",
        description="Updated model configuration",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the agent is active",
        examples=[True, False],
    )

    class Config:
        """Pydantic configuration for population by name."""

        populate_by_name = True


class AgentResponse(BaseModel):
    """Schema for agent in API responses.

    Includes all agent fields with timestamps and ORM support.
    Uses from_attributes for SQLAlchemy model conversion.

    Attributes:
        id: Agent unique identifier
        name: Agent display name
        description: Agent description
        system_prompt: System prompt
        llm_config: Model configuration (aliased as model_config in API)
        tool_ids: List of tool UUIDs
        is_active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID = Field(
        ...,
        description="Agent unique identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    name: str = Field(
        ...,
        description="Agent display name",
    )
    description: str | None = Field(
        default=None,
        description="Agent description",
    )
    system_prompt: str = Field(
        ...,
        description="System prompt",
    )
    llm_config: ModelConfig = Field(
        ...,
        alias="model_config",
        description="Model configuration",
    )
    tool_ids: list[UUID] = Field(
        ...,
        description="List of tool UUIDs",
    )
    is_active: bool = Field(
        ...,
        description="Whether the agent is active",
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )

    class Config:
        """Pydantic configuration for ORM mode."""

        from_attributes = True
        populate_by_name = True


# =============================================================================
# Tool Management Schema
# =============================================================================


class AgentToolsUpdate(BaseModel):
    """Schema for updating agent tool connections.

    Replaces the agent's tool list with the provided tool_ids.
    Empty list removes all tools.

    Attributes:
        tool_ids: New list of tool UUIDs
    """

    tool_ids: list[UUID] = Field(
        ...,
        description="List of tool UUIDs to connect to agent",
        examples=[["550e8400-e29b-41d4-a716-446655440001"]],
    )


# =============================================================================
# Test Execution Schemas
# =============================================================================


class AgentTestRequest(BaseModel):
    """Schema for agent test execution request.

    Sends a test prompt to the agent with timeout configuration.

    Attributes:
        test_prompt: Test message to send to agent (min 1 character)
        timeout: Test timeout in seconds (1-300, default 60)
    """

    test_prompt: str = Field(
        ...,
        min_length=1,
        description="Test message to send to agent",
        examples=["Hello, how are you?", "What is 2+2?"],
    )
    timeout: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Test timeout in seconds",
        examples=[30, 60, 120, 300],
    )


class AgentTestResponse(BaseModel):
    """Schema for agent test execution response.

    Returns test execution results including response, errors,
    tool calls, execution time, and token usage.

    Attributes:
        success: Whether test execution succeeded
        response: Agent response text (if successful)
        error: Error message (if failed)
        tool_calls: List of tool executions during test
        execution_time_ms: Execution time in milliseconds
        tokens_used: Token usage statistics
    """

    success: bool = Field(
        ...,
        description="Whether the test execution succeeded",
    )
    response: str | None = Field(
        default=None,
        description="Agent response text",
>>>>>>> origin/main
    )
    error: str | None = Field(
        default=None,
        description="Error message if execution failed",
    )
<<<<<<< HEAD
    execution_time_ms: float = Field(
        ...,
        description="Agent execution time in milliseconds",
        examples=[250.5],
    )
=======
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of tool executions during test",
        examples=[[{"name": "search", "args": {"query": "test"}}]],
    )
    execution_time_ms: int = Field(
        ...,
        description="Execution time in milliseconds",
        examples=[523, 1234, 5000],
    )
    tokens_used: dict[str, int] | None = Field(
        default=None,
        description="Token usage statistics",
        examples=[{"prompt": 10, "completion": 20, "total": 30}],
    )


__all__ = [
    "AgentCreate",
    "AgentResponse",
    "AgentTestRequest",
    "AgentTestResponse",
    "AgentToolsUpdate",
    "AgentUpdate",
    "ModelConfig",
]
>>>>>>> origin/main
