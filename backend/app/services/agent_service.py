"""Agent service layer.

TAG: [SPEC-009] [API] [SERVICE] [AGENT]
REQ: REQ-001 - AgentService CRUD Operations
REQ: REQ-002 - Agent Tool Association
REQ: REQ-003 - Agent Filtering and Search

This module provides service layer abstractions for agent management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.orm import attributes

from app.models.agent import Agent

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Exceptions
# =============================================================================


class AgentServiceError(Exception):
    """Base exception for agent service errors."""


class AgentNotFoundError(AgentServiceError):
    """Raised when an agent is not found."""


class ToolNotFoundError(AgentServiceError):
    """Raised when a tool is not found."""


class ToolAlreadyAssociatedError(AgentServiceError):
    """Raised when a tool is already associated with an agent."""


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

    async def get(self, agent_id: UUID, include_deleted: bool = False) -> Agent | None:
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
        is_active: bool | None = None,
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
        is_active: bool | None = None,
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
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        agent.soft_delete()
        await self.db.flush()
        await self.db.refresh(agent)
        return agent

    async def add_tool(self, agent_id: UUID, tool_id: UUID) -> Agent:
        """Add a tool to an agent.

        Args:
            agent_id: UUID of the agent.
            tool_id: UUID of the tool to add.

        Returns:
            Updated Agent instance.

        Raises:
            AgentNotFoundError: If agent not found.
            ToolAlreadyAssociatedError: If tool already associated.
        """
        agent = await self.get(agent_id)
        if agent is None:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        tool_id_str = str(tool_id)
        if tool_id_str in agent.tools:
            raise ToolAlreadyAssociatedError(
                f"Tool {tool_id} already associated with agent {agent_id}"
            )

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


__all__ = [
    "AgentNotFoundError",
    "AgentService",
    "AgentServiceError",
    "ToolAlreadyAssociatedError",
    "ToolNotFoundError",
]
