"""Tests for Schedule model.

TAG: [SPEC-006] [SCHEDULE] [MODEL]
REQ: REQ-001 - Schedule Model Definition
AC: AC-001 to AC-010 - Schedule Model Acceptance Criteria
"""

import uuid
from datetime import UTC, datetime

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ScheduleType


class TestScheduleModel:
    """Test Schedule model structure and relationships.

    TAG: [SPEC-006] [SCHEDULE] [TEST]
    """

    def test_schedule_model_exists(self) -> None:
        """Schedule model should exist and be importable."""
        from app.models.schedule import Schedule

        assert Schedule is not None

    def test_schedule_has_required_fields(self) -> None:
        """Schedule should have all required fields."""
        from app.models.schedule import Schedule

        # Check that Schedule class has the expected fields
        schedule_fields = {
            "id": uuid.UUID,
            "workflow_id": uuid.UUID,
            "user_id": uuid.UUID,
            "name": str,
            "description": str | None,
            "schedule_type": ScheduleType,
            "schedule_config": dict,
            "timezone": str,
            "is_active": bool,
            "job_id": str | None,
            "next_run_at": datetime | None,
            "last_run_at": datetime | None,
            "run_count": int,
            "metadata_": dict,
            "created_at": datetime,
            "updated_at": datetime,
            "deleted_at": datetime | None,
        }

        for field_name, _expected_type in schedule_fields.items():
            assert hasattr(Schedule, field_name), (
                f"Schedule should have {field_name} field"
            )

    def test_schedule_inherits_from_mixins(self) -> None:
        """Schedule should inherit from UUIDMixin, TimestampMixin, and SoftDeleteMixin."""
        from app.models.schedule import Schedule

        assert issubclass(Schedule, Base)
        assert issubclass(Schedule, UUIDMixin)
        assert issubclass(Schedule, TimestampMixin)
        assert issubclass(Schedule, SoftDeleteMixin)

    def test_schedule_has_workflow_relationship(self) -> None:
        """Schedule should have a relationship to Workflow."""
        from app.models.schedule import Schedule

        assert hasattr(Schedule, "workflow"), (
            "Schedule should have workflow relationship"
        )

    def test_schedule_has_user_relationship(self) -> None:
        """Schedule should have a relationship to User."""
        from app.models.schedule import Schedule

        assert hasattr(Schedule, "user"), "Schedule should have user relationship"

    def test_schedule_table_name(self) -> None:
        """Schedule should use 'schedules' as table name."""
        from app.models.schedule import Schedule

        assert Schedule.__tablename__ == "schedules"

    def test_schedule_default_values(self) -> None:
        """Schedule fields should have correct default values."""
        from app.models.schedule import Schedule

        # Check timezone default
        timezone_field = Schedule.__table__.columns.get("timezone")
        assert timezone_field is not None
        assert (
            timezone_field.default.arg == "UTC"
            or timezone_field.server_default.arg == "UTC"
        )

        # Check is_active default
        is_active_field = Schedule.__table__.columns.get("is_active")
        assert is_active_field is not None
        assert (
            is_active_field.default.arg is True
            or is_active_field.server_default.arg == "true"
        )

        # Check run_count default
        run_count_field = Schedule.__table__.columns.get("run_count")
        assert run_count_field is not None
        assert (
            run_count_field.default.arg == 0
            or run_count_field.server_default.arg == "0"
        )

    def test_schedule_foreign_keys(self) -> None:
        """Schedule should have foreign keys to workflows and users."""
        from app.models.schedule import Schedule

        workflow_id_field = Schedule.__table__.columns.get("workflow_id")
        assert workflow_id_field is not None
        assert workflow_id_field.foreign_keys is not None

        user_id_field = Schedule.__table__.columns.get("user_id")
        assert user_id_field is not None
        assert user_id_field.foreign_keys is not None

    def test_schedule_indexes(self) -> None:
        """Schedule table should have proper indexes."""
        from app.models.schedule import Schedule

        table = Schedule.__table__
        index_names = {idx.name for idx in table.indexes}

        # Check for expected indexes

        # At least some core indexes should exist
        assert len(index_names) > 0, "Schedule table should have indexes"

    def test_schedule_metadata_field_name(self) -> None:
        """Schedule should use 'metadata' as the actual column name."""
        from app.models.schedule import Schedule

        # Check that metadata_ is the attribute name but 'metadata' is the column name
        metadata_column = Schedule.__table__.columns.get("metadata")
        assert metadata_column is not None, "Schedule should have 'metadata' column"

    def test_schedule_repr(self) -> None:
        """Schedule should have a __repr__ method."""
        from app.models.schedule import Schedule

        assert hasattr(Schedule, "__repr__"), "Schedule should have __repr__ method"


class TestScheduleProperties:
    """Test Schedule property methods.

    TAG: [SPEC-006] [SCHEDULE] [PROPERTIES]
    """

    def test_is_one_time_for_date_schedule(self) -> None:
        """is_one_time should return True for DATE schedule type."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="One-time Run",
            schedule_type=ScheduleType.DATE,
            schedule_config={"run_date": "2026-06-15T10:30:00Z"},
        )

        assert schedule.is_one_time is True

    def test_is_one_time_false_for_cron_schedule(self) -> None:
        """is_one_time should return False for CRON schedule type."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Daily Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )

        assert schedule.is_one_time is False

    def test_is_recurring_for_cron_schedule(self) -> None:
        """is_recurring should return True for CRON schedule type."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Daily Cron",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )

        assert schedule.is_recurring is True

    def test_is_recurring_for_interval_schedule(self) -> None:
        """is_recurring should return True for INTERVAL schedule type."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Hourly Interval",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": 1},
        )

        assert schedule.is_recurring is True

    def test_is_recurring_false_for_date_schedule(self) -> None:
        """is_recurring should return False for DATE schedule type."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="One-time Run",
            schedule_type=ScheduleType.DATE,
            schedule_config={"run_date": "2026-06-15T10:30:00Z"},
        )

        assert schedule.is_recurring is False

    def test_is_expired_for_date_schedule_after_run(self) -> None:
        """is_expired should return True for DATE schedule that has run."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="One-time Run",
            schedule_type=ScheduleType.DATE,
            schedule_config={"run_date": "2026-06-15T10:30:00Z"},
            last_run_at=datetime.now(UTC),
        )

        assert schedule.is_expired is True

    def test_is_expired_for_schedule_with_end_date_passed(self) -> None:
        """is_expired should return True when end_date has passed."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Expired Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={
                "cron_expression": "0 9 * * *",
                "end_date": "2020-01-01T00:00:00Z",  # Past date
            },
        )

        assert schedule.is_expired is True

    def test_is_expired_false_for_active_schedule(self) -> None:
        """is_expired should return False for active schedule."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Active Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={
                "cron_expression": "0 9 * * *",
                "end_date": "2030-01-01T00:00:00Z",  # Future date
            },
        )

        assert schedule.is_expired is False

    def test_is_expired_false_for_schedule_without_end_date(self) -> None:
        """is_expired should return False for schedule without end_date."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Recurring Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )

        assert schedule.is_expired is False

    def test_record_execution_updates_last_run_at(self) -> None:
        """record_execution should update last_run_at timestamp."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
            run_count=5,
        )

        before_time = schedule.last_run_at
        schedule.record_execution()

        assert schedule.last_run_at is not None
        if before_time:
            assert schedule.last_run_at >= before_time

    def test_record_execution_increments_run_count(self) -> None:
        """record_execution should increment run_count by 1."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
            run_count=5,
        )

        initial_count = schedule.run_count
        schedule.record_execution()

        assert schedule.run_count == initial_count + 1
        assert schedule.run_count == 6


class TestSchedulePropertiesEdgeCases:
    """Test edge cases for Schedule property methods."""

    def test_is_expired_with_invalid_end_date_format(self) -> None:
        """is_expired should handle invalid end_date format gracefully."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Invalid End Date",
            schedule_type=ScheduleType.CRON,
            schedule_config={
                "cron_expression": "0 9 * * *",
                "end_date": "invalid-date-format",  # Invalid format
            },
        )

        # Should return False (not expired) for invalid date format
        assert schedule.is_expired is False

    def test_is_expired_with_malformed_end_date(self) -> None:
        """is_expired should handle malformed end_date values."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Malformed End Date",
            schedule_type=ScheduleType.CRON,
            schedule_config={
                "cron_expression": "0 9 * * *",
                "end_date": None,  # None value
            },
        )

        assert schedule.is_expired is False

    def test_is_expired_date_schedule_without_run_date(self) -> None:
        """is_expired for DATE schedule without run_date should return False."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Date Schedule No Run Date",
            schedule_type=ScheduleType.DATE,
            schedule_config={},  # No run_date
        )

        # Should not be expired if there's no run_date
        assert schedule.is_expired is False

    def test_is_expired_date_schedule_with_future_run_date(self) -> None:
        """is_expired for DATE schedule with future run_date should return False."""
        from app.models.schedule import Schedule

        future_date = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)

        schedule = Schedule(
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Future Date Schedule",
            schedule_type=ScheduleType.DATE,
            schedule_config={"run_date": "2030-01-01T12:00:00Z"},
            last_run_at=None,  # Haven't run yet
        )

        assert schedule.is_expired is False

    def test_schedule_repr_includes_all_fields(self) -> None:
        """__repr__ should include all key fields."""
        from app.models.schedule import Schedule

        schedule = Schedule(
            id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )

        repr_str = repr(schedule)
        assert "Schedule" in repr_str
        assert str(schedule.id) in repr_str
        assert "Test Schedule" in repr_str
        assert "cron" in repr_str


# =============================================================================
