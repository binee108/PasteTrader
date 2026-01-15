<<<<<<< HEAD
"""Agent service layer.

TAG: [SPEC-009] [API] [SERVICE] [AGENT]
REQ: REQ-001 - AgentService CRUD Operations
REQ: REQ-002 - Agent Tool Association
REQ: REQ-003 - Agent Filtering and Search

This module provides service layer abstractions for agent management.
"""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import attributes

from app.core.exceptions import ResourceInUseError
from app.models.agent import Agent
from app.models.tool import Tool
from app.models.workflow import Node, Workflow

from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Exceptions
# =============================================================================


class AgentServiceError(Exception):
    """Base exception for agent service errors."""


class AgentNotFoundError(AgentServiceError):
    """Raised when an agent is not found."""


class ToolNotFoundError(AgentServiceError):
    """Raised when a tool is not found or is inactive."""


class ToolAlreadyAssociatedError(AgentServiceError):
    """Raised when a tool is already associated with an agent."""


    """Raised when attempting to add an inactive tool to an agent."""


class AgentExecutionError(AgentServiceError):
    """Raised when agent execution fails."""


# =============================================================================
# AgentService
# =============================================================================


class AgentService:
    """Service for agent CRUD operations.

    TAG: [SPEC-009] [API] [SERVICE] [AGENT]
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize agent service."""
        self.db = db

    async def create(self, owner_id: UUID, data: Any) -> Agent:
        """Create a new agent.

        Args:
            owner_id: UUID of the agent owner.
            data: AgentCreate schema with agent data.

        Returns:
            Created Agent instance.

        Raises:
            AgentServiceError: If creation fails.
        """
        try:
            agent = Agent(
                owner_id=owner_id,
                name=data.name,
                description=data.description,
                model_provider=data.model_provider,
                model_name=data.model_name,
                system_prompt=data.system_prompt,
                config=data.config,
                tools=data.tools or [],
                memory_config=data.memory_config,
                is_active=data.is_active,
                is_public=data.is_public,
            )
            self.db.add(agent)
            await self.db.flush()
            await self.db.refresh(agent)
            return agent
        except Exception as e:
            raise AgentServiceError(f"Failed to create agent: {e}") from e

    async def get(
        self, agent_id: UUID, include_deleted: bool = False
    ) -> Agent | None:
        """Get an agent by ID.

        Args:
            agent_id: UUID of the agent to retrieve.
            include_deleted: If True, include soft-deleted agents.

        Returns:
            The Agent if found, None otherwise.
        """
        query = select(Agent).where(Agent.id == agent_id)

        if not include_deleted:
            query = query.where(Agent.deleted_at.is_(None))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 20,
        model_provider: str | None = None,
        is_active: bool | None = True,
        is_public: bool | None = None,
        include_deleted: bool = False,
    ) -> list[Agent]:
        """List agents with pagination and filtering.

        Args:
            owner_id: UUID of the agent owner.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            model_provider: Optional filter by model provider.
            is_active: Optional filter by active status.
            is_public: Optional filter by public status.
            include_deleted: If True, include soft-deleted agents.

        Returns:
            List of Agent records.
        """
        query = select(Agent).where(Agent.owner_id == owner_id)

        if model_provider is not None:
            query = query.where(Agent.model_provider == model_provider)

        if is_active is not None:
            query = query.where(Agent.is_active == is_active)

        if is_public is not None:
            query = query.where(Agent.is_public == is_public)

        if not include_deleted:
            query = query.where(Agent.deleted_at.is_(None))

        query = query.offset(skip).limit(limit).order_by(Agent.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        owner_id: UUID,
        model_provider: str | None = None,
        is_active: bool | None = True,
        is_public: bool | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count agents with optional filtering.

        Args:
            owner_id: UUID of the agent owner.
            model_provider: Optional filter by model provider.
            is_active: Optional filter by active status.
            is_public: Optional filter by public status.
            include_deleted: If True, include soft-deleted agents.

        Returns:
            Count of matching agents.
        """
        query = select(func.count()).where(Agent.owner_id == owner_id)

        if model_provider is not None:
            query = query.where(Agent.model_provider == model_provider)

        if is_active is not None:
            query = query.where(Agent.is_active == is_active)

        if is_public is not None:
            query = query.where(Agent.is_public == is_public)

        if not include_deleted:
            query = query.where(Agent.deleted_at.is_(None))

        result = await self.db.scalar(query)
        return result or 0

    async def update(self, agent_id: UUID, data: Any) -> Agent:
        """Update an agent.

        Args:
            agent_id: UUID of the agent to update.
            data: AgentUpdate schema with fields to update.

        Returns:
            Updated Agent instance.

        Raises:
            AgentNotFoundError: If agent not found.
            AgentServiceError: If update fails.
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        try:
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(agent, field):
                    setattr(agent, field, value)

            agent.updated_at = datetime.now(UTC)

            await self.db.flush()
            await self.db.refresh(agent)
            return agent
        except Exception as e:
            raise AgentServiceError(f"Failed to update agent: {e}") from e

    async def delete(self, agent_id: UUID) -> Agent:
        """Soft delete an agent.

        Args:
            agent_id: UUID of the agent to delete.

        Returns:
            Deleted Agent instance.

        Raises:
            AgentNotFoundError: If agent not found.
            ResourceInUseError: If agent is used in workflows.
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        # X-001: 워크플로우에서 사용 중인지 확인
        agent_id_str = str(agent_id)
        
        # Node 테이블에서 이 agent를 사용하는 노드 찾기
        node_query = select(Node, Workflow).join(
            Workflow, Node.workflow_id == Workflow.id
        ).where(
            Node.agent_id == agent_id_str,
            Workflow.deleted_at.is_(None)
        )
        
        node_result = await self.db.execute(node_query)
        node_workflow_pairs = node_result.all()
        
        if node_workflow_pairs:
            # 참조 정보 수집
            references = [
                {"type": "workflow", "id": str(workflow.id), "name": workflow.name}
                for node, workflow in node_workflow_pairs
            ]
            # 중복 제거 (workflow ID로)
            seen = set()
            unique_references = []
            for ref in references:
                if ref["id"] not in seen:
                    seen.add(ref["id"])
                    unique_references.append(ref)
            
            raise ResourceInUseError(
                resource_type="agent",
                resource_id=agent_id_str,
                references=unique_references
            )

        agent.soft_delete()
        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def add_tool(self, agent_id: UUID, tool_id: UUID) -> Agent:
        """Add a tool to an agent.

        Validates that:
        1. The tool exists in the database
        2. The tool is active (is_active=True)
        3. The tool is not already associated with the agent

        Args:
            agent_id: UUID of the agent.
            tool_id: UUID of the tool to add.

        Returns:
            Updated Agent instance.

        Raises:
            AgentNotFoundError: If agent not found.
            ToolNotFoundError: If tool not found or deleted.
            ToolAlreadyAssociatedError: If tool already associated.
        """
        # Check if agent exists
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        tool_id_str = str(tool_id)

        # Check if tool is already associated
        if tool_id_str in agent.tools:
            raise ToolAlreadyAssociatedError(
                f"Tool {tool_id} already associated with agent {agent_id}"
            )


        # Add tool to agent
        agent.tools.append(tool_id_str)
        agent.updated_at = datetime.now(UTC)

        # Flag the tools field as modified for SQLAlchemy
        attributes.flag_modified(agent, "tools")

        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def remove_tool(self, agent_id: UUID, tool_id: UUID) -> Agent:
        """Remove a tool from an agent.

        Args:
            agent_id: UUID of the agent.
            tool_id: UUID of the tool to remove.

        Returns:
            Updated Agent instance.

        Raises:
            AgentNotFoundError: If agent not found.
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        tool_id_str = str(tool_id)
        if tool_id_str in agent.tools:
            agent.tools.remove(tool_id_str)
            agent.updated_at = datetime.now(UTC)
            # Flag the tools field as modified for SQLAlchemy
            attributes.flag_modified(agent, "tools")

        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def cleanup_tool_references(self, tool_id: UUID) -> builtins.list[str]:
        """Remove a deleted tool from all agents' tools arrays.

        When a tool is deleted, this method should be called to clean up
        references to the tool ID in all agents.

        Args:
            tool_id: UUID of the deleted tool.

        Returns:
            List of agent IDs that were updated.
        """
        tool_id_str = str(tool_id)

        # Find all agents that reference this tool
        agent_query = select(Agent).where(
            Agent.deleted_at.is_(None)
        )
        agent_result = await self.db.execute(agent_query)
        agents = agent_result.scalars().all()

        updated_agent_ids = []

        for agent in agents:
            if tool_id_str in agent.tools:
                agent.tools.remove(tool_id_str)
                agent.updated_at = datetime.now(UTC)
                attributes.flag_modified(agent, "tools")
                updated_agent_ids.append(str(agent.id))

        if updated_agent_ids:
            await self.db.flush()

        return updated_agent_ids

    async def validate_tool_references(self, agent_id: UUID) -> dict[str, Any]:
        """Validate that all tools referenced by an agent exist and are active.

        This method checks each tool ID in the agent's tools array and returns
        a report of any invalid or inactive tool references.

        Args:
            agent_id: UUID of the agent to validate.

        Returns:
            Dictionary with validation results:
                - valid: List of valid tool IDs
                - missing: List of tool IDs that don't exist
                - inactive: List of tool IDs that exist but are not active
                - deleted: List of tool IDs that have been soft-deleted

        Raises:
            AgentNotFoundError: If agent not found.
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        if not agent.tools:
            return {
                "valid": [],
                "missing": [],
                "inactive": [],
                "deleted": [],
            }

        # Query all tools at once
        tool_ids = [UUID(tool_id_str) for tool_id_str in agent.tools]
        tool_query = select(Tool).where(Tool.id.in_(tool_ids))
        tool_result = await self.db.execute(tool_query)
        existing_tools = tool_result.scalars().all()

        # Categorize tool IDs
        existing_tool_ids = {str(tool.id) for tool in existing_tools}
        valid_tools = []
        inactive_tools = []
        missing_tools = []

        for tool_id_str in agent.tools:
            if tool_id_str not in existing_tool_ids:
                # Tool doesn't exist - check if it was deleted
                deleted_query = select(Tool).where(
                    Tool.id == UUID(tool_id_str),
                    Tool.deleted_at.isnot(None)
                )
                deleted_result = await self.db.execute(deleted_query)
                deleted_tool = deleted_result.scalar_one_or_none()

                if deleted_tool:
                    # Soft-deleted tools are tracked separately
                    pass
                else:
                    # Tool ID doesn't exist at all
                    missing_tools.append(tool_id_str)
            else:
                # Tool exists, check if active
                for tool in existing_tools:
                    if str(tool.id) == tool_id_str:
                        if tool.is_active:
                            valid_tools.append(tool_id_str)
                        else:
                            inactive_tools.append(tool_id_str)
                        break

        return {
            "valid": valid_tools,
            "missing": missing_tools,
            "inactive": inactive_tools,
            "deleted": [],  # Soft-deleted tools not tracked separately
        }

    async def test_execute(self, agent_id: UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        """Test execute an agent with sample input.

        Args:
            agent_id: UUID of the agent to test.
            input_data: Input data for agent execution.

        Returns:
            Dictionary with execution results.

        Raises:
            AgentNotFoundError: If agent not found.
            AgentExecutionError: If execution fails.
        """
        import time

        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        if not agent.is_active:
            raise AgentExecutionError(f"Agent {agent_id} is not active")

        start_time = time.time()
        try:

            # TODO: Implement actual agent execution based on model_provider
            # For now, return a mock response
            execution_time_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "output": {
                    "message": f"Agent '{agent.name}' execution simulated",
                    "input": input_data,
                    "model_provider": agent.model_provider,
                    "model_name": agent.model_name,
                },
                "error": None,
                "execution_time_ms": execution_time_ms,
            }
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            raise AgentExecutionError(
                f"Agent execution failed: {e}"
            ) from e


__all__ = [
    "AgentNotFoundError",
    "AgentService",
    "AgentServiceError",
    "ToolAlreadyAssociatedError",
    "ToolNotFoundError",
    "AgentExecutionError",
]
=======
"""AgentService for Agent CRUD operations.

TAG: [SPEC-009] [SERVICE] [AGENT]
REQ: REQ-006 - Agent Service Business Logic
REQ: REQ-007 - Agent CRUD Operations

This module provides the business logic layer for Agent CRUD operations
including name uniqueness validation, tool connection management, and
query filtering with pagination.
"""

from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent as AgentModel, agent_tools
from app.models.tool import Tool as ToolModel
from app.schemas.agent import (
    AgentCreate,
    AgentToolsUpdate,
    AgentUpdate,
)


class AgentService:
    """Service for Agent CRUD operations.

    Provides business logic for creating, reading, updating, and deleting agents.
    Handles name uniqueness validation, tool ID validation, and tool connection
    management through the agent_tools association table.
    """

    async def create_agent(
        self, db: AsyncSession, agent_in: AgentCreate, owner_id: UUID
    ) -> AgentModel:
        """Create a new agent with validation.

        Args:
            db: Database session
            agent_in: Agent creation data
            owner_id: UUID of the user who will own this agent

        Returns:
            AgentModel: Created agent instance

        Raises:
            ValueError: If agent name already exists or tool IDs are invalid
        """
        # Check name uniqueness
        existing = await self.get_agent_by_name(db, agent_in.name)
        if existing:
            raise ValueError(f"Agent with name '{agent_in.name}' already exists")

        # Validate tool IDs
        if agent_in.tool_ids:
            valid_tools = await self._validate_tool_ids(db, agent_in.tool_ids)
            if len(valid_tools) != len(agent_in.tool_ids):
                invalid_ids = set(agent_in.tool_ids) - set(valid_tools)
                raise ValueError(f"Invalid tool IDs: {invalid_ids}")

        # Prepare agent data
        agent_data = agent_in.model_dump()
        # Map llm_config -> model_config for database
        agent_data["model_config"] = agent_data.pop("llm_config")
        agent_data["owner_id"] = owner_id

        # Remove tool_ids from agent_data (handled separately)
        agent_data.pop("tool_ids", None)

        agent = AgentModel(**agent_data)

        db.add(agent)
        await db.flush()  # Get agent ID before adding tool connections

        # Add tool connections using direct INSERT
        if agent_in.tool_ids:
            for tool_id in agent_in.tool_ids:
                # Verify tool exists
                tool = await db.get(ToolModel, tool_id)
                if tool:
                    # Insert into association table
                    await db.execute(
                        insert(agent_tools).values(agent_id=agent.id, tool_id=tool_id)
                    )

        await db.commit()

        # Reload agent with tools
        return await self.get_agent(db, agent.id)

    async def get_agent(self, db: AsyncSession, agent_id: UUID) -> AgentModel | None:
        """Get an agent by ID with tools loaded.

        Args:
            db: Database session
            agent_id: UUID of the agent to retrieve

        Returns:
            AgentModel | None: Agent instance or None if not found
        """
        result = await db.execute(
            select(AgentModel)
            .options(selectinload(AgentModel.tools))
            .where(AgentModel.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_agent_by_name(self, db: AsyncSession, name: str) -> AgentModel | None:
        """Get an agent by name.

        Args:
            db: Database session
            name: Agent name to search for

        Returns:
            AgentModel | None: Agent instance or None if not found
        """
        result = await db.execute(select(AgentModel).where(AgentModel.name == name))
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        db: AsyncSession,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AgentModel]:
        """List agents with optional filtering and pagination.

        Args:
            db: Database session
            is_active: Filter by active status (None = no filter)
            search: Search string for agent name (case-insensitive)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            list[AgentModel]: List of agents matching the criteria
        """
        query = select(AgentModel)

        if is_active is not None:
            query = query.where(AgentModel.is_active == is_active)

        if search:
            query = query.where(AgentModel.name.ilike(f"%{search}%"))

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_agent(
        self, db: AsyncSession, agent_id: UUID, agent_in: AgentUpdate
    ) -> AgentModel | None:
        """Update an existing agent.

        Args:
            db: Database session
            agent_id: UUID of the agent to update
            agent_in: Agent update data (partial)

        Returns:
            AgentModel | None: Updated agent instance or None if not found
        """
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return None

        update_data = agent_in.model_dump(exclude_unset=True)

        # Map model_config -> llm_config for database
        if "llm_config" in update_data:
            update_data["model_config"] = update_data.pop("llm_config")

        for field, value in update_data.items():
            setattr(agent, field, value)

        await db.commit()
        await db.refresh(agent, ["tools"])
        return agent

    async def update_agent_tools(
        self, db: AsyncSession, agent_id: UUID, tools_update: AgentToolsUpdate
    ) -> AgentModel | None:
        """Update an agent's tool connections.

        Replaces the agent's tool list with the provided tool_ids.
        Empty list removes all tools.

        Args:
            db: Database session
            agent_id: UUID of the agent to update
            tools_update: Tool IDs to connect to the agent

        Returns:
            AgentModel | None: Updated agent instance or None if not found

        Raises:
            ValueError: If tool IDs are invalid
        """
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return None

        # Validate tool IDs
        valid_tools = await self._validate_tool_ids(db, tools_update.tool_ids)
        if len(valid_tools) != len(tools_update.tool_ids):
            invalid_ids = set(tools_update.tool_ids) - set(valid_tools)
            raise ValueError(f"Invalid tool IDs: {invalid_ids}")

        # Clear existing tool connections using direct DELETE
        await db.execute(delete(agent_tools).where(agent_tools.c.agent_id == agent_id))

        # Add new tool connections using direct INSERT
        for tool_id in tools_update.tool_ids:
            await db.execute(
                insert(agent_tools).values(agent_id=agent_id, tool_id=tool_id)
            )

        await db.commit()

        # Reload agent from database to get updated tools
        await db.refresh(agent, ["tools"])
        return agent

    async def delete_agent(self, db: AsyncSession, agent_id: UUID) -> bool:
        """Delete an agent.

        Args:
            db: Database session
            agent_id: UUID of the agent to delete

        Returns:
            bool: True if deleted, False if not found

        Note:
            Currently does not check if agent is in use. This should be
            implemented when Workflow model is available (409 Conflict).
        """
        agent = await self.get_agent(db, agent_id)
        if not agent:
            return False

        # TODO: Check if agent is used in any workflow
        # When Workflow model is available, add:
        # workflow_count = await db.execute(
        #     select(func.count(Workflow.id))
        #     .where(Workflow.agent_id == agent_id)
        # )
        # if workflow_count.scalar() > 0:
        #     return False  # Or raise HTTPException 409

        await db.delete(agent)
        await db.commit()
        return True

    async def _validate_tool_ids(
        self, db: AsyncSession, tool_ids: list[UUID]
    ) -> list[UUID]:
        """Validate that tool IDs exist and are active.

        Args:
            db: Database session
            tool_ids: List of tool IDs to validate

        Returns:
            list[UUID]: List of valid tool IDs (active and existing)
        """
        if not tool_ids:
            return []

        result = await db.execute(
            select(ToolModel.id)
            .where(ToolModel.id.in_(tool_ids))
            .where(ToolModel.is_active)
        )
        return [row[0] for row in result.all()]


# Global service instance
agent_service = AgentService()


__all__ = ["AgentService", "agent_service"]
>>>>>>> origin/main
