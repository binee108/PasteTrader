"""Tool model for external tool execution.

TAG: [SPEC-004] [DATABASE] [TOOL]
REQ: REQ-001 - Tool Model Definition
REQ: REQ-002 - Tool Type Enum Update

This module defines the Tool model for managing external tools
including HTTP APIs, MCP servers, Python functions, shell commands,
and builtin utilities.
"""

import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ToolType

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
        PG_UUID(as_uuid=True),
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

    def __repr__(self) -> str:
        """Return string representation of the tool."""
        return f"<Tool(id={self.id}, name='{self.name}', type={self.tool_type})>"


__all__ = ["Tool"]
