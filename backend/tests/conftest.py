"""pytest configuration and fixtures.

This module provides common fixtures for all tests.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_workflow_data() -> dict:
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "version": "1.0.0",
    }
