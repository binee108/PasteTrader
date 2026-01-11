"""API routing configuration.

This package contains all API routes organized by version.
"""

from fastapi import APIRouter

from app.api.v1 import router as v1_router

router = APIRouter()

# Include versioned routers
router.include_router(v1_router, tags=["v1"])
