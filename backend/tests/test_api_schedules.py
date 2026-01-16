"""Integration tests for Schedule API endpoints.

TAG: [SPEC-013] [TESTS] [API] [SCHEDULE]
REQ: REQ-013-013 - Create Schedule (POST /api/v1/schedules)
REQ: REQ-013-014 - List Schedules (GET /api/v1/schedules)
REQ: REQ-013-015 - Get Schedule Details (GET /api/v1/schedules/{id})
REQ: REQ-013-016 - Update Schedule (PUT /api/v1/schedules/{id})
REQ: REQ-013-017 - Delete Schedule (DELETE /api/v1/schedules/{id})
REQ: REQ-013-018 - Pause Schedule (POST /api/v1/schedules/{id}/pause)
REQ: REQ-013-019 - Resume Schedule (POST /api/v1/schedules/{id}/resume)

SECURITY: Updated to require authentication for all endpoints.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

# =============================================================================
# Async Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def workflow_id(async_client_auth: AsyncClient) -> str:
    """Create a workflow and return its ID."""
    response = await async_client_auth.post(
        "/api/v1/workflows/",
        json={
            "name": "Test Workflow for Scheduling",
            "description": "Workflow used for schedule testing",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


@pytest_asyncio.fixture
async def schedule_id(async_client_auth: AsyncClient, workflow_id: str) -> str:
    """Create a schedule and return its ID."""
    response = await async_client_auth.post(
        "/api/v1/schedules",
        json={
            "workflow_id": workflow_id,
            "name": "Test Schedule",
            "description": "A test schedule",
            "trigger_type": "cron",
            "cron_expression": "0 9 * * *",
            "timezone": "UTC",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


# =============================================================================
# POST /api/v1/schedules - Create Schedule
# =============================================================================


class TestCreateSchedule:
    """Test suite for POST /api/v1/schedules endpoint."""

    @pytest.mark.asyncio
    async def test_create_cron_schedule(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test creating a cron schedule.

        TAG: [SPEC-013-TASK-008-TEST-001]
        REQ: REQ-013-013
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Daily Backup",
                "description": "Run backup every day at midnight",
                "trigger_type": "cron",
                "cron_expression": "0 0 * * *",
                "timezone": "UTC",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Daily Backup"
        assert data["schedule_type"] == "cron"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_interval_schedule(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test creating an interval schedule.

        TAG: [SPEC-013-TASK-008-TEST-002]
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Hourly Sync",
                "trigger_type": "interval",
                "interval_hours": 1,
                "timezone": "UTC",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Hourly Sync"
        assert data["schedule_type"] == "interval"

    @pytest.mark.asyncio
    async def test_create_schedule_missing_workflow_id(
        self, async_client_auth: AsyncClient
    ):
        """Test creating schedule without workflow_id fails.

        TAG: [SPEC-013-TASK-008-TEST-003]
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "name": "Test Schedule",
                "trigger_type": "cron",
                "cron_expression": "0 9 * * *",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_schedule_missing_name(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test creating schedule without name fails.

        TAG: [SPEC-013-TASK-008-TEST-004]
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "trigger_type": "cron",
                "cron_expression": "0 9 * * *",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_cron_without_expression_fails(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test creating cron schedule without expression fails.

        TAG: [SPEC-013-TASK-008-TEST-005]
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Invalid Cron",
                "trigger_type": "cron",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_interval_without_value_fails(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test creating interval schedule without interval value fails.

        TAG: [SPEC-013-TASK-008-TEST-006]
        """
        response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Invalid Interval",
                "trigger_type": "interval",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# GET /api/v1/schedules - List Schedules
# =============================================================================


class TestListSchedules:
    """Test suite for GET /api/v1/schedules endpoint."""

    @pytest.mark.asyncio
    async def test_list_schedules_empty(self, async_client_auth: AsyncClient):
        """Test listing schedules when none exist.

        TAG: [SPEC-013-TASK-009-TEST-001]
        REQ: REQ-013-014
        """
        response = await async_client_auth.get("/api/v1/schedules")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_list_schedules_with_results(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test listing schedules returns created schedules.

        TAG: [SPEC-013-TASK-009-TEST-002]
        """
        response = await async_client_auth.get("/api/v1/schedules")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_list_schedules_with_workflow_filter(
        self, async_client_auth: AsyncClient, workflow_id: str, schedule_id: str
    ):
        """Test filtering schedules by workflow_id.

        TAG: [SPEC-013-TASK-009-TEST-003]
        """
        response = await async_client_auth.get(
            f"/api/v1/schedules?workflow_id={workflow_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned schedules should belong to the workflow
        for schedule in data["items"]:
            assert schedule["workflow_id"] == workflow_id

    @pytest.mark.asyncio
    async def test_list_schedules_with_is_active_filter(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test filtering schedules by is_active status.

        TAG: [SPEC-013-TASK-009-TEST-004]
        """
        response = await async_client_auth.get("/api/v1/schedules?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned schedules should be active
        for schedule in data["items"]:
            assert schedule["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_schedules_with_pagination(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test pagination works correctly.

        TAG: [SPEC-013-TASK-009-TEST-005]
        """
        response = await async_client_auth.get("/api/v1/schedules?skip=0&limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10


# =============================================================================
# GET /api/v1/schedules/{id} - Get Schedule Details
# =============================================================================


class TestGetScheduleDetails:
    """Test suite for GET /api/v1/schedules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_schedule_details(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test getting schedule details by ID.

        TAG: [SPEC-013-TASK-010-TEST-001]
        REQ: REQ-013-015
        """
        response = await async_client_auth.get(f"/api/v1/schedules/{schedule_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == schedule_id
        assert "name" in data
        assert "schedule_type" in data
        assert "schedule_config" in data

    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self, async_client_auth: AsyncClient):
        """Test getting non-existent schedule returns 404.

        TAG: [SPEC-013-TASK-010-TEST-002]
        """
        fake_id = uuid4()
        response = await async_client_auth.get(f"/api/v1/schedules/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_schedule_details_includes_statistics(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test schedule details include statistics.

        TAG: [SPEC-013-TASK-010-TEST-003]
        """
        response = await async_client_auth.get(f"/api/v1/schedules/{schedule_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Statistics should be present (even if empty for new schedules)
        assert "statistics" in data or "run_count" in data


# =============================================================================
# PUT /api/v1/schedules/{id} - Update Schedule
# =============================================================================


class TestUpdateSchedule:
    """Test suite for PUT /api/v1/schedules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_schedule_name(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test updating schedule name.

        TAG: [SPEC-013-TASK-011-TEST-001]
        REQ: REQ-013-016
        """
        response = await async_client_auth.put(
            f"/api/v1/schedules/{schedule_id}",
            json={"name": "Updated Schedule Name"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Schedule Name"

    @pytest.mark.asyncio
    async def test_update_schedule_cron_expression(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test updating cron expression.

        TAG: [SPEC-013-TASK-011-TEST-002]
        """
        response = await async_client_auth.put(
            f"/api/v1/schedules/{schedule_id}",
            json={"cron_expression": "0 12 * * *"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["schedule_config"]["cron_expression"] == "0 12 * * *"

    @pytest.mark.asyncio
    async def test_update_schedule_deactivate(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test deactivating a schedule.

        TAG: [SPEC-013-TASK-011-TEST-003]
        """
        response = await async_client_auth.put(
            f"/api/v1/schedules/{schedule_id}",
            json={"is_active": False},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_schedule_not_found(self, async_client_auth: AsyncClient):
        """Test updating non-existent schedule returns 404.

        TAG: [SPEC-013-TASK-011-TEST-004]
        """
        fake_id = uuid4()
        response = await async_client_auth.put(
            f"/api/v1/schedules/{fake_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# DELETE /api/v1/schedules/{id} - Delete Schedule
# =============================================================================


class TestDeleteSchedule:
    """Test suite for DELETE /api/v1/schedules/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_schedule_soft(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test soft deleting a schedule.

        TAG: [SPEC-013-TASK-012-TEST-001]
        REQ: REQ-013-017

        Note: Soft deleted schedules are not found in normal GET requests.
        This is expected behavior - soft delete marks the record as deleted
        and filters it out from normal queries.
        """
        # Create a schedule to delete
        create_response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Schedule to Delete",
                "trigger_type": "cron",
                "cron_expression": "0 9 * * *",
            },
        )
        schedule_id = create_response.json()["id"]

        # Delete the schedule (soft delete)
        response = await async_client_auth.delete(f"/api/v1/schedules/{schedule_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify schedule is soft deleted (not found in normal queries)
        get_response = await async_client_auth.get(f"/api/v1/schedules/{schedule_id}")
        # Soft deleted schedules return 404 as they are filtered out
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_schedule_hard(
        self, async_client_auth: AsyncClient, workflow_id: str
    ):
        """Test hard deleting a schedule (admin only).

        TAG: [SPEC-013-TASK-012-TEST-002]

        Note: This test uses async_client_auth which provides admin privileges.
        Regular users should get 403 Forbidden when attempting hard delete.
        """
        # Create a schedule to delete
        create_response = await async_client_auth.post(
            "/api/v1/schedules",
            json={
                "workflow_id": workflow_id,
                "name": "Schedule to Hard Delete",
                "trigger_type": "cron",
                "cron_expression": "0 9 * * *",
            },
        )
        schedule_id = create_response.json()["id"]

        # Hard delete the schedule (admin only)
        response = await async_client_auth.delete(
            f"/api/v1/schedules/{schedule_id}?hard_delete=true"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self, async_client_auth: AsyncClient):
        """Test deleting non-existent schedule returns 404.

        TAG: [SPEC-013-TASK-012-TEST-003]
        """
        fake_id = uuid4()
        response = await async_client_auth.delete(f"/api/v1/schedules/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# POST /api/v1/schedules/{id}/pause - Pause Schedule
# =============================================================================


class TestPauseSchedule:
    """Test suite for POST /api/v1/schedules/{id}/pause endpoint."""

    @pytest.mark.asyncio
    async def test_pause_schedule(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test pausing a schedule.

        TAG: [SPEC-013-TASK-013-TEST-001]
        REQ: REQ-013-018
        """
        response = await async_client_auth.post(
            f"/api/v1/schedules/{schedule_id}/pause"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_pause_already_paused_schedule(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test pausing an already paused schedule.

        TAG: [SPEC-013-TASK-013-TEST-002]
        """
        # Pause once
        await async_client_auth.post(f"/api/v1/schedules/{schedule_id}/pause")

        # Pause again (should be idempotent or return appropriate status)
        response = await async_client_auth.post(
            f"/api/v1/schedules/{schedule_id}/pause"
        )

        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        )

    @pytest.mark.asyncio
    async def test_pause_schedule_not_found(self, async_client_auth: AsyncClient):
        """Test pausing non-existent schedule returns 404.

        TAG: [SPEC-013-TASK-013-TEST-003]
        """
        fake_id = uuid4()
        response = await async_client_auth.post(f"/api/v1/schedules/{fake_id}/pause")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# POST /api/v1/schedules/{id}/resume - Resume Schedule
# =============================================================================


class TestResumeSchedule:
    """Test suite for POST /api/v1/schedules/{id}/resume endpoint."""

    @pytest.mark.asyncio
    async def test_resume_schedule(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test resuming a paused schedule.

        TAG: [SPEC-013-TASK-013-TEST-004]
        REQ: REQ-013-019
        """
        # First pause the schedule
        await async_client_auth.post(f"/api/v1/schedules/{schedule_id}/pause")

        # Then resume it
        response = await async_client_auth.post(
            f"/api/v1/schedules/{schedule_id}/resume"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_resume_active_schedule(
        self, async_client_auth: AsyncClient, schedule_id: str
    ):
        """Test resuming an already active schedule.

        TAG: [SPEC-013-TASK-013-TEST-005]
        """
        response = await async_client_auth.post(
            f"/api/v1/schedules/{schedule_id}/resume"
        )

        # Should be idempotent or return appropriate status
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        )

    @pytest.mark.asyncio
    async def test_resume_schedule_not_found(self, async_client_auth: AsyncClient):
        """Test resuming non-existent schedule returns 404.

        TAG: [SPEC-013-TASK-013-TEST-006]
        """
        fake_id = uuid4()
        response = await async_client_auth.post(f"/api/v1/schedules/{fake_id}/resume")

        assert response.status_code == status.HTTP_404_NOT_FOUND
