"""Agent schemas for API request/response validation.

TAG: [SPEC-009] [SCHEMAS] [AGENT]
REQ: REQ-001 - Agent CRUD Schemas
REQ: REQ-002 - Agent Tool Association Schemas

This module defines Pydantic schemas for Agent API validation.
"""

from __future__ import annotations

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
]
