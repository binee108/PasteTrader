"""API v1 routing configuration.

This module defines all v1 API routes.
"""

from fastapi import APIRouter

from app.api.v1 import agents, executions, schedules, tools, validation, workflows

router = APIRouter()

# Domain routers
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
router.include_router(executions.router, prefix="/executions", tags=["Executions"])
router.include_router(tools.router, prefix="/tools", tags=["Tools"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(schedules.router, tags=["Schedules"])
router.include_router(validation.router, tags=["Validation"])


@router.get("/status", tags=["Status"])
async def api_status() -> dict[str, str]:
    """API v1 status check."""
    return {"status": "ok", "version": "v1"}
