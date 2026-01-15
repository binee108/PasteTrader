<<<<<<< HEAD
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

from app.core.exceptions import InvalidToolConfigError, ResourceInUseError
from app.models.agent import Agent
from app.models.tool import Tool
from app.models.workflow import Workflow, Node

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

    # 도구 타입별 필수 필드 매핑
    REQUIRED_FIELDS_BY_TYPE: dict[str, list[str]] = {
        "http": ["url"],
        "python": ["code"],
        "shell": ["command"],
        "mcp": ["server_url"],
    }

    def __init__(self, db: AsyncSession) -> None:
        """Initialize tool service."""
        self.db = db

    def _validate_tool_config(self, tool_type: str, config: dict[str, Any]) -> None:
        """도구 설정의 유효성을 검증합니다.

        Args:
            tool_type: 도구 타입
            config: 도구 설정 딕셔너리

        Raises:
            InvalidToolConfigError: 필수 필드가 누락된 경우
        """
        required_fields = self.REQUIRED_FIELDS_BY_TYPE.get(tool_type, [])

        # builtin 타입은 config 검증이 필요 없음
        if tool_type == "builtin":
            return

        # 누락된 필드 확인
        missing_fields: list[str] = []
        for field in required_fields:
            if field not in config or config[field] is None:
                missing_fields.append(field)

        if missing_fields:
            raise InvalidToolConfigError(
                tool_type=tool_type,
                missing_fields=missing_fields,
            )

    async def create(self, owner_id: UUID, data: Any) -> Tool:
        """Create a new tool.

        Args:
            owner_id: UUID of the tool owner.
            data: ToolCreate schema with tool data.

        Returns:
            Created Tool instance.

        Raises:
            ToolServiceError: If creation fails.
            InvalidToolConfigError: If required config fields are missing.
        """
        # 서비스 수준에서도 config 유효성 검증 수행 (이중 체크)
        self._validate_tool_config(data.tool_type, data.config)

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
        except InvalidToolConfigError:
            # InvalidToolConfigError는 그대로 전파
            raise
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
        is_active: bool | None = True,
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
        is_active: bool | None = True,
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
            ResourceInUseError: If tool is used in agents or workflows.
        """
        tool = await self.get(tool_id)
        if tool is None:
            raise ToolNotFoundError(f"Tool {tool_id} not found")

        # X-002: 에이전트 및 워크플로우에서 사용 중인지 확인
        tool_id_str = str(tool_id)
        references = []
        
        # 1. Agent 테이블의 tools 배열에서 확인
        agent_query = select(Agent).where(Agent.deleted_at.is_(None))
        agent_result = await self.db.execute(agent_query)
        agents = agent_result.scalars().all()
        
        for agent in agents:
            if tool_id_str in agent.tools:
                references.append({
                    "type": "agent",
                    "id": str(agent.id),
                    "name": agent.name
                })
        
        # 2. Node 테이블에서 확인 (tool_type 노드)
        node_query = select(Node, Workflow).join(
            Workflow, Node.workflow_id == Workflow.id
        ).where(
            Node.tool_id == tool_id_str,
            Workflow.deleted_at.is_(None)
        )
        
        node_result = await self.db.execute(node_query)
        node_workflow_pairs = node_result.all()
        
        for node, workflow in node_workflow_pairs:
            references.append({
                "type": "workflow",
                "id": str(workflow.id),
                "name": workflow.name
            })
        
        if references:
            raise ResourceInUseError(
                resource_type="tool",
                resource_id=tool_id_str,
                references=references
            )

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
=======
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
>>>>>>> origin/main
