"""FastAPI application entry point.

This module defines the main FastAPI application with CORS middleware,
lifespan management, and API routing configuration.

Logging:
    Initializes structured logging on application startup.
    All application events are logged with appropriate context.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

# Initialize logging system
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE,
    service_name=settings.PROJECT_NAME,
    enable_json=settings.LOG_JSON_FORMAT,
)

# Get application logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ARG001 - Required by FastAPI lifespan interface
    """Application lifespan context manager.

    Handles startup and shutdown events for the application.
    Initialize database connections, caches, and schedulers on startup.
    Clean up resources on shutdown.

    Logging:
        Logs application startup and shutdown events with configuration details.
    """
    # Startup
    logger.info(
        f"Starting {settings.PROJECT_NAME}",
        extra={
            "context": {
                "action": "application_startup",
                "version": "0.1.0",
                "debug": settings.DEBUG,
                "log_level": settings.LOG_LEVEL,
            }
        },
    )

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize APScheduler

    logger.info(
        "Application startup completed",
        extra={"context": {"action": "application_startup", "status": "success"}},
    )

    yield

    # Shutdown
    logger.info(
        f"Shutting down {settings.PROJECT_NAME}",
        extra={"context": {"action": "application_shutdown"}},
    )

    # TODO: Close database connections
    # TODO: Close Redis connection
    # TODO: Shutdown scheduler

    logger.info(
        "Application shutdown completed",
        extra={"context": {"action": "application_shutdown", "status": "success"}},
    )


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered trading workflow automation platform",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns a simple status indicating the service is running.
    """
    return {"status": "healthy"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns basic API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }
