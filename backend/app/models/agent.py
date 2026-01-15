"""Agent model for LLM-based AI agents.

TAG: [SPEC-009] [DATABASE] [AGENT]
REQ: REQ-003 - Agent Model Definition
REQ: REQ-004 - Model Provider Enum
REQ: REQ-005 - User-Agent Relationship

This module defines the Agent model for managing LLM-based AI agents
that can use tools and maintain conversation memory.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.tool import Tool
    from app.models.user import User

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")

# Association table for many-to-many relationship between Agent and Tool
# CASCADE delete: When an agent is deleted, remove its tool associations
#                   When a tool is deleted, remove its agent associations
agent_tools = Table(
    "agent_tools",
    Base.metadata,
    Column(
        "agent_id",
        GUID(),
        ForeignKey("agents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tool_id",
        GUID(),
        ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    comment="Many-to-many relationship between agents and tools",
)


class Agent(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Agent model for LLM-based AI agents.

    Represents a configurable AI agent that can execute tools and
    maintain conversation context within workflows.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        owner_id: UUID of the user who owns this agent
        name: Display name of the agent (unique)
        description: Optional description of the agent's purpose
        system_prompt: System prompt for the agent (required)
        model_config: JSONB configuration for model parameters
        tools: Many-to-many relationship with Tool
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
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # System prompt (required)
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Model configuration as JSONB (replaces separate model_provider/model_name fields)
    model_config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
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

    # Note: tools relationship manages Tool connections via agent_tools table
    tools: Mapped[list[Tool]] = relationship(
        "Tool",
        secondary=agent_tools,
        back_populates="agents",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation of the agent."""
        provider = self.model_config.get("provider", "unknown")
        return f"<Agent(id={self.id}, name='{self.name}', provider={provider})>"


__all__ = ["Agent", "agent_tools"]
