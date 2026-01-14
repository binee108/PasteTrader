"""Tool service layer.

TAG: [SPEC-009] [API] [SERVICE] [TOOL]
REQ: REQ-001 - ToolService CRUD Operations
REQ: REQ-002 - Tool Test Execution
REQ: REQ-003 - Tool Filtering and Search

This module provides service layer abstractions for tool management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.models.tool import Tool

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Exceptions
# =============================================================================


class ToolServiceError(Exception):
    """Base exception for tool service errors."""


class ToolNotFoundError(ToolServiceError):
    """Raised when a tool is not found."""


class ToolExecutionError(ToolServiceError):
    """Raised when tool execution fails."""


# =============================================================================
# ToolService
# =============================================================================


class ToolService:
    """Service for tool CRUD operations.

    TAG: [SPEC-009] [API] [SERVICE] [TOOL]
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize tool service."""
        self.db = db

    async def create(self, owner_id: UUID, data: Any) -> Tool:
        """Create a new tool.

        Args:
            owner_id: UUID of the tool owner.
            data: ToolCreate schema with tool data.

        Returns:
            Created Tool instance.

        Raises:
            ToolServiceError: If creation fails.
        """
        try:
            tool = Tool(
                owner_id=owner_id,
                name=data.name,
                description=data.description,
                tool_type=data.tool_type,
                config=data.config,
                input_schema=data.input_schema,
                output_schema=data.output_schema,
                auth_config=data.auth_config,
                rate_limit=data.rate_limit,
                is_active=data.is_active,
                is_public=data.is_public,
            )
            self.db.add(tool)
            await self.db.flush()
            await self.db.refresh(tool)
            return tool
        except Exception as e:
            raise ToolServiceError(f"Failed to create tool: {e}") from e

    async def get(
        self, tool_id: UUID, include_deleted: bool = False
    ) -> Tool | None:
        """Get a tool by ID.

        Args:
            tool_id: UUID of the tool to retrieve.
            include_deleted: If True, include soft-deleted tools.

        Returns:
            The Tool if found, None otherwise.
        """
        query = select(Tool).where(Tool.id == tool_id)

        if not include_deleted:
            query = query.where(Tool.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
        tool_type: str | None = None,
        is_active: bool | None = None,
        is_public: bool | None = None,
        include_deleted: bool = False,
    ) -> list[Tool]:
        """List tools with pagination and filtering.

        Args:
            owner_id: UUID of the tool owner.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            tool_type: Optional filter by tool type.
            is_active: Optional filter by active status.
            is_public: Optional filter by public status.
            include_deleted: If True, include soft-deleted tools.

        Returns:
            List of Tool records.
        """
        query = select(Tool).where(Tool.owner_id == owner_id)

        if tool_type is not None:
            query = query.where(Tool.tool_type == tool_type)

        if is_active is not None:
            query = query.where(Tool.is_active == is_active)

        if is_public is not None:
            query = query.where(Tool.is_public == is_public)

        if not include_deleted:
            query = query.where(Tool.deleted_at.is_(None))

        query = query.offset(skip).limit(limit).order_by(Tool.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        owner_id: UUID,
        tool_type: str | None = None,
        is_active: bool | None = None,
        is_public: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count tools with optional filtering.

        Args:
            owner_id: UUID of the tool owner.
            tool_type: Optional filter by tool type.
            is_active: Optional filter by active status.
            is_public: Optional filter by public status.
            include_deleted: If True, include soft-deleted tools.

        Returns:
            Count of matching tools.
        """
        query = select(func.count()).where(Tool.owner_id == owner_id)

        if tool_type is not None:
            query = query.where(Tool.tool_type == tool_type)

        if is_active is not None:
            query = query.where(Tool.is_active == is_active)

        if is_public is not None:
            query = query.where(Tool.is_public == is_public)

        if not include_deleted:
            query = query.where(Tool.deleted_at.is_(None))

        result = await self.db.scalar(query)
        return result or 0

    async def update(self, tool_id: UUID, data: Any) -> Tool:
        """Update a tool.

        Args:
            tool_id: UUID of the tool to update.
            data: ToolUpdate schema with fields to update.

        Returns:
            Updated Tool instance.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolServiceError: If update fails.
        """
        tool = await self.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id} not found")

        try:
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(tool, field):
                    setattr(tool, field, value)

            tool.updated_at = datetime.now(UTC)

            await self.db.flush()
            await self.db.refresh(tool)
            return tool
        except Exception as e:
            raise ToolServiceError(f"Failed to update tool: {e}") from e

    async def delete(self, tool_id: UUID) -> Tool:
        """Soft delete a tool.

        Args:
            tool_id: UUID of the tool to delete.

        Returns:
            Deleted Tool instance.

        Raises:
            ToolNotFoundError: If tool not found.
        """
        tool = await self.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id} not found")

        tool.soft_delete()
        await self.db.flush()
        await self.db.refresh(tool)
        return tool

    async def test_execute(self, tool_id: UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        """Test execute a tool with sample input.

        Args:
            tool_id: UUID of the tool to test.
            input_data: Input data for tool execution.

        Returns:
            Dictionary with execution results.

        Raises:
            ToolNotFoundError: If tool not found.
            ToolExecutionError: If execution fails.
        """
        import time

        tool = await self.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id} not found")

        if not tool.is_active:
            raise ToolExecutionError(f"Tool {tool_id} is not active")

        try:
            start_time = time.time()

            # TODO: Implement actual tool execution based on tool_type
            # For now, return a mock response
            execution_time_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "output": {"message": "Tool execution simulated", "input": input_data},
                "error": None,
                "execution_time_ms": execution_time_ms,
            }
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            raise ToolExecutionError(
                f"Tool execution failed: {e}"
            ) from e


__all__ = [
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolService",
    "ToolServiceError",
]
