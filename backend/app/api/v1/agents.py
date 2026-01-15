"""Agent API Router.

TAG: [SPEC-009] [API] [AGENT]
REQ: REQ-001 - Agent CRUD Endpoints
REQ: REQ-002 - Agent Tool Association Endpoints
REQ: REQ-003 - Agent Filtering and Pagination

This module provides REST API endpoints for managing agents.
Supports CRUD operations, tool associations, and filtering.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import (  # noqa: TC001 - Needed at runtime for FastAPI DI
    DBSession,
    Pagination,
)
from app.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentToolsUpdate,
    AgentUpdate,
)
from app.schemas.base import PaginatedResponse
from app.services.agent_service import AgentService

router = APIRouter()

# Temporary owner_id until auth is implemented
TEMP_OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")


# =============================================================================
# Agent Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=PaginatedResponse[AgentResponse],
    summary="List agents",
    description="Retrieve a paginated list of agents with optional filtering.",
)
async def list_agents(
    db: DBSession,
    pagination: Pagination,
    model_provider: Annotated[
        str | None,
        Query(description="Filter by model provider"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status"),
    ] = None,
    is_public: Annotated[
        bool | None,
        Query(description="Filter by public status"),
    ] = None,
) -> PaginatedResponse[AgentResponse]:
    """List agents with pagination and optional filtering.

    Args:
        db: Database session.
        pagination: Pagination parameters (skip, limit).
        model_provider: Optional filter by model provider.
        is_active: Optional filter by active status.
        is_public: Optional filter by public status.

    Returns:
        Paginated list of agents.
    """
    try:
        agent_service = AgentService(db)
        agents = await agent_service.list(
            owner_id=TEMP_OWNER_ID,
            skip=pagination.skip,
            limit=pagination.limit,
            model_provider=model_provider,
            is_active=is_active,
            is_public=is_public,
        )
        total = await agent_service.count(
            owner_id=TEMP_OWNER_ID,
            model_provider=model_provider,
            is_active=is_active,
            is_public=is_public,
        )

        # Convert models to response schemas
        agent_responses = [
            AgentResponse(
                id=agent.id,
                name=agent.name,
                model_provider=agent.model_provider,
                model_name=agent.model_name,
                is_active=agent.is_active,
                is_public=agent.is_public,
                created_at=agent.created_at.isoformat(),
            )
            for agent in agents
        ]

        return PaginatedResponse.create(
            items=agent_responses,
            total=total,
            page=(pagination.skip // pagination.limit) + 1
            if pagination.limit > 0
            else 1,
            size=pagination.limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {e!s}",
        ) from e


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent",
    description="Create a new agent with the provided configuration.",
)
async def create_agent(
    db: DBSession,
    agent_in: AgentCreate,
) -> AgentResponse:
    """Create a new agent.

    Args:
        db: Database session.
        agent_in: Agent creation data.

    Returns:
        Created agent.

    Raises:
        HTTPException: 400 if validation fails.
    """
    try:
        agent_service = AgentService(db)
        agent = await agent_service.create(owner_id=TEMP_OWNER_ID, data=agent_in)
        return AgentResponse.model_validate(agent)
    except AgentServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent",
    description="Retrieve an agent by its ID.",
)
async def get_agent(
    db: DBSession,
    agent_id: UUID,
) -> AgentResponse:
    """Get an agent by ID.

    Args:
        db: Database session.
        agent_id: UUID of the agent.

    Returns:
        Agent details.

    Raises:
        HTTPException: 404 if agent not found.
    """
    try:
        agent_service = AgentService(db)
        agent = await agent_service.get(agent_id)
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )
        return AgentResponse.model_validate(agent)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {e!s}",
        ) from e


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Update an existing agent.",
)
async def update_agent(
    db: DBSession,
    agent_id: UUID,
    agent_in: AgentUpdate,
) -> AgentResponse:
    """Update an existing agent.

    Args:
        db: Database session.
        agent_id: UUID of the agent.
        agent_in: Agent update data.

    Returns:
        Updated agent.

    Raises:
        HTTPException: 404 if agent not found.
    """
    try:
        agent_service = AgentService(db)
        agent = await agent_service.update(agent_id, data=agent_in)
        return AgentResponse.model_validate(agent)
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {e!s}",
        ) from e


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent",
    description="Soft delete an agent. The agent can be restored later.",
)
async def delete_agent(
    db: DBSession,
    agent_id: UUID,
) -> None:
    """Soft delete an agent.

    Args:
        db: Database session.
        agent_id: UUID of the agent.

    Raises:
        HTTPException: 404 if agent not found.
    """
    try:
        agent_service = AgentService(db)
        await agent_service.delete(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {e!s}",
        ) from e


# =============================================================================
# Agent Tool Association Endpoints
# =============================================================================


@router.post(
    "/{agent_id}/tools",
    response_model=AgentResponse,
    summary="Add tool to agent",
    description="Associate a tool with an agent.",
)
async def add_tool_to_agent(
    db: DBSession,
    agent_id: UUID,
    tool_data: AgentToolAdd,
) -> AgentResponse:
    """Add a tool to an agent.

    Args:
        db: Database session.
        agent_id: UUID of the agent.
        tool_data: Tool association data.

    Returns:
        Updated agent.

    Raises:
        HTTPException: 404 if agent not found.
        HTTPException: 409 if tool already associated.
    """
    try:
        agent_service = AgentService(db)
        agent = await agent_service.add_tool(agent_id, tool_data.tool_id)
        return AgentResponse.model_validate(agent)
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ToolAlreadyAssociatedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add tool to agent: {e!s}",
        ) from e


@router.delete(
    "/{agent_id}/tools/{tool_id}",
    response_model=AgentResponse,
    summary="Remove tool from agent",
    description="Remove a tool association from an agent.",
)
async def remove_tool_from_agent(
    db: DBSession,
    agent_id: UUID,
    tool_id: UUID,
) -> AgentResponse:
    """Remove a tool from an agent.

    Args:
        db: Database session.
        agent_id: UUID of the agent.
        tool_id: UUID of the tool to remove.

    Returns:
        Updated agent.

    Raises:
        HTTPException: 404 if agent not found.
    """
    try:
        agent_service = AgentService(db)
        agent = await agent_service.remove_tool(agent_id, tool_id)
        return AgentResponse.model_validate(agent)
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove tool from agent: {e!s}",
        ) from e


__all__ = [
    "router",
]
