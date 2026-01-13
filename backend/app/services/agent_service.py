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
