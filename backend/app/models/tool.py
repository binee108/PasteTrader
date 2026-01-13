"""Tool model for external tool execution.

TAG: [SPEC-004] [DATABASE] [TOOL]
REQ: REQ-001 - Tool Model Definition
REQ: REQ-002 - Tool Type Enum Update
REQ: REQ-005 - User-Tool Relationship

This module defines the Tool model for managing external tools
including HTTP APIs, MCP servers, Python functions, shell commands,
and builtin utilities.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ToolType

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.user import User

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Tool(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Tool model for external tool execution.

    Represents a configurable tool that can be used in workflow nodes.
    Supports multiple tool types: HTTP, MCP, Python, Shell, and Builtin.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        owner_id: UUID of the user who owns this tool
        name: Display name of the tool
        description: Optional description of the tool's purpose
        tool_type: Type of tool (http, mcp, python, shell, builtin)
        config: JSONB configuration specific to tool type
        input_schema: JSON Schema for tool input validation
        output_schema: JSON Schema for tool output validation
        auth_config: Encrypted authentication configuration
        rate_limit: Rate limiting configuration
        is_active: Whether the tool is active and usable
        is_public: Whether the tool is publicly accessible
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
    """

    __tablename__ = "tools"

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

    # Tool type enum
    tool_type: Mapped[ToolType] = mapped_column(
        String(50),
        nullable=False,
    )

    # JSON fields for flexible configuration (JSONB on PostgreSQL, JSON on SQLite)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    auth_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    rate_limit: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    # Relationships
    owner: Mapped[User] = relationship(
        "User",
        back_populates="tools",
    )

    agents: Mapped[list[Agent]] = relationship(
        "app.models.agent.Agent",
        secondary="agent_tools",
        back_populates="tools",
    )

    def get_masked_auth_config(self) -> dict[str, Any] | None:
        """Get a masked version of auth_config for display/logging.

        Returns a copy of auth_config with sensitive field values masked.
        Returns None if auth_config is None.

        Returns:
            Masked auth_config dictionary or None

        Example:
            >>> tool = Tool(auth_config={"api_key": "secret123"})
            >>> masked = tool.get_masked_auth_config()
            >>> masked["api_key"]
            '***'
        """
        from app.utils.crypto import mask_auth_config

        return mask_auth_config(self.auth_config)

    def __repr__(self) -> str:
        """Return string representation of the tool."""
        return f"<Tool(id={self.id}, name='{self.name}', type={self.tool_type})>"


__all__ = ["Tool"]
