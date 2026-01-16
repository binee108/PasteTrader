"""Tests for Schedule schemas.

TAG: [SPEC-013] [TEST] [SCHEMAS] [SCHEDULE]
REQ: REQ-013-001 - Create Schedule with Cron Expression
REQ: REQ-013-002 - Create Schedule with Interval
REQ: REQ-013-003 - Read Schedules with Filtering
REQ: REQ-013-004 - Update Schedule Configuration
REQ: REQ-013-005 - Delete/Deactivate Schedule
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import ExecutionHistoryStatus, ScheduleType
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleDetailResponse,
    ScheduleResponse,
    ScheduleStatistics,
    ScheduleUpdate,
    TriggerType,
)


class TestTriggerType:
    """Test TriggerType enum."""

    def test_trigger_type_values(self) -> None:
        """Test that TriggerType has correct values."""
        assert TriggerType.CRON.value == "cron"
        assert TriggerType.INTERVAL.value == "interval"

    def test_trigger_type_is_string_enum(self) -> None:
        """Test that TriggerType is a string enum."""
        assert isinstance(TriggerType.CRON.value, str)
        assert isinstance(TriggerType.INTERVAL.value, str)


class TestScheduleStatistics:
    """Test ScheduleStatistics schema."""

    def test_schedule_statistics_fields(self) -> None:
        """Test ScheduleStatistics has all required fields."""
        stats = ScheduleStatistics(
            total_runs=10,
            successful_runs=8,
            failed_runs=2,
            success_rate=0.8,
            average_duration_ms=1500,
            last_run_at=datetime.now(UTC),
            last_status=ExecutionHistoryStatus.COMPLETED,
        )

        assert stats.total_runs == 10
        assert stats.successful_runs == 8
        assert stats.failed_runs == 2
        assert stats.success_rate == 0.8
        assert stats.average_duration_ms == 1500
        assert stats.last_run_at is not None
        assert stats.last_status == ExecutionHistoryStatus.COMPLETED

    def test_schedule_statistics_optional_fields(self) -> None:
        """Test ScheduleStatistics with optional fields."""
        stats = ScheduleStatistics(
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            success_rate=0.0,
        )

        assert stats.total_runs == 0
        assert stats.average_duration_ms is None
        assert stats.last_run_at is None
        assert stats.last_status is None


class TestScheduleCreate:
    """Test ScheduleCreate schema."""

    def test_schedule_create_with_cron(self) -> None:
        """Test creating schedule with cron expression."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Daily Backup",
            "description": "Daily backup at midnight",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "0 0 * * *",
            "timezone": "UTC",
        }

        schedule = ScheduleCreate(**data)

        assert schedule.workflow_id == workflow_id
        assert schedule.name == "Daily Backup"
        assert schedule.trigger_type == TriggerType.CRON
        assert schedule.cron_expression == "0 0 * * *"
        assert schedule.timezone == "UTC"

    def test_schedule_create_with_interval(self) -> None:
        """Test creating schedule with interval."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Hourly Sync",
            "description": "Sync every hour",
            "trigger_type": TriggerType.INTERVAL,
            "interval_hours": 1,
            "timezone": "UTC",
        }

        schedule = ScheduleCreate(**data)

        assert schedule.workflow_id == workflow_id
        assert schedule.trigger_type == TriggerType.INTERVAL
        assert schedule.interval_hours == 1

    def test_schedule_create_with_minutes(self) -> None:
        """Test creating schedule with minutes interval."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Every 30 minutes",
            "trigger_type": TriggerType.INTERVAL,
            "interval_minutes": 30,
            "timezone": "UTC",
        }

        schedule = ScheduleCreate(**data)

        assert schedule.interval_minutes == 30

    def test_schedule_create_invalid_cron_expression(self) -> None:
        """Test that invalid cron expression raises ValidationError."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Invalid Schedule",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "invalid",
            "timezone": "UTC",
        }

        with pytest.raises(ValidationError):
            ScheduleCreate(**data)

    def test_schedule_create_cron_requires_cron_expression(self) -> None:
        """Test that CRON trigger type requires cron_expression."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Missing Cron",
            "trigger_type": TriggerType.CRON,
            "timezone": "UTC",
        }

        with pytest.raises(ValidationError):
            ScheduleCreate(**data)

    def test_schedule_create_interval_requires_interval_value(self) -> None:
        """Test that INTERVAL trigger type requires at least one interval field."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Missing Interval",
            "trigger_type": TriggerType.INTERVAL,
            "timezone": "UTC",
        }

        with pytest.raises(ValidationError):
            ScheduleCreate(**data)

    def test_schedule_create_name_validation(self) -> None:
        """Test that name field has proper validation."""
        workflow_id = uuid.uuid4()

        # Empty name should fail
        with pytest.raises(ValidationError):
            ScheduleCreate(
                workflow_id=workflow_id,
                name="",
                trigger_type=TriggerType.INTERVAL,
                interval_hours=1,
            )

        # Name too long should fail
        with pytest.raises(ValidationError):
            ScheduleCreate(
                workflow_id=workflow_id,
                name="x" * 300,
                trigger_type=TriggerType.INTERVAL,
                interval_hours=1,
            )

    def test_schedule_create_timezone_validation(self) -> None:
        """Test timezone field validation."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Schedule with TZ",
            "trigger_type": TriggerType.INTERVAL,
            "interval_hours": 1,
            "timezone": "America/New_York",
        }

        schedule = ScheduleCreate(**data)
        assert schedule.timezone == "America/New_York"


class TestScheduleUpdate:
    """Test ScheduleUpdate schema."""

    def test_schedule_update_name_only(self) -> None:
        """Test updating only the name."""
        data = {"name": "Updated Name"}

        update = ScheduleUpdate(**data)

        assert update.name == "Updated Name"
        assert update.cron_expression is None
        assert update.is_active is None

    def test_schedule_update_cron_expression(self) -> None:
        """Test updating cron expression."""
        data = {"cron_expression": "0 9 * * 1-5"}

        update = ScheduleUpdate(**data)

        assert update.cron_expression == "0 9 * * 1-5"

    def test_schedule_update_is_active(self) -> None:
        """Test updating is_active field."""
        data = {"is_active": False}

        update = ScheduleUpdate(**data)

        assert update.is_active is False

    def test_schedule_update_all_fields(self) -> None:
        """Test updating all fields."""
        data = {
            "name": "Complete Update",
            "description": "Updated description",
            "cron_expression": "0 12 * * *",
            "timezone": "Europe/London",
            "is_active": True,
        }

        update = ScheduleUpdate(**data)

        assert update.name == "Complete Update"
        assert update.description == "Updated description"
        assert update.cron_expression == "0 12 * * *"
        assert update.timezone == "Europe/London"
        assert update.is_active is True


class TestScheduleResponse:
    """Test ScheduleResponse schema."""

    def test_schedule_response_from_model(self, schedule_model) -> None:
        """Test creating response from ORM model."""
        response = ScheduleResponse.model_validate(schedule_model)

        assert response.id == schedule_model.id
        assert response.workflow_id == schedule_model.workflow_id
        assert response.name == schedule_model.name
        assert response.schedule_type == schedule_model.schedule_type
        assert response.timezone == schedule_model.timezone

    def test_schedule_response_all_fields(self, schedule_model) -> None:
        """Test all fields are included in response."""
        response = ScheduleResponse.model_validate(schedule_model)

        assert hasattr(response, "id")
        assert hasattr(response, "workflow_id")
        assert hasattr(response, "name")
        assert hasattr(response, "description")
        assert hasattr(response, "schedule_type")
        assert hasattr(response, "schedule_config")
        assert hasattr(response, "timezone")
        assert hasattr(response, "is_active")
        assert hasattr(response, "next_run_at")
        assert hasattr(response, "last_run_at")
        assert hasattr(response, "run_count")
        assert hasattr(response, "created_at")
        assert hasattr(response, "updated_at")


class TestScheduleDetailResponse:
    """Test ScheduleDetailResponse schema."""

    def test_schedule_detail_response_with_statistics(self) -> None:
        """Test detail response includes statistics."""
        schedule_id = uuid.uuid4()
        workflow_id = uuid.uuid4()

        stats = ScheduleStatistics(
            total_runs=100,
            successful_runs=95,
            failed_runs=5,
            success_rate=0.95,
            average_duration_ms=2000,
            last_run_at=datetime.now(UTC),
            last_status=ExecutionHistoryStatus.COMPLETED,
        )

        detail = ScheduleDetailResponse(
            id=schedule_id,
            workflow_id=workflow_id,
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 0 * * *"},
            timezone="UTC",
            is_active=True,
            run_count=100,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            statistics=stats,
        )

        assert detail.id == schedule_id
        assert detail.statistics is not None
        assert detail.statistics.total_runs == 100
        assert detail.statistics.success_rate == 0.95


class TestScheduleValidation:
    """Test cross-field validation."""

    def test_cron_with_interval_fields_fails(self) -> None:
        """Test that cron trigger cannot have interval fields."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Invalid Mix",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "0 0 * * *",
            "interval_hours": 1,  # This should not be allowed
            "timezone": "UTC",
        }

        # Should raise validation error due to field mismatch
        with pytest.raises(ValidationError):
            ScheduleCreate(**data)

    def test_interval_with_cron_fields_fails(self) -> None:
        """Test that interval trigger cannot have cron expression."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Invalid Mix",
            "trigger_type": TriggerType.INTERVAL,
            "interval_hours": 1,
            "cron_expression": "0 0 * * *",  # This should not be allowed
            "timezone": "UTC",
        }

        # Should raise validation error due to field mismatch
        with pytest.raises(ValidationError):
            ScheduleCreate(**data)

    def test_valid_cron_expressions(self) -> None:
        """Test various valid cron expressions."""
        workflow_id = uuid.uuid4()

        valid_crons = [
            "0 0 * * *",  # Midnight daily
            "0 9 * * 1-5",  # 9 AM weekdays
            "*/5 * * * *",  # Every 5 minutes
            "0 0 1 * *",  # First of month
            "30 14 * * 3",  # 2:30 PM every Wednesday
        ]

        for cron_expr in valid_crons:
            data = {
                "workflow_id": workflow_id,
                "name": f"Test {cron_expr}",
                "trigger_type": TriggerType.CRON,
                "cron_expression": cron_expr,
                "timezone": "UTC",
            }

            schedule = ScheduleCreate(**data)
            assert schedule.cron_expression == cron_expr

    def test_cron_expression_with_six_fields(self) -> None:
        """Test cron expression with 6 fields (including year)."""
        workflow_id = uuid.uuid4()
        data = {
            "workflow_id": workflow_id,
            "name": "Cron with Year",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "0 0 12 * * 2025",  # 6 fields with year
            "timezone": "UTC",
        }

        schedule = ScheduleCreate(**data)
        assert schedule.cron_expression == "0 0 12 * * 2025"

    def test_cron_expression_with_special_characters(self) -> None:
        """Test cron expressions with special characters."""
        workflow_id = uuid.uuid4()

        # Range with dash
        data = {
            "workflow_id": workflow_id,
            "name": "Range Test",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "0 9-17 * * *",  # 9 AM to 5 PM
            "timezone": "UTC",
        }
        schedule = ScheduleCreate(**data)
        assert schedule.cron_expression == "0 9-17 * * *"

        # List with comma
        data = {
            "workflow_id": workflow_id,
            "name": "List Test",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "0 9,12,15 * * *",  # 9 AM, 12 PM, 3 PM
            "timezone": "UTC",
        }
        schedule = ScheduleCreate(**data)
        assert schedule.cron_expression == "0 9,12,15 * * *"

        # Step with slash
        data = {
            "workflow_id": workflow_id,
            "name": "Step Test",
            "trigger_type": TriggerType.CRON,
            "cron_expression": "*/15 * * * *",  # Every 15 minutes
            "timezone": "UTC",
        }
        schedule = ScheduleCreate(**data)
        assert schedule.cron_expression == "*/15 * * * *"

    def test_cron_expression_out_of_range_values(self) -> None:
        """Test that out of range values fail validation."""
        workflow_id = uuid.uuid4()

        # Hour out of range (0-23)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Invalid Hour",
                trigger_type=TriggerType.CRON,
                cron_expression="0 25 * * *",  # 25 is invalid
                timezone="UTC",
            )
        assert "out of range" in str(exc_info.value).lower()

        # Minute out of range (0-59)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Invalid Minute",
                trigger_type=TriggerType.CRON,
                cron_expression="70 * * * *",  # 70 is invalid
                timezone="UTC",
            )
        assert "out of range" in str(exc_info.value).lower()

        # Day out of range (1-31)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Invalid Day",
                trigger_type=TriggerType.CRON,
                cron_expression="0 0 32 * *",  # 32 is invalid
                timezone="UTC",
            )
        assert "out of range" in str(exc_info.value).lower()

        # Month out of range (1-12)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Invalid Month",
                trigger_type=TriggerType.CRON,
                cron_expression="0 0 1 13 *",  # 13 is invalid
                timezone="UTC",
            )
        assert "out of range" in str(exc_info.value).lower()

    def test_cron_expression_wrong_number_of_fields(self) -> None:
        """Test that wrong number of fields fails validation."""
        workflow_id = uuid.uuid4()

        # Too few fields (4 instead of 5 or 6)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Too Few Fields",
                trigger_type=TriggerType.CRON,
                cron_expression="0 0 * *",  # Only 4 fields
                timezone="UTC",
            )
        assert "5 or 6 fields" in str(exc_info.value)

        # Too many fields (7 instead of 5 or 6)
        with pytest.raises(ValidationError) as exc_info:
            ScheduleCreate(
                workflow_id=workflow_id,
                name="Too Many Fields",
                trigger_type=TriggerType.CRON,
                cron_expression="0 0 12 * * * 2025 extra",  # 7 fields
                timezone="UTC",
            )
        assert "5 or 6 fields" in str(exc_info.value)

    def test_update_with_cron_and_interval_fails(self) -> None:
        """Test that update cannot have both cron and interval fields."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleUpdate(
                cron_expression="0 0 * * *",
                interval_hours=1,
            )
        assert "cannot set both" in str(exc_info.value).lower()

    def test_update_with_interval_and_cron_fails(self) -> None:
        """Test that update with interval cannot have cron."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleUpdate(
                interval_minutes=30,
                cron_expression="*/5 * * * *",
            )
        assert "cannot set both" in str(exc_info.value).lower()
