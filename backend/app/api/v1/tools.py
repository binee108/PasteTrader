"""Tool API Router.

TAG: [SPEC-009] [API] [TOOL]
REQ: REQ-001 - Tool CRUD Endpoints
REQ: REQ-002 - Tool Test Execution Endpoint
REQ: REQ-003 - Tool Filtering and Pagination

This module provides REST API endpoints for managing tools.
Supports CRUD operations, filtering, and test execution.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession, Pagination
from app.schemas.base import PaginatedResponse
from app.schemas.tool import (
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)
from app.services.tool_service import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolService,
    ToolServiceError,
)

router = APIRouter()

# Temporary owner_id until auth is implemented
TEMP_OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")


# =============================================================================
# Tool Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=PaginatedResponse[ToolListResponse],
    summary="List tools",
    description="Retrieve a paginated list of tools with optional filtering.",
)
async def list_tools(
    db: DBSession,
    pagination: Pagination,
    tool_type: Annotated[
        str | None,
        Query(description="Filter by tool type"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status"),
    ] = None,
    is_public: Annotated[
        bool | None,
        Query(description="Filter by public status"),
    ] = None,
) -> PaginatedResponse[ToolListResponse]:
    """List tools with pagination and optional filtering.

    Args:
        db: Database session.
        pagination: Pagination parameters (skip, limit).
        tool_type: Optional filter by tool type.
        is_active: Optional filter by active status.
        is_public: Optional filter by public status.

    Returns:
        Paginated list of tools.
    """
    try:
        tool_service = ToolService(db)
        tools = await tool_service.list(
            owner_id=TEMP_OWNER_ID,
            skip=pagination.skip,
            limit=pagination.limit,
            tool_type=tool_type,
            is_active=is_active,
            is_public=is_public,
        )
        total = await tool_service.count(
            owner_id=TEMP_OWNER_ID,
            tool_type=tool_type,
            is_active=is_active,
            is_public=is_public,
        )

        # Convert models to response schemas
        tool_responses = [
            ToolListResponse(
                id=tool.id,
                name=tool.name,
                tool_type=tool.tool_type,
                is_active=tool.is_active,
                is_public=tool.is_public,
                created_at=tool.created_at.isoformat(),
            )
            for tool in tools
        ]

        return PaginatedResponse.create(
            items=tool_responses,
            total=total,
            page=(pagination.skip // pagination.limit) + 1
            if pagination.limit > 0
            else 1,
            size=pagination.limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {e!s}",
        ) from e


@router.post(
    "/",
    response_model=ToolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tool",
    description="Create a new tool with the provided configuration.",
)
async def create_tool(
    db: DBSession,
    tool_in: ToolCreate,
) -> ToolResponse:
    """Create a new tool.

    Args:
        db: Database session.
        tool_in: Tool creation data.

    Returns:
        Created tool.

    Raises:
        HTTPException: 400 if validation fails.
    """
    try:
        tool_service = ToolService(db)
        tool = await tool_service.create(owner_id=TEMP_OWNER_ID, data=tool_in)
        return ToolResponse.model_validate(tool)
    except ToolServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{tool_id}",
    response_model=ToolResponse,
    summary="Get tool",
    description="Retrieve a tool by its ID.",
)
async def get_tool(
    db: DBSession,
    tool_id: UUID,
) -> ToolResponse:
    """Get a tool by ID.

    Args:
        db: Database session.
        tool_id: UUID of the tool.

    Returns:
        Tool details.

    Raises:
        HTTPException: 404 if tool not found.
    """
    try:
        tool_service = ToolService(db)
        tool = await tool_service.get(tool_id)
        if tool is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool {tool_id} not found",
            )
        return ToolResponse.model_validate(tool)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool: {e!s}",
        ) from e


@router.put(
    "/{tool_id}",
    response_model=ToolResponse,
    summary="Update tool",
    description="Update an existing tool.",
)
async def update_tool(
    db: DBSession,
    tool_id: UUID,
    tool_in: ToolUpdate,
) -> ToolResponse:
    """Update an existing tool.

    Args:
        db: Database session.
        tool_id: UUID of the tool.
        tool_in: Tool update data.

    Returns:
        Updated tool.

    Raises:
        HTTPException: 404 if tool not found.
    """
    try:
        tool_service = ToolService(db)
        tool = await tool_service.update(tool_id, data=tool_in)
        return ToolResponse.model_validate(tool)
    except ToolNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {e!s}",
        ) from e


@router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tool",
    description="Soft delete a tool. The tool can be restored later.",
)
async def delete_tool(
    db: DBSession,
    tool_id: UUID,
) -> None:
    """Soft delete a tool.

    Args:
        db: Database session.
        tool_id: UUID of the tool.

    Raises:
        HTTPException: 404 if tool not found.
    """
    try:
        tool_service = ToolService(db)
        await tool_service.delete(tool_id)
    except ToolNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {e!s}",
        ) from e


@router.post(
    "/{tool_id}/test",
    response_model=ToolTestResponse,
    summary="Test tool execution",
    description="Test execute a tool with sample input data.",
)
async def test_tool(
    db: DBSession,
    tool_id: UUID,
    test_request: ToolTestRequest,
) -> ToolTestResponse:
    """Test execute a tool.

    Args:
        db: Database session.
        tool_id: UUID of the tool.
        test_request: Test input data.

    Returns:
        Tool test execution results.

    Raises:
        HTTPException: 404 if tool not found.
        HTTPException: 400 if execution fails.
    """
    try:
        tool_service = ToolService(db)
        result = await tool_service.test_execute(tool_id, test_request.input_data)
        return ToolTestResponse(**result)
    except ToolNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ToolExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test tool: {e!s}",
        ) from e


__all__ = [
    "router",
]
