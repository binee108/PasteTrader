"""Tool model for SPEC-009 ToolRegistry integration.

TAG: [SPEC-009] [DATABASE] [TOOL-MODEL]
REQ: SPEC-009 Tool Model Definition

This module defines the Tool SQLAlchemy model for ToolRegistry integration.
This is different from the SPEC-004 Tool model:
- SPEC-004 Tool: Workflow node external tools (HTTP, MCP, Python, Shell, Builtin)
- SPEC-009 Tool: meta_llm ToolRegistry integration tools

SPEC-009 Tool fields:
- id: UUID primary key
- name: Unique tool name
- description: Optional description
- parameters: JSON Schema for tool input validation
- implementation_path: Python import path for tool implementation
- is_active: Whether the tool is active
- created_at: Timestamp of creation
- updated_at: Timestamp of last update
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

# Use JSONB for PostgreSQL, JSON for SQLite (testing)
JSONType = SQLiteJSON().with_variant(JSONB(), "postgresql")

# Independent Base for SPEC-009 Tool to avoid conflicts with SPEC-004 Tool
Spec009Base = declarative_base()


def _generate_uuid() -> uuid.UUID:
    """Generate UUID for default value.

    Using a function instead of direct reference to avoid issues with
    SQLAlchemy's introspection.
    """
    return uuid.uuid4()


class Tool(Spec009Base):
    """Tool model for SPEC-009 ToolRegistry integration.

    Represents a tool that can be registered in meta_llm's ToolRegistry.
    Tools are Python functions with JSON Schema parameter validation.

    Attributes:
        id: UUID primary key
        name: Unique tool name (e.g., "price_fetcher", "indicator_calculator")
        description: Optional description of the tool's purpose
        parameters: JSON Schema for tool input validation
        implementation_path: Python import path (e.g., "meta_llm.tools.data.PriceFetcher")
        is_active: Whether the tool is active and usable
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "tools_spec009"

    # UUID primary key
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=_generate_uuid,
        nullable=False,
    )

    # Tool name (unique constraint)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Optional description
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # JSON Schema for parameter validation
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )

    # Python import path for implementation
    implementation_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Active status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation of the tool."""
        return f"<Tool(id={self.id}, name='{self.name}', is_active={self.is_active})>"


__all__ = ["Tool"]
