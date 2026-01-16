"""Schedule API Router.

TAG: [SPEC-013] [API] [SCHEDULE]
REQ: REQ-013-013 - Create Schedule (POST /api/v1/schedules)
REQ: REQ-013-014 - List Schedules (GET /api/v1/schedules)
REQ: REQ-013-015 - Get Schedule Details (GET /api/v1/schedules/{id})
REQ: REQ-013-016 - Update Schedule (PUT /api/v1/schedules/{id})
REQ: REQ-013-017 - Delete Schedule (DELETE /api/v1/schedules/{id})
REQ: REQ-013-018 - Pause Schedule (POST /api/v1/schedules/{id}/pause)
REQ: REQ-013-019 - Resume Schedule (POST /api/v1/schedules/{id}/resume)

This module provides REST API endpoints for managing workflow schedules,
including creating, listing, updating, deleting, pausing, and resuming schedules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession, Pagination
from app.models.enums import ScheduleType
from app.models.schedule import Schedule, ScheduleHistory
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleDetailResponse,
    SchedulePaginatedResponse,
    ScheduleResponse,
    ScheduleStatistics,
    ScheduleUpdate,
)

if TYPE_CHECKING:
    pass

# Optional import for apscheduler (not needed for basic CRUD)
try:
    from app.services.schedule.triggers import (
        build_cron_trigger,
        build_interval_trigger,
    )
except ImportError:
    # Fallback for testing without apscheduler
    def build_cron_trigger(*args, **kwargs):  # type: ignore
        return None

    def build_interval_trigger(*args, **kwargs):  # type: ignore
        return None


router = APIRouter()

# Admin email domain for hard delete authorization
# TODO: Replace with proper role-based access control (RBAC) system
ADMIN_EMAIL_DOMAINS = {"admin.local", "localhost", "paste trader.admin"}


# =============================================================================
# Helper Functions
# =============================================================================


def is_admin_user(user: User) -> bool:
    """Check if user is an admin based on email domain.

    Args:
        user: User to check

    Returns:
        True if user email matches admin domain, False otherwise
    """
    if not user or not user.email:
        return False
    email_domain = user.email.split("@")[-1].lower()
    return email_domain in ADMIN_EMAIL_DOMAINS


async def verify_schedule_ownership(
    schedule: Schedule,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verify that the current user owns this schedule or its workflow.

    Args:
        schedule: Schedule to check ownership for
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: 403 if user doesn't own the schedule
    """
    # Check if user is the schedule creator
    if schedule.user_id == current_user.id:
        return

    # Check if user owns the workflow associated with this schedule
    result = await db.execute(
        select(Workflow).where(Workflow.id == schedule.workflow_id)
    )
    workflow = result.scalar_one_or_none()

    if workflow and workflow.owner_id == current_user.id:
        return

    # Check if user is admin (admin can manage any schedule)
    if is_admin_user(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this schedule",
    )


async def get_schedule_or_404(
    db: AsyncSession,
    schedule_id: UUID,
) -> Schedule:
    """Get schedule by ID or raise 404.

    Args:
        db: Database session
        schedule_id: UUID of the schedule

    Returns:
        Schedule: The schedule object

    Raises:
        HTTPException: 404 if schedule not found or soft deleted
    """
    result = await db.execute(
        select(Schedule)
        .where(Schedule.id == schedule_id)
        .where(Schedule.deleted_at.is_(None))  # Exclude soft deleted
        .options(selectinload(Schedule.workflow))
    )
    schedule = result.scalar_one_or_none()

    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    return schedule


async def get_workflow_or_404(
    db: AsyncSession,
    workflow_id: UUID,
) -> Workflow:
    """Get workflow by ID or raise 404.

    Args:
        db: Database session
        workflow_id: UUID of the workflow

    Returns:
        Workflow: The workflow object

    Raises:
        HTTPException: 404 if workflow not found
    """
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return workflow


async def calculate_schedule_statistics(
    db: AsyncSession,
    schedule: Schedule,
) -> ScheduleStatistics | None:
    """Calculate execution statistics for a schedule.

    Args:
        db: Database session
        schedule: Schedule object

    Returns:
        ScheduleStatistics or None if no executions
    """
    result = await db.execute(
        select(ScheduleHistory)
        .where(ScheduleHistory.schedule_id == schedule.id)
        .order_by(ScheduleHistory.created_at.desc())
        .limit(100)
    )
    histories = result.scalars().all()

    if not histories:
        return None

    total_runs = len(histories)
    successful_runs = sum(1 for h in histories if h.status == "completed")
    failed_runs = total_runs - successful_runs
    success_rate = successful_runs / total_runs if total_runs > 0 else 0.0

    total_duration = sum(h.duration_ms for h in histories)
    average_duration = total_duration // total_runs if total_runs > 0 else 0

    last_history = histories[0] if histories else None

    return ScheduleStatistics(
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        average_duration_ms=average_duration if average_duration > 0 else None,
        last_run_at=last_history.triggered_at if last_history else None,
        last_status=last_history.status if last_history else None,
    )


def convert_trigger_type_to_schedule_type(
    trigger_type: str,
) -> ScheduleType:
    """Convert API trigger type to model ScheduleType.

    Args:
        trigger_type: Trigger type from API ("cron" or "interval")

    Returns:
        ScheduleType: Corresponding ScheduleType enum
    """
    if trigger_type == "cron":
        return ScheduleType.CRON
    if trigger_type == "interval":
        return ScheduleType.INTERVAL
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid trigger_type: {trigger_type}",
    )


def build_schedule_config(
    trigger_type: str,
    cron_expression: str | None = None,
    interval_weeks: int | None = None,
    interval_days: int | None = None,
    interval_hours: int | None = None,
    interval_minutes: int | None = None,
    interval_seconds: int | None = None,
) -> dict[str, Any]:
    """Build schedule_config dict from trigger parameters.

    Args:
        trigger_type: Type of trigger ("cron" or "interval")
        cron_expression: Cron expression for cron triggers
        interval_weeks: Weeks interval
        interval_days: Days interval
        interval_hours: Hours interval
        interval_minutes: Minutes interval
        interval_seconds: Seconds interval

    Returns:
        dict: Schedule configuration
    """
    config: dict[str, Any] = {}

    if trigger_type == "cron":
        config["cron_expression"] = cron_expression
    elif trigger_type == "interval":
        if interval_weeks:
            config["weeks"] = interval_weeks
        if interval_days:
            config["days"] = interval_days
        if interval_hours:
            config["hours"] = interval_hours
        if interval_minutes:
            config["minutes"] = interval_minutes
        if interval_seconds:
            config["seconds"] = interval_seconds

    return config


# =============================================================================
# POST /api/v1/schedules - Create Schedule
# =============================================================================


@router.post(
    "/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Schedule",
    description="Create a new schedule for automated workflow execution",
)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ScheduleResponse:
    """Create a new schedule.

    TAG: [SPEC-013-TASK-008] [API] [CREATE_SCHEDULE]
    REQ: REQ-013-013

    Creates a new schedule for automated workflow execution with the
    specified trigger type (cron or interval).

    Security:
        - Requires authentication
        - User must own the workflow to create a schedule for it
    """
    # Verify workflow exists and user has access
    workflow = await get_workflow_or_404(db, schedule_data.workflow_id)

    # Verify user owns the workflow
    if workflow.owner_id != current_user.id and not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create schedules for this workflow",
        )

    # Convert trigger type to ScheduleType enum
    schedule_type = convert_trigger_type_to_schedule_type(schedule_data.trigger_type)

    # Build schedule config
    schedule_config = build_schedule_config(
        trigger_type=schedule_data.trigger_type,
        cron_expression=schedule_data.cron_expression,
        interval_hours=schedule_data.interval_hours,
        interval_minutes=schedule_data.interval_minutes,
        interval_days=schedule_data.interval_days,
        interval_weeks=schedule_data.interval_weeks,
        interval_seconds=schedule_data.interval_seconds,
    )

    # Create schedule object with current user ID
    schedule = Schedule(
        id=uuid4(),
        workflow_id=schedule_data.workflow_id,
        user_id=current_user.id,
        name=schedule_data.name,
        description=schedule_data.description,
        schedule_type=schedule_type,
        schedule_config=schedule_config,
        timezone=schedule_data.timezone,
        is_active=True,
        job_id=None,
        next_run_at=None,
        last_run_at=None,
        run_count=0,
        metadata_={},
    )

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)


# =============================================================================
# GET /api/v1/schedules - List Schedules
# =============================================================================


@router.get(
    "/schedules",
    response_model=SchedulePaginatedResponse,
    summary="List Schedules",
    description="List schedules with optional filtering and pagination",
)
async def list_schedules(
    db: DBSession,
    current_user: CurrentUser,
    pagination: Pagination,
    workflow_id: UUID | None = None,
    is_active: bool | None = None,
    trigger_type: str | None = None,
) -> dict[str, Any]:
    """List schedules with filtering and pagination.

    TAG: [SPEC-013-TASK-009] [API] [LIST_SCHEDULES]
    REQ: REQ-013-014

    Security:
        - Requires authentication
        - Users can only see their own schedules and schedules for their workflows
        - Admins can see all schedules
    """
    query = select(Schedule)

    # Apply ownership filter (non-admin users only see their own schedules)
    if not is_admin_user(current_user):
        # Get IDs of workflows owned by current user
        workflow_ids_result = await db.execute(
            select(Workflow.id).where(Workflow.owner_id == current_user.id)
        )
        user_workflow_ids = set(workflow_ids_result.scalars().all())

        # Filter by schedules created by user OR schedules for user's workflows
        query = query.where(
            or_(
                Schedule.user_id == current_user.id,
                Schedule.workflow_id.in_(user_workflow_ids),
            )
        )

    # Apply filters
    if workflow_id is not None:
        query = query.where(Schedule.workflow_id == workflow_id)

    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)

    if trigger_type is not None:
        schedule_type = convert_trigger_type_to_schedule_type(trigger_type)
        query = query.where(Schedule.schedule_type == schedule_type)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(pagination.offset).limit(pagination.limit)

    # Execute query
    result = await db.execute(query)
    schedules = result.scalars().all()

    # Convert ORM objects to Pydantic models
    items = [ScheduleResponse.model_validate(s) for s in schedules]

    # Calculate total pages
    pages = (total + pagination.limit - 1) // pagination.limit

    return {
        "items": items,
        "total": total,
        "page": pagination.offset // pagination.limit + 1,
        "size": pagination.limit,
        "pages": pages,
    }


# =============================================================================
# GET /api/v1/schedules/{id} - Get Schedule Details
# =============================================================================


@router.get(
    "/schedules/{schedule_id}",
    response_model=ScheduleDetailResponse,
    summary="Get Schedule Details",
    description="Get detailed information about a schedule including statistics",
)
async def get_schedule(
    db: DBSession,
    current_user: CurrentUser,
    schedule_id: UUID,
) -> dict[str, Any]:
    """Get schedule details by ID.

    TAG: [SPEC-013-TASK-010] [API] [GET_SCHEDULE]
    REQ: REQ-013-015

    Security:
        - Requires authentication
        - Users can only view their own schedules or schedules for their workflows
        - Admins can view any schedule
    """
    schedule = await get_schedule_or_404(db, schedule_id)

    # Verify ownership
    await verify_schedule_ownership(schedule, current_user, db)

    # Calculate statistics
    statistics = await calculate_schedule_statistics(db, schedule)

    # Build response
    return {
        "id": schedule.id,
        "workflow_id": schedule.workflow_id,
        "user_id": schedule.user_id,
        "name": schedule.name,
        "description": schedule.description,
        "schedule_type": schedule.schedule_type,
        "schedule_config": schedule.schedule_config,
        "timezone": schedule.timezone,
        "is_active": schedule.is_active,
        "job_id": schedule.job_id,
        "next_run_at": schedule.next_run_at,
        "last_run_at": schedule.last_run_at,
        "run_count": schedule.run_count,
        "metadata": schedule.metadata_,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
        "statistics": statistics,
    }



# =============================================================================
# PUT /api/v1/schedules/{id} - Update Schedule
# =============================================================================


@router.put(
    "/schedules/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Update Schedule",
    description="Update schedule configuration",
)
async def update_schedule(
    schedule_id: UUID,
    schedule_data: ScheduleUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> ScheduleResponse:
    """Update schedule by ID.

    TAG: [SPEC-013-TASK-011] [API] [UPDATE_SCHEDULE]
    REQ: REQ-013-016

    Security:
        - Requires authentication
        - Only schedule creator or workflow owner can update
        - Admins can update any schedule
    """
    schedule = await get_schedule_or_404(db, schedule_id)

    # Verify ownership
    await verify_schedule_ownership(schedule, current_user, db)

    # Update fields if provided
    if schedule_data.name is not None:
        schedule.name = schedule_data.name

    if schedule_data.description is not None:
        schedule.description = schedule_data.description

    if schedule_data.timezone is not None:
        schedule.timezone = schedule_data.timezone

    if schedule_data.is_active is not None:
        schedule.is_active = schedule_data.is_active

    # Update schedule config if provided
    if any(
        [
            schedule_data.cron_expression is not None,
            schedule_data.interval_weeks is not None,
            schedule_data.interval_days is not None,
            schedule_data.interval_hours is not None,
            schedule_data.interval_minutes is not None,
            schedule_data.interval_seconds is not None,
        ]
    ):
        # Determine trigger type from current schedule if not clear
        if schedule_data.cron_expression is not None:
            schedule.schedule_config = {
                "cron_expression": schedule_data.cron_expression
            }
        else:
            config = schedule.schedule_config.copy()
            if schedule_data.interval_weeks is not None:
                config["weeks"] = schedule_data.interval_weeks
            if schedule_data.interval_days is not None:
                config["days"] = schedule_data.interval_days
            if schedule_data.interval_hours is not None:
                config["hours"] = schedule_data.interval_hours
            if schedule_data.interval_minutes is not None:
                config["minutes"] = schedule_data.interval_minutes
            if schedule_data.interval_seconds is not None:
                config["seconds"] = schedule_data.interval_seconds
            schedule.schedule_config = config

    schedule.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)


# =============================================================================
# DELETE /api/v1/schedules/{id} - Delete Schedule
# =============================================================================


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Schedule",
    description="Delete a schedule (soft delete by default, hard delete with query param)",
)
async def delete_schedule(
    schedule_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    hard_delete: bool = False,
) -> None:
    """Delete schedule by ID.

    TAG: [SPEC-013-TASK-012] [API] [DELETE_SCHEDULE]
    REQ: REQ-013-017

    Args:
        schedule_id: UUID of the schedule to delete
        hard_delete: If True, permanently delete. If False, soft delete.
            Only admin users can perform hard delete.

    Security:
        - Requires authentication
        - Only schedule creator or workflow owner can delete
        - Hard delete is restricted to admin users only
        - Admins can delete any schedule
    """
    schedule = await get_schedule_or_404(db, schedule_id)

    # Verify ownership
    await verify_schedule_ownership(schedule, current_user, db)

    # Check admin permission for hard delete
    if hard_delete and not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can perform hard delete",
        )

    if hard_delete:
        # Hard delete (admin only)
        await db.delete(schedule)
    else:
        # Soft delete
        schedule.deleted_at = datetime.now(UTC)
        schedule.is_active = False

    await db.commit()


# =============================================================================
# POST /api/v1/schedules/{id}/pause - Pause Schedule
# =============================================================================


@router.post(
    "/schedules/{schedule_id}/pause",
    response_model=ScheduleResponse,
    summary="Pause Schedule",
    description="Pause schedule execution",
)
async def pause_schedule(
    schedule_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ScheduleResponse:
    """Pause schedule execution.

    TAG: [SPEC-013-TASK-013] [API] [PAUSE_SCHEDULE]
    REQ: REQ-013-018

    Security:
        - Requires authentication
        - Only schedule creator or workflow owner can pause
        - Admins can pause any schedule
    """
    schedule = await get_schedule_or_404(db, schedule_id)

    # Verify ownership
    await verify_schedule_ownership(schedule, current_user, db)

    if not schedule.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule is already paused",
        )

    schedule.is_active = False
    schedule.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)


# =============================================================================
# POST /api/v1/schedules/{id}/resume - Resume Schedule
# =============================================================================


@router.post(
    "/schedules/{schedule_id}/resume",
    response_model=ScheduleResponse,
    summary="Resume Schedule",
    description="Resume paused schedule execution",
)
async def resume_schedule(
    schedule_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ScheduleResponse:
    """Resume paused schedule execution.

    TAG: [SPEC-013-TASK-013] [API] [RESUME_SCHEDULE]
    REQ: REQ-013-019

    Security:
        - Requires authentication
        - Only schedule creator or workflow owner can resume
        - Admins can resume any schedule
    """
    schedule = await get_schedule_or_404(db, schedule_id)

    # Verify ownership
    await verify_schedule_ownership(schedule, current_user, db)

    if schedule.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule is already active",
        )

    schedule.is_active = True
    schedule.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse.model_validate(schedule)
