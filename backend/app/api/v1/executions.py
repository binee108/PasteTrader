"""Execution API Router.

TAG: [SPEC-007] [API] [EXECUTION]
REQ: REQ-001 - WorkflowExecution Endpoints
REQ: REQ-002 - NodeExecution Endpoints
REQ: REQ-003 - ExecutionLog Endpoints

This module defines the API endpoints for workflow executions, node executions,
and execution logs.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import (  # noqa: TC001 - Required at runtime for FastAPI
    DBSession,
    Pagination,
)
from app.models.enums import (  # noqa: TC001 - Required at runtime for FastAPI
    ExecutionStatus,
    LogLevel,
)
from app.schemas.base import PaginatedResponse
from app.schemas.execution import (
    ExecutionCancel,
    ExecutionLogPaginatedResponse,
    ExecutionLogResponse,
    ExecutionStatistics,
    NodeExecutionPaginatedResponse,
    NodeExecutionResponse,
    NodeExecutionWithLogs,
    WorkflowExecutionCreate,
    WorkflowExecutionDetail,
    WorkflowExecutionListResponse,
    WorkflowExecutionPaginatedResponse,
    WorkflowExecutionResponse,
    WorkflowExecutionStatistics,
)
from app.services.execution_service import (
    ExecutionLogService,
    NodeExecutionService,
    WorkflowExecutionService,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


# =============================================================================
# Path Parameter Dependencies
# =============================================================================


ExecutionIdPath = Annotated[
    UUID,
    Path(
        ...,
        description="Unique identifier of the workflow execution",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    ),
]

NodeExecutionIdPath = Annotated[
    UUID,
    Path(
        ...,
        description="Unique identifier of the node execution",
        examples=["660e8400-e29b-41d4-a716-446655440000"],
    ),
]

WorkflowIdPath = Annotated[
    UUID,
    Path(
        ...,
        description="Unique identifier of the workflow",
        examples=["770e8400-e29b-41d4-a716-446655440000"],
    ),
]


# =============================================================================
# Query Parameter Dependencies
# =============================================================================


def get_execution_filters(
    workflow_id: Annotated[
        UUID | None,
        Query(description="Filter by workflow ID"),
    ] = None,
    status: Annotated[
        ExecutionStatus | None,
        Query(description="Filter by execution status"),
    ] = None,
) -> dict[str, Any]:
    """Get execution list filter parameters.

    Args:
        workflow_id: Filter by workflow ID.
        status: Filter by execution status.

    Returns:
        Dictionary of filter parameters.
    """
    filters: dict[str, Any] = {}
    if workflow_id is not None:
        filters["workflow_id"] = workflow_id
    if status is not None:
        filters["status"] = status
    return filters


ExecutionFilters = Annotated[dict[str, Any], Depends(get_execution_filters)]


def get_log_filters(
    level: Annotated[
        LogLevel | None,
        Query(description="Filter by log level"),
    ] = None,
) -> dict[str, Any]:
    """Get log list filter parameters.

    Args:
        level: Filter by log level.

    Returns:
        Dictionary of filter parameters.
    """
    filters: dict[str, Any] = {}
    if level is not None:
        filters["level"] = level
    return filters


LogFilters = Annotated[dict[str, Any], Depends(get_log_filters)]


# =============================================================================
# WorkflowExecution Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=WorkflowExecutionPaginatedResponse,
    summary="List workflow executions",
    description="List workflow executions with optional filtering.",
)
async def list_executions(
    db: DBSession,
    pagination: Pagination,
    filters: ExecutionFilters,
) -> WorkflowExecutionPaginatedResponse:
    """List all workflow executions.

    Args:
        db: Database session.
        pagination: Pagination parameters (skip, limit).
        filters: Filter parameters (workflow_id, status).

    Returns:
        Paginated list of workflow executions.
    """
    workflow_id: UUID | None = filters.get("workflow_id")
    status_filter: ExecutionStatus | None = filters.get("status")

    if workflow_id is None:
        # If no workflow_id filter, return empty result
        # (full list across all workflows not implemented yet)
        return PaginatedResponse.create(
            items=[],
            total=0,
            page=(pagination.skip // pagination.limit) + 1,
            size=pagination.limit,
        )

    items = await WorkflowExecutionService.list(
        db,
        workflow_id=workflow_id,
        skip=pagination.skip,
        limit=pagination.limit,
        status=status_filter,
    )
    total = await WorkflowExecutionService.count(
        db,
        workflow_id=workflow_id,
        status=status_filter,
    )

    # Convert models to response schemas
    items_response = [
        WorkflowExecutionListResponse.model_validate(item) for item in items
    ]

    return PaginatedResponse.create(
        items=items_response,
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
    )


@router.post(
    "/",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start workflow execution",
    description="Start a new workflow execution with the provided configuration.",
)
async def create_execution(
    db: DBSession,
    execution_data: WorkflowExecutionCreate,
) -> WorkflowExecutionResponse:
    """Start a new workflow execution.

    Args:
        db: Database session.
        execution_data: Execution configuration data.

    Returns:
        Created workflow execution record.

    Raises:
        HTTPException: 404 if workflow not found.
    """
    # Validate workflow exists
    workflow_service = WorkflowService(db)
    workflow = await workflow_service.get(execution_data.workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {execution_data.workflow_id} not found",
        )

    # Create execution
    execution = await WorkflowExecutionService.create(
        db,
        workflow_id=execution_data.workflow_id,
        data=execution_data,
    )
    await db.commit()

    return WorkflowExecutionResponse.model_validate(execution)


@router.get(
    "/{execution_id}",
    response_model=WorkflowExecutionResponse,
    summary="Get execution by ID",
    description="Retrieve a specific workflow execution by its unique identifier.",
)
async def get_execution(
    db: DBSession,
    execution_id: ExecutionIdPath,
) -> WorkflowExecutionResponse:
    """Get a workflow execution by ID.

    Args:
        db: Database session.
        execution_id: UUID of the workflow execution.

    Returns:
        Workflow execution record.

    Raises:
        HTTPException: 404 if execution not found.
    """
    execution = await WorkflowExecutionService.get(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )
    return WorkflowExecutionResponse.model_validate(execution)


@router.get(
    "/{execution_id}/detail",
    response_model=WorkflowExecutionDetail,
    summary="Get execution with details",
    description="Retrieve a workflow execution with all node executions and logs.",
)
async def get_execution_detail(
    db: DBSession,
    execution_id: ExecutionIdPath,
) -> WorkflowExecutionDetail:
    """Get detailed workflow execution including node executions and logs.

    Args:
        db: Database session.
        execution_id: UUID of the workflow execution.

    Returns:
        Detailed workflow execution with nested node executions and logs.

    Raises:
        HTTPException: 404 if execution not found.
    """
    execution = await WorkflowExecutionService.get_with_nodes(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )

    # Get workflow-level logs
    logs = await ExecutionLogService.list_by_execution(
        db,
        workflow_execution_id=execution_id,
        skip=0,
        limit=1000,
    )

    # Build node executions with their logs
    node_executions_with_logs = []
    for node in execution.node_executions:
        node_logs = await ExecutionLogService.list_by_node(
            db,
            node_execution_id=node.id,
        )
        node_executions_with_logs.append(
            NodeExecutionWithLogs(
                **NodeExecutionResponse.model_validate(node).model_dump(),
                logs=[ExecutionLogResponse.model_validate(log) for log in node_logs],
            )
        )

    return WorkflowExecutionDetail(
        **WorkflowExecutionResponse.model_validate(execution).model_dump(),
        node_executions=node_executions_with_logs,
        logs=[ExecutionLogResponse.model_validate(log) for log in logs],
    )


@router.post(
    "/{execution_id}/cancel",
    response_model=WorkflowExecutionResponse,
    summary="Cancel execution",
    description="Cancel a running workflow execution.",
)
async def cancel_execution(
    db: DBSession,
    execution_id: ExecutionIdPath,
    _cancel_data: ExecutionCancel | None = None,
) -> WorkflowExecutionResponse:
    """Cancel a running workflow execution.

    Args:
        db: Database session.
        execution_id: UUID of the workflow execution.
        _cancel_data: Optional cancellation reason (reserved for future use).

    Returns:
        Updated workflow execution record.

    Raises:
        HTTPException: 404 if execution not found.
        HTTPException: 400 if execution is not running.
    """
    try:
        execution = await WorkflowExecutionService.cancel(db, execution_id)
        await db.commit()
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution with ID {execution_id} not found",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return WorkflowExecutionResponse.model_validate(execution)


@router.get(
    "/{execution_id}/statistics",
    response_model=ExecutionStatistics,
    summary="Get execution statistics",
    description="Get statistics for a specific workflow execution.",
)
async def get_execution_statistics(
    db: DBSession,
    execution_id: ExecutionIdPath,
) -> ExecutionStatistics:
    """Get statistics for a workflow execution.

    Args:
        db: Database session.
        execution_id: UUID of the workflow execution.

    Returns:
        Execution statistics.

    Raises:
        HTTPException: 404 if execution not found.
    """
    execution = await WorkflowExecutionService.get(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )

    return ExecutionStatistics.model_validate(
        await WorkflowExecutionService.get_statistics(db, execution.workflow_id)
    )


# =============================================================================
# NodeExecution Endpoints (nested under execution)
# =============================================================================


@router.get(
    "/{execution_id}/nodes",
    response_model=NodeExecutionPaginatedResponse,
    summary="List node executions",
    description="List node executions for a workflow execution.",
)
async def list_node_executions(
    db: DBSession,
    execution_id: ExecutionIdPath,
    pagination: Pagination,
) -> NodeExecutionPaginatedResponse:
    """List node executions for a workflow execution.

    Args:
        db: Database session.
        execution_id: UUID of the parent workflow execution.
        pagination: Pagination parameters.

    Returns:
        Paginated list of node executions.

    Raises:
        HTTPException: 404 if workflow execution not found.
    """
    # Verify execution exists
    execution = await WorkflowExecutionService.get(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )

    items = await NodeExecutionService.list_by_execution(db, execution_id)

    # Apply pagination in-memory (service returns all ordered by execution_order)
    total = len(items)
    start = pagination.skip
    end = start + pagination.limit
    paginated_items = items[start:end]

    items_response = [
        NodeExecutionResponse.model_validate(item) for item in paginated_items
    ]

    return PaginatedResponse.create(
        items=items_response,
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
    )


@router.get(
    "/{execution_id}/nodes/{node_execution_id}",
    response_model=NodeExecutionWithLogs,
    summary="Get node execution detail",
    description="Retrieve a specific node execution with its logs.",
)
async def get_node_execution(
    db: DBSession,
    execution_id: ExecutionIdPath,
    node_execution_id: NodeExecutionIdPath,
) -> NodeExecutionWithLogs:
    """Get a node execution by ID with its logs.

    Args:
        db: Database session.
        execution_id: UUID of the parent workflow execution.
        node_execution_id: UUID of the node execution.

    Returns:
        Node execution with embedded logs.

    Raises:
        HTTPException: 404 if node execution not found.
    """
    # Verify parent execution exists
    execution = await WorkflowExecutionService.get(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )

    node_execution = await NodeExecutionService.get(db, node_execution_id)
    if node_execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node execution with ID {node_execution_id} not found",
        )

    # Get logs for this node execution
    logs = await ExecutionLogService.list_by_node(
        db,
        node_execution_id=node_execution_id,
    )

    return NodeExecutionWithLogs(
        **NodeExecutionResponse.model_validate(node_execution).model_dump(),
        logs=[ExecutionLogResponse.model_validate(log) for log in logs],
    )


# =============================================================================
# ExecutionLog Endpoints
# =============================================================================


@router.get(
    "/{execution_id}/logs",
    response_model=ExecutionLogPaginatedResponse,
    summary="List execution logs",
    description="Retrieve a paginated list of logs for a workflow execution.",
)
async def list_execution_logs(
    db: DBSession,
    execution_id: ExecutionIdPath,
    pagination: Pagination,
    filters: LogFilters,
) -> ExecutionLogPaginatedResponse:
    """List logs for a workflow execution.

    Args:
        db: Database session.
        execution_id: UUID of the workflow execution.
        pagination: Pagination parameters.
        filters: Log filter parameters (level).

    Returns:
        Paginated list of execution logs.

    Raises:
        HTTPException: 404 if workflow execution not found.
    """
    # Verify execution exists
    execution = await WorkflowExecutionService.get(db, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID {execution_id} not found",
        )

    level: LogLevel | None = filters.get("level")

    items = await ExecutionLogService.list_by_execution(
        db,
        workflow_execution_id=execution_id,
        level=level,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    total = await ExecutionLogService.count(
        db,
        workflow_execution_id=execution_id,
        level=level,
    )

    items_response = [ExecutionLogResponse.model_validate(item) for item in items]

    return PaginatedResponse.create(
        items=items_response,
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
    )


@router.get(
    "/{execution_id}/nodes/{node_execution_id}/logs",
    response_model=ExecutionLogPaginatedResponse,
    summary="List node execution logs",
    description="Retrieve logs for a specific node execution.",
)
async def list_node_execution_logs(
    db: DBSession,
    execution_id: ExecutionIdPath,  # noqa: ARG001 - Path parameter for consistency with API spec
    node_execution_id: NodeExecutionIdPath,
    pagination: Pagination,
    filters: LogFilters,
) -> ExecutionLogPaginatedResponse:
    """List logs for a specific node execution.

    Args:
        db: Database session.
        execution_id: UUID of the parent workflow execution.
        node_execution_id: UUID of the node execution.
        pagination: Pagination parameters.
        filters: Log filter parameters (level).

    Returns:
        Paginated list of logs for the node execution.

    Raises:
        HTTPException: 404 if node execution not found.
    """
    # Verify node execution exists
    node_execution = await NodeExecutionService.get(db, node_execution_id)
    if node_execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node execution with ID {node_execution_id} not found",
        )

    level: LogLevel | None = filters.get("level")

    items = await ExecutionLogService.list_by_node(
        db,
        node_execution_id=node_execution_id,
        level=level,
    )

    # Apply pagination in-memory (service returns all ordered by timestamp)
    total = len(items)
    start = pagination.skip
    end = start + pagination.limit
    paginated_items = items[start:end]

    items_response = [
        ExecutionLogResponse.model_validate(item) for item in paginated_items
    ]

    return PaginatedResponse.create(
        items=items_response,
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
    )


# =============================================================================
# Workflow-specific Execution Endpoints
# =============================================================================


@router.get(
    "/workflows/{workflow_id}/executions",
    response_model=WorkflowExecutionPaginatedResponse,
    summary="List executions for workflow",
    description="Retrieve a paginated list of executions for a specific workflow.",
)
async def list_workflow_executions(
    db: DBSession,
    workflow_id: WorkflowIdPath,
    pagination: Pagination,
    status_filter: Annotated[
        ExecutionStatus | None,
        Query(alias="status", description="Filter by execution status"),
    ] = None,
) -> WorkflowExecutionPaginatedResponse:
    """List executions for a specific workflow.

    Args:
        db: Database session.
        workflow_id: UUID of the workflow.
        pagination: Pagination parameters.
        status_filter: Optional status filter.

    Returns:
        Paginated list of workflow executions.

    Raises:
        HTTPException: 404 if workflow not found.
    """
    items = await WorkflowExecutionService.list(
        db,
        workflow_id=workflow_id,
        skip=pagination.skip,
        limit=pagination.limit,
        status=status_filter,
    )
    total = await WorkflowExecutionService.count(
        db,
        workflow_id=workflow_id,
        status=status_filter,
    )

    items_response = [
        WorkflowExecutionListResponse.model_validate(item) for item in items
    ]

    return PaginatedResponse.create(
        items=items_response,
        total=total,
        page=(pagination.skip // pagination.limit) + 1,
        size=pagination.limit,
    )


@router.get(
    "/workflows/{workflow_id}/statistics",
    response_model=WorkflowExecutionStatistics,
    summary="Get workflow execution statistics",
    description="Get aggregated execution statistics for a specific workflow.",
)
async def get_workflow_statistics(
    db: DBSession,
    workflow_id: WorkflowIdPath,
) -> WorkflowExecutionStatistics:
    """Get execution statistics for a workflow.

    Args:
        db: Database session.
        workflow_id: UUID of the workflow.

    Returns:
        Aggregated execution statistics for the workflow.

    Raises:
        HTTPException: 404 if workflow not found.
    """
    # Get statistics - this will return stats even if no executions exist
    stats = await WorkflowExecutionService.get_statistics(db, workflow_id)

    # For workflow_name, we need to fetch from workflow table
    # For now, use a placeholder since we don't have workflow service imported
    from sqlalchemy import select

    from app.models.workflow import Workflow

    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with ID {workflow_id} not found",
        )

    return WorkflowExecutionStatistics(
        workflow_id=workflow_id,
        workflow_name=workflow.name,
        last_execution_at=workflow.updated_at,  # Using updated_at as proxy
        **stats.model_dump(),
    )


__all__ = ["router"]
