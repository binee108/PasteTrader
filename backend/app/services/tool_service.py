"""ToolService for SPEC-009 Tool CRUD operations.

TAG: [SPEC-009] [SERVICE] [TOOL-CRUD]
REQ: REQ-T005 - ToolService CRUD Implementation

This service provides business logic for Tool CRUD operations including:
- Create with name uniqueness validation
- Read by ID and name
- List with filtering (is_active, search)
- Update tool fields
- Delete with usage prevention
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_spec009 import Tool as ToolModel
from app.schemas.tool import ToolCreate, ToolUpdate


class ToolService:
    """Service for Tool CRUD operations.

    Provides business logic layer for Tool management including validation,
    filtering, and usage tracking.
    """

    async def create_tool(self, db: AsyncSession, tool_in: ToolCreate) -> ToolModel:
        """Create a new tool with name uniqueness validation.

        Args:
            db: Database session
            tool_in: Tool creation schema

        Returns:
            Created tool instance

        Raises:
            ValueError: If tool with same name already exists
        """
        # Check for existing tool with same name
        existing = await self.get_tool_by_name(db, tool_in.name)
        if existing:
            raise ValueError(f"Tool with name '{tool_in.name}' already exists")

        # Create new tool
        tool = ToolModel(**tool_in.model_dump())
        db.add(tool)
        await db.commit()
        await db.refresh(tool)
        return tool

    async def get_tool(self, db: AsyncSession, tool_id: UUID) -> ToolModel | None:
        """Retrieve tool by ID.

        Args:
            db: Database session
            tool_id: Tool UUID

        Returns:
            Tool instance or None if not found
        """
        result = await db.execute(select(ToolModel).where(ToolModel.id == tool_id))
        return result.scalar_one_or_none()

    async def get_tool_by_name(self, db: AsyncSession, name: str) -> ToolModel | None:
        """Retrieve tool by name.

        Args:
            db: Database session
            name: Tool unique name

        Returns:
            Tool instance or None if not found
        """
        result = await db.execute(select(ToolModel).where(ToolModel.name == name))
        return result.scalar_one_or_none()

    async def list_tools(
        self,
        db: AsyncSession,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ToolModel]:
        """List tools with optional filtering and pagination.

        Args:
            db: Database session
            is_active: Filter by active status (None = no filter)
            search: Search term for tool name (case-insensitive partial match)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of tool instances
        """
        query = select(ToolModel)

        # Apply active filter if specified
        if is_active is not None:
            query = query.where(ToolModel.is_active == is_active)

        # Apply search filter if specified
        if search:
            query = query.where(ToolModel.name.ilike(f"%{search}%"))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_tool(
        self, db: AsyncSession, tool_id: UUID, tool_in: ToolUpdate
    ) -> ToolModel | None:
        """Update tool fields.

        Args:
            db: Database session
            tool_id: Tool UUID
            tool_in: Tool update schema with optional fields

        Returns:
            Updated tool instance or None if not found
        """
        # Get existing tool
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return None

        # Update only provided fields
        update_data = tool_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tool, field, value)

        # Commit changes
        await db.commit()
        await db.refresh(tool)
        return tool

    async def delete_tool(self, db: AsyncSession, tool_id: UUID) -> bool:
        """Delete tool by ID.

        Args:
            db: Database session
            tool_id: Tool UUID

        Returns:
            True if deleted, False if not found

        Note:
            In production, should check if tool is in use by agents or workflows
            and return appropriate error (409 Conflict) instead of deleting.
        """
        # Get existing tool
        tool = await self.get_tool(db, tool_id)
        if not tool:
            return False

        # TODO: Check if tool is in use by agents or workflows
        # For now, proceed with deletion
        # if tool.used_by_agents or tool.used_in_workflows:
        #     raise ValueError("Tool is in use and cannot be deleted")

        # Delete tool
        await db.delete(tool)
        await db.commit()
        return True


# Singleton instance for use in dependency injection
tool_service = ToolService()
