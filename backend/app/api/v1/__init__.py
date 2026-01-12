"""API v1 routing configuration.

This module defines all v1 API routes.
"""

from fastapi import APIRouter

from app.api.v1 import executions, workflows

router = APIRouter()

# Domain routers
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
router.include_router(executions.router, prefix="/executions", tags=["Executions"])

# TODO: Add future domain routers (tools, agents) when implemented


@router.get("/status", tags=["Status"])
async def api_status() -> dict[str, str]:
    """API v1 status check."""
    return {"status": "ok", "version": "v1"}
