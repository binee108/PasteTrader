"""Validation API Router.

TAG: [SPEC-010] [API] [VALIDATION] [DAG]
REQ: REQ-010-E - API Endpoint

This module provides REST API endpoints for workflow DAG validation.
Supports real-time validation, topology analysis, and cycle checking.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession
from app.schemas.validation import (
    CycleCheckResult,
    EdgeValidationRequest,
    TopologyResult,
    ValidationOptions,
    ValidationResult,
)
from app.services.workflow import DAGValidator

router = APIRouter(prefix="/validation", tags=["validation"])


# =============================================================================
# Validation Endpoints
# =============================================================================


@router.post(
    "/workflows/{workflow_id}",
    response_model=ValidationResult,
    summary="Validate Workflow DAG",
    description="Perform comprehensive DAG validation for a workflow.",
    responses={
        200: {"description": "Validation completed successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"},
    },
)
async def validate_workflow(
    workflow_id: UUID,
    options: ValidationOptions | None = None,
    db: DBSession = None,
) -> ValidationResult:
    """Validate entire workflow graph.

    TAG: [SPEC-010] [API] [VALIDATION]

    Performs structural, connectivity, and optionally schema validation.
    Returns detailed validation results with errors, warnings, and topology.

    Args:
        workflow_id: UUID of the workflow to validate.
        options: Optional validation settings (level, timeout, limits).
        db: Database session (injected).

    Returns:
        ValidationResult with comprehensive validation information.

    Raises:
        HTTPException: If workflow is not found (404).
    """
    validator = DAGValidator(db)

    try:
        result = await validator.validate_workflow(
            workflow_id=workflow_id,
            options=options or ValidationOptions(),
        )
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post(
    "/workflows/{workflow_id}/check-edge",
    response_model=CycleCheckResult,
    summary="Check Edge Addition",
    description="Quick check if adding an edge would create a cycle.",
    responses={
        200: {"description": "Edge check completed"},
        404: {"description": "Workflow or node not found"},
        500: {"description": "Internal server error"},
    },
)
async def check_edge(
    workflow_id: UUID,
    source_node_id: Annotated[
        UUID,
        Query(description="Source node ID for the proposed edge"),
    ],
    target_node_id: Annotated[
        UUID,
        Query(description="Target node ID for the proposed edge"),
    ],
    source_handle: Annotated[
        str | None,
        Query(description="Optional source handle"),
    ] = None,
    target_handle: Annotated[
        str | None,
        Query(description="Optional target handle"),
    ] = None,
    db: DBSession = None,
) -> CycleCheckResult:
    """Quick cycle check for proposed edge.

    TAG: [SPEC-010] [API] [VALIDATION]

    Lightweight validation for real-time UI feedback.
    Checks if adding the specified edge would create a cycle.

    Args:
        workflow_id: UUID of the workflow.
        source_node_id: Source node ID.
        target_node_id: Target node ID.
        source_handle: Optional source handle.
        target_handle: Optional target handle.
        db: Database session (injected).

    Returns:
        CycleCheckResult indicating if cycle would be created.
    """
    validator = DAGValidator(db)

    try:
        result = await validator.validate_edge_addition(
            workflow_id=workflow_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            source_handle=source_handle,
            target_handle=target_handle,
        )
        return CycleCheckResult(
            has_cycle=not result.is_valid,
            cycle_path=result.errors[0].details.get("cycle_path") if result.errors else None,
            cycle_description=result.errors[0].message if result.errors else None,
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get(
    "/workflows/{workflow_id}/topology",
    response_model=TopologyResult,
    summary="Get Workflow Topology",
    description="Generate topological sort and execution order.",
    responses={
        200: {"description": "Topology generated successfully"},
        400: {"description": "Workflow contains a cycle"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_topology(
    workflow_id: UUID,
    db: DBSession = None,
) -> TopologyResult:
    """Get execution topology for workflow.

    TAG: [SPEC-010] [API] [VALIDATION]

    Returns execution levels for parallel processing.
    Includes critical path analysis and maximum parallelism.

    Args:
        workflow_id: UUID of the workflow.
        db: Database session (injected).

    Returns:
        TopologyResult with execution order and parallelization info.

    Raises:
        HTTPException: If workflow has a cycle (400) or not found (404).
    """
    validator = DAGValidator(db)

    try:
        result = await validator.get_topology(workflow_id)
        return result
    except Exception as e:
        error_msg = str(e).lower()
        if "cycle" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow contains a cycle and cannot have topology",
            ) from e
        if "not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post(
    "/workflows/{workflow_id}/cycle-check",
    response_model=CycleCheckResult,
    summary="Check for Cycles",
    description="Check if workflow contains any cycles.",
    responses={
        200: {"description": "Cycle check completed"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"},
    },
)
async def check_cycle(
    workflow_id: UUID,
    db: DBSession = None,
) -> CycleCheckResult:
    """Check workflow for cycles.

    TAG: [SPEC-010] [API] [VALIDATION]

    Lightweight cycle detection without full validation.
    Useful for quick health checks.

    Args:
        workflow_id: UUID of the workflow.
        db: Database session (injected).

    Returns:
        CycleCheckResult indicating if cycle exists.
    """
    validator = DAGValidator(db)

    try:
        result = await validator.check_cycle(workflow_id)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


__all__ = ["router"]
