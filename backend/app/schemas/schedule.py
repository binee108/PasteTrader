"""Pydantic schemas for Schedule model.

TAG: [SPEC-013] [SCHEMAS] [SCHEDULE]
REQ: REQ-013-001 - Create Schedule with Cron Expression
REQ: REQ-013-002 - Create Schedule with Interval
REQ: REQ-013-003 - Read Schedules with Filtering
REQ: REQ-013-004 - Update Schedule Configuration
REQ: REQ-013-005 - Delete/Deactivate Schedule
REQ: REQ-013-009 - Next Run Time Calculation
REQ: REQ-013-010 - Schedule Pause/Resume
REQ: REQ-013-011 - Schedule History Tracking
REQ: REQ-013-012 - Execution Status Monitoring

This module defines request/response schemas for schedule-related endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic.types import PositiveInt

from app.models.enums import ExecutionHistoryStatus, ScheduleType
from app.schemas.base import (
    BaseResponse,
    BaseSchema,
    PaginatedResponse,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Schedule Type Enum (Simplified for API)
# =============================================================================


class TriggerType(str, Enum):
    """Schedule trigger type for API.

    Simplified version of ScheduleType for client interactions.
    Maps to ScheduleType enum values (CRON, INTERVAL).
    DATE type is handled internally for one-time schedules.
    """

    CRON = ScheduleType.CRON.value  # "cron"
    INTERVAL = ScheduleType.INTERVAL.value  # "interval"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


# =============================================================================
# Schedule Statistics Schema
# =============================================================================


class ScheduleStatistics(BaseSchema):
    """Execution statistics for a schedule.

    Provides aggregated execution metrics for schedule monitoring.
    """

    total_runs: int = Field(
        ...,
        ge=0,
        description="Total number of times the schedule has run",
        examples=[100],
    )
    successful_runs: int = Field(
        ...,
        ge=0,
        description="Number of successful executions",
        examples=[95],
    )
    failed_runs: int = Field(
        ...,
        ge=0,
        description="Number of failed executions",
        examples=[5],
    )
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Success rate (0.0 to 1.0)",
        examples=[0.95],
    )
    average_duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Average execution duration in milliseconds",
        examples=[1500],
    )
    last_run_at: datetime | None = Field(
        default=None,
        description="Timestamp of the last execution",
        examples=["2026-01-15T10:30:00Z"],
    )
    last_status: ExecutionHistoryStatus | None = Field(
        default=None,
        description="Status of the last execution",
        examples=[ExecutionHistoryStatus.COMPLETED],
    )


# =============================================================================
# Schedule Base Schemas
# =============================================================================


class ScheduleBase(BaseSchema):
    """Base schema with common schedule fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the schedule",
        examples=["Daily Backup", "Hourly Sync"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description of the schedule's purpose",
        examples=["Runs backup every day at midnight"],
    )
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="Timezone for schedule execution (IANA format)",
        examples=["UTC", "America/New_York", "Europe/London"],
    )


class ScheduleConfigMixin(BaseSchema):
    """Mixin for schedule configuration fields.

    Provides validation for trigger-specific configuration.
    """

    # Cron-specific fields
    cron_expression: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Cron expression (5 or 6 fields): "
            "minute hour day month day-of-week [year]"
        ),
        examples=[
            "0 0 * * *",  # Daily at midnight
            "0 9 * * 1-5",  # Weekdays at 9 AM
            "*/5 * * * *",  # Every 5 minutes
        ],
    )

    # Interval-specific fields
    interval_weeks: PositiveInt | None = Field(
        default=None,
        description="Interval in weeks",
        examples=[1],
    )
    interval_days: PositiveInt | None = Field(
        default=None,
        description="Interval in days",
        examples=[7],
    )
    interval_hours: PositiveInt | None = Field(
        default=None,
        description="Interval in hours",
        examples=[1, 12, 24],
    )
    interval_minutes: PositiveInt | None = Field(
        default=None,
        description="Interval in minutes",
        examples=[5, 15, 30],
    )
    interval_seconds: PositiveInt | None = Field(
        default=None,
        description="Interval in seconds",
        examples=[60, 300],
    )

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: str | None) -> str | None:
        """Validate cron expression format.

        Validates standard 5-field or extended 6-field cron expressions:
        - minute (0-59)
        - hour (0-23)
        - day (1-31)
        - month (1-12)
        - day-of-week (0-7, where 0 and 7 are Sunday)
        - year (optional, 4 digits)

        Special characters supported:
        - * : all values
        - , : value list separator
        - - : range of values
        - / : step values
        """
        if v is None:
            return v

        parts = v.strip().split()
        if len(parts) not in (5, 6):
            raise ValueError(
                f"Cron expression must have 5 or 6 fields, got {len(parts)}"
            )

        # Basic validation: check that each part is valid
        # This is a simplified validation; full cron validation is complex
        valid_ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
        if len(parts) == 6:
            valid_ranges.append((1970, 2099))

        for i, part in enumerate(parts):
            if part == "*":
                continue
            if "," in part:
                # Value list: 1,2,3
                for val in part.split(","):
                    cls._validate_cron_value(val.strip(), valid_ranges[i])
            elif "-" in part:
                # Range: 1-5
                range_parts = part.split("-")
                if len(range_parts) != 2:
                    raise ValueError(f"Invalid range in cron field {i+1}: {part}")
                cls._validate_cron_value(range_parts[0], valid_ranges[i])
                cls._validate_cron_value(range_parts[1], valid_ranges[i])
            elif "/" in part:
                # Step: */5 or 1-10/2
                step_parts = part.split("/")
                if len(step_parts) != 2:
                    raise ValueError(f"Invalid step in cron field {i+1}: {part}")
            else:
                cls._validate_cron_value(part, valid_ranges[i])

        return v

    @classmethod
    def _validate_cron_value(cls, value: str, value_range: tuple[int, int]) -> None:
        """Validate a single cron value against a range."""
        try:
            num = int(value)
            min_val, max_val = value_range
            if not (min_val <= num <= max_val):
                raise ValueError(
                    f"Cron value {num} out of range [{min_val}, {max_val}]"
                )
        except ValueError as e:
            if "out of range" in str(e):
                raise
            raise ValueError(f"Invalid cron value: {value}")


# =============================================================================
# Schedule Create Schema
# =============================================================================


class ScheduleCreate(ScheduleBase, ScheduleConfigMixin):
    """Schema for creating a new schedule."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the target workflow to execute",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    trigger_type: TriggerType = Field(
        ...,
        description="Type of schedule trigger",
        examples=[TriggerType.CRON, TriggerType.INTERVAL],
    )

    @model_validator(mode="after")
    def validate_trigger_config(self) -> ScheduleCreate:
        """Validate that trigger configuration matches trigger type."""
        if self.trigger_type == TriggerType.CRON:
            if self.cron_expression is None:
                raise ValueError("cron_expression is required for CRON trigger type")
            # Check that no interval fields are set
            if any(
                [
                    self.interval_weeks,
                    self.interval_days,
                    self.interval_hours,
                    self.interval_minutes,
                    self.interval_seconds,
                ]
            ):
                raise ValueError(
                    "Interval fields cannot be set for CRON trigger type"
                )
        elif self.trigger_type == TriggerType.INTERVAL:
            # At least one interval field must be set
            if not any(
                [
                    self.interval_weeks,
                    self.interval_days,
                    self.interval_hours,
                    self.interval_minutes,
                    self.interval_seconds,
                ]
            ):
                raise ValueError(
                    "At least one interval field must be set for INTERVAL trigger type"
                )
            # Check that cron_expression is not set
            if self.cron_expression is not None:
                raise ValueError(
                    "cron_expression cannot be set for INTERVAL trigger type"
                )

        return self


# =============================================================================
# Schedule Update Schema
# =============================================================================


class ScheduleUpdate(ScheduleConfigMixin):
    """Schema for updating an existing schedule.

    All fields are optional to support partial updates.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name of the schedule",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description",
    )
    timezone: str | None = Field(
        default=None,
        max_length=50,
        description="Timezone for schedule execution",
    )
    is_active: bool | None = Field(
        default=None,
        description="Whether the schedule is currently active",
        examples=[True, False],
    )

    @model_validator(mode="after")
    def validate_update_consistency(self) -> ScheduleUpdate:
        """Validate that updates are consistent."""
        # If cron_expression is being updated, ensure interval fields are not
        if self.cron_expression is not None and any(
            [
                self.interval_weeks,
                self.interval_days,
                self.interval_hours,
                self.interval_minutes,
                self.interval_seconds,
            ]
        ):
            raise ValueError(
                "Cannot set both cron_expression and interval fields"
            )

        # If any interval field is being updated, ensure cron_expression is not
        if any(
            [
                self.interval_weeks,
                self.interval_days,
                self.interval_hours,
                self.interval_minutes,
                self.interval_seconds,
            ]
        ) and self.cron_expression is not None:
            raise ValueError(
                "Cannot set both cron_expression and interval fields"
            )

        return self


# =============================================================================
# Schedule Response Schemas
# =============================================================================


class ScheduleResponse(BaseResponse):
    """Schema for schedule in API responses."""

    workflow_id: UUID = Field(
        ...,
        description="UUID of the target workflow",
    )
    name: str = Field(
        ...,
        description="Display name of the schedule",
    )
    description: str | None = Field(
        default=None,
        description="Optional description",
    )
    schedule_type: ScheduleType = Field(
        ...,
        description="Type of schedule (CRON, INTERVAL, or DATE)",
        examples=[ScheduleType.CRON, ScheduleType.INTERVAL],
    )
    schedule_config: dict[str, Any] = Field(
        ...,
        description="Schedule configuration (JSON)",
        examples=[
            {"cron_expression": "0 0 * * *"},
            {"hours": 1, "minutes": 30},
        ],
    )
    timezone: str = Field(
        ...,
        description="Timezone for schedule execution",
    )
    is_active: bool = Field(
        ...,
        description="Whether the schedule is currently active",
    )
    next_run_at: datetime | None = Field(
        default=None,
        description="Next scheduled execution time",
    )
    last_run_at: datetime | None = Field(
        default=None,
        description="Last execution timestamp",
    )
    run_count: int = Field(
        ...,
        ge=0,
        description="Total number of times the schedule has run",
    )


class ScheduleDetailResponse(ScheduleResponse):
    """Detailed schedule response with execution statistics."""

    statistics: ScheduleStatistics | None = Field(
        default=None,
        description="Execution statistics for this schedule",
    )


# =============================================================================
# Paginated Response Types
# =============================================================================


SchedulePaginatedResponse = PaginatedResponse[ScheduleResponse]


# =============================================================================
# Export List
# =============================================================================

__all__ = [
    "ScheduleCreate",
    "ScheduleDetailResponse",
    "SchedulePaginatedResponse",
    "ScheduleResponse",
    "ScheduleStatistics",
    "ScheduleUpdate",
    "TriggerType",
]
