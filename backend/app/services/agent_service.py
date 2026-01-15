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
