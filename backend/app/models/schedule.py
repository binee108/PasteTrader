"""Schedule model for workflow automation.

TAG: [SPEC-006] [DATABASE] [SCHEDULE] [MODEL]
REQ: REQ-001 - Schedule Model Definition
REQ: REQ-003 - Schedule Config Structure
REQ: REQ-004 - Workflow-Schedule Relationship
REQ: REQ-005 - APScheduler Job ID Management
REQ: REQ-006 - Next Run Time Tracking
REQ: REQ-007 - Schedule Execution History Tracking
REQ: REQ-008 - Soft Delete Support
REQ: REQ-009 - Schedule Metadata Management

This module defines the Schedule model for automated workflow execution
using APScheduler integration.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ExecutionHistoryStatus, ScheduleType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workflow import Workflow

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Schedule(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Workflow schedule configuration model.

    Stores scheduling configuration for automated workflow execution
    using APScheduler integration with cron, interval, and date triggers.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_id: UUID of the target workflow
        user_id: UUID of the user who created this schedule
        name: Display name of the schedule
        description: Optional description of the schedule's purpose
        schedule_type: Type of schedule (ScheduleType enum: cron, interval, date)
        schedule_config: JSONB configuration for schedule-specific settings
        timezone: Timezone for schedule execution (default: UTC)
        is_active: Whether the schedule is currently active
        job_id: APScheduler Job ID (unique, nullable)
        next_run_at: Next scheduled execution time
        last_run_at: Last execution timestamp
        run_count: Total number of times this schedule has run
        metadata: Additional metadata for the schedule
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
        workflow: Relationship to the associated Workflow
        user: Relationship to the User who created this schedule

    Schedule Config Structure by Type:

        Cron Schedule (schedule_type = CRON):
            {
                "cron_expression": "0 9 * * 1-5",  # Standard cron expression
                "year": null,                       # Optional: 4-digit year
                "month": null,                      # Optional: 1-12
                "day": null,                        # Optional: 1-31
                "week": null,                       # Optional: 1-53
                "day_of_week": "mon-fri",          # Optional: mon, tue, wed, etc.
                "hour": 9,                          # Optional: 0-23
                "minute": 0,                        # Optional: 0-59
                "second": 0,                        # Optional: 0-59
                "start_date": "2026-01-01T00:00:00Z",  # Optional: ISO 8601
                "end_date": "2026-12-31T23:59:59Z"     # Optional: ISO 8601
            }

        Interval Schedule (schedule_type = INTERVAL):
            {
                "weeks": 0,                         # Optional: weeks interval
                "days": 0,                          # Optional: days interval
                "hours": 1,                         # Optional: hours interval
                "minutes": 0,                       # Optional: minutes interval
                "seconds": 0,                       # Optional: seconds interval
                "start_date": "2026-01-01T00:00:00Z",  # Optional: ISO 8601
                "end_date": null                    # Optional: ISO 8601
            }

        Date Schedule (schedule_type = DATE):
            {
                "run_date": "2026-06-15T10:30:00Z"  # Required: ISO 8601 timestamp
            }

    Metadata Structure:
        {
            "priority": "normal",                   # Optional: normal, high, low
            "tags": ["daily", "market-open"],      # Optional: user-defined tags
            "notification": {
                "on_success": false,                # Optional: notify on success
                "on_failure": true,                 # Optional: notify on failure
                "channels": ["slack", "email"]     # Optional: notification channels
            },
            "max_instances": 1,                    # Optional: max concurrent instances
            "coalesce": true,                      # Optional: combine missed runs
            "misfire_grace_time": 60               # Optional: seconds grace for misfire
        }

    Security:
        - Only schedule creator or workflow owner can modify
        - No sensitive information in metadata field
        - job_id is UUID-based to prevent prediction

    Examples:
        >>> schedule = Schedule(
        ...     workflow_id=workflow.id,
        ...     user_id=user.id,
        ...     name="Daily Market Analysis",
        ...     description="Run market analysis every weekday at 9 AM",
        ...     schedule_type=ScheduleType.CRON,
        ...     schedule_config={"cron_expression": "0 9 * * 1-5"},
        ...     timezone="UTC"
        ... )
    """

    __tablename__ = "schedules"

    # Foreign keys
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Schedule configuration
    schedule_type: Mapped[ScheduleType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    schedule_config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Timezone and status
    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )

    # APScheduler integration
    job_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    run_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Additional metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    workflow: Mapped[Workflow] = relationship(
        "Workflow",
        back_populates="schedules",
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="schedules",
    )

    histories: Mapped[list[ScheduleHistory]] = relationship(
        "ScheduleHistory",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of the schedule."""
        return (
            f"<Schedule(id={self.id}, name='{self.name}', type={self.schedule_type})>"
        )

    @property
    def is_one_time(self) -> bool:
        """Check if this is a one-time schedule (DATE type).

        Returns:
            True if schedule_type is DATE, False otherwise.
        """
        return self.schedule_type == ScheduleType.DATE

    @property
    def is_recurring(self) -> bool:
        """Check if this is a recurring schedule (CRON or INTERVAL type).

        Returns:
            True if schedule_type is CRON or INTERVAL, False otherwise.
        """
        return self.schedule_type in (ScheduleType.CRON, ScheduleType.INTERVAL)

    @property
    def is_expired(self) -> bool:
        """Check if the schedule has expired.

        A schedule is expired if:
        - It's a DATE type schedule that has already run, or
        - It has an end_date in the past

        Returns:
            True if the schedule is expired, False otherwise.
        """
        # DATE type schedules expire after they run once
        if self.schedule_type == ScheduleType.DATE:
            run_date = self.schedule_config.get("run_date")
            if run_date and self.last_run_at:
                return True

        # Check if end_date has passed
        end_date = self.schedule_config.get("end_date")
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                return datetime.now(UTC) > end_datetime
            except (ValueError, AttributeError):
                # Invalid date format, treat as not expired
                pass

        return False

    def record_execution(self) -> None:
        """Record a schedule execution by updating execution metadata.

        Updates:
            - last_run_at: Set to current UTC time
            - run_count: Incremented by 1

        This method should be called each time a scheduled workflow
        execution is triggered.
        """
        self.last_run_at = datetime.now(UTC)
        self.run_count += 1


class ScheduleHistory(UUIDMixin, TimestampMixin, Base):
    """Schedule execution history model.

    TAG: [SPEC-013] [DATABASE] [SCHEDULE_HISTORY] [MODEL]
    REQ: REQ-013-011 - Schedule History Tracking

    Tracks the execution history of scheduled workflows, storing
    information about each scheduled execution including status,
    duration, and error messages.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Timestamp when history record was created (from TimestampMixin)
        updated_at: Timestamp when history record was last updated (from TimestampMixin)
        schedule_id: UUID of the associated schedule
        workflow_execution_id: UUID of the workflow execution
        triggered_at: Timestamp when the schedule was triggered
        status: Execution status (ExecutionHistoryStatus enum)
        duration_ms: Execution duration in milliseconds
        error_message: Error message if execution failed
        schedule: Relationship to the parent Schedule

    Examples:
        >>> history = ScheduleHistory(
        ...     schedule_id=schedule.id,
        ...     workflow_execution_id=execution.id,
        ...     triggered_at=datetime.now(UTC),
        ...     status=ExecutionHistoryStatus.COMPLETED,
        ...     duration_ms=1500
        ... )
    """

    __tablename__ = "schedule_history"

    # Foreign key to schedules table
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Workflow execution reference
    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
    )

    # Execution metadata
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    status: Mapped[ExecutionHistoryStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionHistoryStatus.PENDING,
        server_default="pending",
    )

    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationship to Schedule
    schedule: Mapped[Schedule] = relationship(
        "Schedule",
        back_populates="histories",
    )

    def __repr__(self) -> str:
        """Return string representation of the schedule history."""
        return (
            f"<ScheduleHistory(id={self.id}, "
            f"schedule_id={self.schedule_id}, "
            f"status={self.status})>"
        )


__all__ = ["Schedule", "ScheduleHistory"]
