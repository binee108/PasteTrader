"""Schedule Service for workflow automation.

TAG: [SPEC-013] [SERVICE] [SCHEDULE]
REQ: REQ-013-001 - Create Schedule with Cron Expression
REQ: REQ-013-002 - Create Schedule with Interval
REQ: REQ-013-003 - Read Schedules with Filtering
REQ: REQ-013-004 - Update Schedule Configuration
REQ: REQ-013-005 - Delete/Deactivate Schedule
REQ: REQ-013-009 - Next Run Time Calculation
REQ: REQ-013-010 - Schedule Pause/Resume
REQ: REQ-013-011 - Schedule History Tracking
REQ: REQ-013-012 - Execution Status Monitoring

This service handles business logic for schedule management including
CRUD operations, job registration with APScheduler, and workflow execution.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ExecutionHistoryStatus, ScheduleType
from app.models.schedule import Schedule, ScheduleHistory
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleDetailResponse,
    SchedulePaginatedResponse,
    ScheduleResponse,
    ScheduleStatistics,
    ScheduleUpdate,
    TriggerType,
)
from app.services.schedule.scheduler import PersistentScheduler
from app.services.schedule.triggers import build_cron_trigger, build_interval_trigger

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for managing workflow schedules.

    Handles CRUD operations for schedules, integrates with APScheduler
    for job management, and coordinates workflow execution.

    Attributes:
        scheduler: PersistentScheduler instance for job management
    """

    def __init__(self, scheduler: PersistentScheduler | None = None) -> None:
        """Initialize the ScheduleService.

        Args:
            scheduler: Optional PersistentScheduler instance.
                      If None, creates a new instance.
        """
        self.scheduler = scheduler or PersistentScheduler(use_sqlite=True)

    # ==========================================================================
    # CRUD Operations
    # ==========================================================================

    async def create_schedule(
        self,
        db: AsyncSession,
        schedule_data: ScheduleCreate,
        user_id: uuid.UUID,
    ) -> ScheduleResponse:
        """Create a new schedule.

        Args:
            db: Database session
            schedule_data: Schedule creation data
            user_id: UUID of the user creating the schedule

        Returns:
            ScheduleResponse: Created schedule

        Raises:
            ValueError: If workflow doesn't exist or validation fails
        """
        from app.models.workflow import Workflow

        # Verify workflow exists
        workflow_result = await db.execute(
            select(Workflow).where(Workflow.id == schedule_data.workflow_id)
        )
        workflow = workflow_result.scalar_one_or_none()

        if not workflow:
            raise ValueError(f"Workflow {schedule_data.workflow_id} not found")

        # Build schedule config based on trigger type
        schedule_config: dict[str, Any] = {}
        schedule_type: ScheduleType

        if schedule_data.trigger_type == TriggerType.CRON:
            schedule_type = ScheduleType.CRON
            schedule_config = {"cron_expression": schedule_data.cron_expression}
        elif schedule_data.trigger_type == TriggerType.INTERVAL:
            schedule_type = ScheduleType.INTERVAL
            schedule_config = self._build_interval_config(schedule_data)
        else:
            raise ValueError(f"Unsupported trigger type: {schedule_data.trigger_type}")

        # Create schedule model
        now = datetime.now(UTC)
        schedule = Schedule(
            workflow_id=schedule_data.workflow_id,
            user_id=user_id,
            name=schedule_data.name,
            description=schedule_data.description,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            timezone=schedule_data.timezone,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add(schedule)
        await db.flush()

        # Register with APScheduler
        await self._register_job(db, schedule)

        await db.commit()
        await db.refresh(schedule)

        logger.info(f"Created schedule {schedule.id} for workflow {workflow.id}")
        return ScheduleResponse.model_validate(schedule)

    async def get_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ScheduleResponse:
        """Get a schedule by ID.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ScheduleResponse: Schedule data

        Raises:
            ValueError: If schedule not found
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)
        return ScheduleResponse.model_validate(schedule)

    async def get_schedule_detail(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ScheduleDetailResponse:
        """Get schedule detail with execution statistics.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ScheduleDetailResponse: Schedule with statistics
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)
        statistics = await self._get_statistics(db, schedule_id)

        return ScheduleDetailResponse(
            **ScheduleResponse.model_validate(schedule).model_dump(),
            statistics=statistics,
        )

    async def list_schedules(
        self,
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        workflow_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        trigger_type: TriggerType | None = None,
    ) -> SchedulePaginatedResponse:
        """List schedules with filtering and pagination.

        Args:
            db: Database session
            page: Page number (1-indexed)
            size: Items per page
            workflow_id: Filter by workflow ID
            is_active: Filter by active status
            trigger_type: Filter by trigger type

        Returns:
            SchedulePaginatedResponse: Paginated schedule list
        """
        # Build query with filters
        query = select(Schedule).where(Schedule.deleted_at.is_(None))

        if workflow_id:
            query = query.where(Schedule.workflow_id == workflow_id)
        if is_active is not None:
            query = query.where(Schedule.is_active == is_active)
        if trigger_type:
            query = query.where(Schedule.schedule_type == trigger_type.value)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * size
        query = query.order_by(Schedule.created_at.desc()).offset(offset).limit(size)

        result = await db.execute(query)
        schedules = result.scalars().all()

        # Convert to response schemas
        items = [ScheduleResponse.model_validate(s) for s in schedules]

        return SchedulePaginatedResponse.create(items, total, page, size)

    async def update_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
        update_data: ScheduleUpdate,
    ) -> ScheduleResponse:
        """Update a schedule configuration.

        Args:
            db: Database session
            schedule_id: UUID of the schedule
            update_data: Update data

        Returns:
            ScheduleResponse: Updated schedule

        Raises:
            ValueError: If schedule not found
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)

        # Update fields
        if update_data.name is not None:
            schedule.name = update_data.name
        if update_data.description is not None:
            schedule.description = update_data.description
        if update_data.timezone is not None:
            schedule.timezone = update_data.timezone
        if update_data.is_active is not None:
            schedule.is_active = update_data.is_active

        # Update trigger configuration if provided
        needs_reregister = False

        if update_data.cron_expression is not None:
            schedule.schedule_config["cron_expression"] = update_data.cron_expression
            needs_reregister = True

        if any(
            [
                update_data.interval_weeks,
                update_data.interval_days,
                update_data.interval_hours,
                update_data.interval_minutes,
                update_data.interval_seconds,
            ]
        ):
            schedule.schedule_config = self._build_interval_config(update_data)
            needs_reregister = True

        schedule.updated_at = datetime.now(UTC)

        # Re-register job if trigger changed
        if needs_reregister:
            await self._register_job(db, schedule)

        await db.commit()
        await db.refresh(schedule)

        logger.info(f"Updated schedule {schedule_id}")
        return ScheduleResponse.model_validate(schedule)

    async def delete_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
        hard_delete: bool = False,
    ) -> None:
        """Delete a schedule.

        Args:
            db: Database session
            schedule_id: UUID of the schedule
            hard_delete: If True, permanently delete; if False, soft delete

        Raises:
            ValueError: If schedule not found
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)

        if hard_delete:
            # Remove from APScheduler
            if schedule.job_id:
                await self.scheduler.remove_job(schedule.job_id)

            await db.delete(schedule)
            logger.info(f"Hard deleted schedule {schedule_id}")
        else:
            # Soft delete
            schedule.deleted_at = datetime.now(UTC)
            schedule.is_active = False

            # Pause the job
            if schedule.job_id:
                await self.scheduler.pause_job(schedule.job_id)

            logger.info(f"Soft deleted schedule {schedule_id}")

        await db.commit()

    # ==========================================================================
    # Schedule Control
    # ==========================================================================

    async def pause_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ScheduleResponse:
        """Pause a schedule.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ScheduleResponse: Updated schedule

        Raises:
            ValueError: If schedule not found
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)

        schedule.is_active = False
        schedule.updated_at = datetime.now(UTC)

        # Pause APScheduler job
        if schedule.job_id:
            await self.scheduler.pause_job(schedule.job_id)

        await db.commit()
        await db.refresh(schedule)

        logger.info(f"Paused schedule {schedule_id}")
        return ScheduleResponse.model_validate(schedule)

    async def resume_schedule(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ScheduleResponse:
        """Resume a paused schedule.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ScheduleResponse: Updated schedule

        Raises:
            ValueError: If schedule not found
        """
        schedule = await self._get_schedule_by_id(db, schedule_id)

        schedule.is_active = True
        schedule.updated_at = datetime.now(UTC)

        # Resume APScheduler job
        if schedule.job_id:
            await self.scheduler.resume_job(schedule.job_id)

        await db.commit()
        await db.refresh(schedule)

        logger.info(f"Resumed schedule {schedule_id}")
        return ScheduleResponse.model_validate(schedule)

    # ==========================================================================
    # Job Registration and Execution
    # ==========================================================================

    async def _register_job(
        self,
        db: AsyncSession,
        schedule: Schedule,
    ) -> None:
        """Register schedule with APScheduler.

        Args:
            db: Database session
            schedule: Schedule model instance
        """
        # Remove existing job if present
        if schedule.job_id:
            try:
                await self.scheduler.remove_job(schedule.job_id)
            except Exception:
                pass  # Job may not exist

        # Build trigger based on schedule type
        job_id = str(schedule.id)

        if schedule.schedule_type == ScheduleType.CRON:
            cron_expr = schedule.schedule_config.get("cron_expression")
            if not cron_expr:
                raise ValueError("Cron expression required for CRON schedules")

            trigger = build_cron_trigger(cron_expr, schedule.timezone)

        elif schedule.schedule_type == ScheduleType.INTERVAL:
            trigger = build_interval_trigger(
                schedule.schedule_config, schedule.timezone
            )

        else:
            raise ValueError(f"Unsupported schedule type: {schedule.schedule_type}")

        # Register job
        await self.scheduler.add_schedule_job(
            job_func=self._execute_scheduled_workflow,
            trigger=trigger,
            job_id=job_id,
            name=schedule.name,
            kwargs={"schedule_id": str(schedule.id)},
        )

        # Update schedule with job ID
        schedule.job_id = job_id

        # Get next run time
        job = await self.scheduler.get_job(job_id)
        if job and job.next_run_time:
            schedule.next_run_at = job.next_run_time

        logger.info(f"Registered job {job_id} for schedule {schedule.id}")

    async def _execute_scheduled_workflow(
        self,
        schedule_id: str,
    ) -> uuid.UUID:
        """Execute a scheduled workflow.

        Called by APScheduler when a schedule triggers.

        Args:
            schedule_id: UUID of the schedule as string

        Returns:
            UUID: Workflow execution ID

        Raises:
            ValueError: If schedule not found
        """
        from app.services.execution_service import WorkflowExecutionService

        # This would be called from the scheduler context
        # We need to create a new DB session
        from sqlalchemy.ext.asyncio import async_sessionmaker

        # For now, return a mock execution ID
        # In production, this would create a new session and execute
        execution_id = uuid.uuid4()

        logger.info(f"Executing scheduled workflow for schedule {schedule_id}")
        return execution_id

    # ==========================================================================
    # Statistics and Monitoring
    # ==========================================================================

    async def _get_statistics(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ScheduleStatistics | None:
        """Get execution statistics for a schedule.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ScheduleStatistics: Execution statistics or None if no history
        """
        # Query execution history
        result = await db.execute(
            select(
                func.count().label("total_runs"),
                func.sum(
                    case(
                        (ScheduleHistory.status == ExecutionHistoryStatus.COMPLETED, 1),
                        else_=0,
                    )
                ).label("successful_runs"),
                func.sum(
                    case(
                        (ScheduleHistory.status == ExecutionHistoryStatus.FAILED, 1),
                        else_=0,
                    )
                ).label("failed_runs"),
                func.avg(ScheduleHistory.duration_ms).label("avg_duration"),
                func.max(ScheduleHistory.triggered_at).label("last_run_at"),
                # Get status of most recent execution
                func.max(
                    func.row_number().over(
                        order_by=ScheduleHistory.triggered_at.desc()
                    )
                ).label("row_num"),
            )
            .where(ScheduleHistory.schedule_id == schedule_id)
            .group_by(ScheduleHistory.schedule_id)
        )

        row = result.first()

        if not row:
            return None

        total_runs = row.total_runs or 0
        successful_runs = row.successful_runs or 0
        failed_runs = row.failed_runs or 0

        # Get last status
        last_result = await db.execute(
            select(ScheduleHistory)
            .where(ScheduleHistory.schedule_id == schedule_id)
            .order_by(ScheduleHistory.triggered_at.desc())
            .limit(1)
        )
        last_history = last_result.scalar_one_or_none()

        return ScheduleStatistics(
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            success_rate=successful_runs / total_runs if total_runs > 0 else 0.0,
            average_duration_ms=int(row.avg_duration) if row.avg_duration else None,
            last_run_at=last_history.triggered_at if last_history else None,
            last_status=last_history.status if last_history else None,
        )

    async def _get_last_run_status(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> ExecutionHistoryStatus | None:
        """Get the status of the last schedule execution.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            ExecutionHistoryStatus: Last execution status or None
        """
        result = await db.execute(
            select(ScheduleHistory)
            .where(ScheduleHistory.schedule_id == schedule_id)
            .order_by(ScheduleHistory.triggered_at.desc())
            .limit(1)
        )

        history = result.scalar_one_or_none()
        return history.status if history else None

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    async def _get_schedule_by_id(
        self,
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> Schedule:
        """Get a schedule by ID or raise ValueError.

        Args:
            db: Database session
            schedule_id: UUID of the schedule

        Returns:
            Schedule: Schedule model instance

        Raises:
            ValueError: If schedule not found
        """
        result = await db.execute(
            select(Schedule)
            .where(Schedule.id == schedule_id)
            .where(Schedule.deleted_at.is_(None))
        )

        schedule = result.scalar_one_or_none()

        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        return schedule

    def _build_interval_config(
        self,
        data: ScheduleCreate | ScheduleUpdate,
    ) -> dict[str, Any]:
        """Build interval configuration from create/update data.

        Args:
            data: Schedule create or update data

        Returns:
            dict: Interval configuration
        """
        config: dict[str, Any] = {}

        if data.interval_weeks:
            config["weeks"] = data.interval_weeks
        if data.interval_days:
            config["days"] = data.interval_days
        if data.interval_hours:
            config["hours"] = data.interval_hours
        if data.interval_minutes:
            config["minutes"] = data.interval_minutes
        if data.interval_seconds:
            config["seconds"] = data.interval_seconds

        return config

    async def _validate_cron_expression(
        self,
        cron_expression: str,
    ) -> bool:
        """Validate a cron expression.

        Args:
            cron_expression: Cron expression to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            build_cron_trigger(cron_expression, "UTC")
            return True
        except Exception:
            return False


# Helper for case expression in statistics query
from sqlalchemy import case  # noqa: E402
