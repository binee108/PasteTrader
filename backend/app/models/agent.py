"""Agent model for LLM-based AI agents.

TAG: [SPEC-004] [DATABASE] [AGENT]
REQ: REQ-003 - Agent Model Definition
REQ: REQ-004 - Model Provider Enum
REQ: REQ-005 - User-Agent Relationship

This module defines the Agent model for managing LLM-based AI agents
that can use tools and maintain conversation memory.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ModelProvider

if TYPE_CHECKING:
    from app.models.user import User

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Agent(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Agent model for LLM-based AI agents.

    Represents a configurable AI agent that can execute tools and
    maintain conversation context within workflows.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        owner_id: UUID of the user who owns this agent
        name: Display name of the agent
        description: Optional description of the agent's purpose
        model_provider: LLM provider (anthropic, openai, glm)
        model_name: Specific model identifier
        system_prompt: System prompt for the agent
        config: JSONB configuration for model parameters
        tools: List of tool UUIDs the agent can use
        memory_config: Memory/context configuration
        is_active: Whether the agent is active and usable
        is_public: Whether the agent is publicly accessible
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
    """

    __tablename__ = "agents"

    # Foreign key to users table (string reference for forward compatibility)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Model configuration
    model_provider: Mapped[ModelProvider] = mapped_column(
        String(50),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # JSON fields for flexible configuration (JSONB on PostgreSQL, JSON on SQLite)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # List of tool UUIDs as JSON array
    tools: Mapped[list[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        server_default="[]",
    )

    memory_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Status flags
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Relationships
    owner: Mapped[User] = relationship(
        "User",
        back_populates="agents",
    )

    def __repr__(self) -> str:
        """Return string representation of the agent."""
        return (
            f"<Agent(id={self.id}, name='{self.name}', provider={self.model_provider})>"
        )


__all__ = ["Agent"]
