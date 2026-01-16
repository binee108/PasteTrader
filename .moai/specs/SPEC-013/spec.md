# SPEC-013: Schedule Management Service

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-013 |
| Title | Schedule Management Service |
| Created | 2026-01-16 |
| Updated | 2026-01-16 |
| Status | Draft |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | binee |
| Phase | Phase 4 - Engine Core |

## Tags

`[SPEC-013]` `[SCHEDULE]` `[APSCHEDULER]` `[CRUD]` `[PERSISTENCE]` `[POSTGRESQL]` `[BACKEND]`

---

## Overview

This SPEC defines the Schedule Management Service that provides persistent job scheduling with PostgreSQL storage and full CRUD operations. While SPEC-011 (Workflow Execution Engine) includes a basic WorkflowScheduler with in-memory storage, this SPEC implements a production-ready scheduling system with database persistence, pause/resume functionality, and comprehensive schedule management APIs.

### Scope

- Schedule CRUD Operations (Create, Read, Update, Delete)
- APScheduler AsyncIOScheduler with PostgreSQL job store
- SQLAlchemyJobStore for job persistence across restarts
- Scheduler lifecycle management (start, shutdown, pause, resume)
- Schedule features (next run time calculation, history tracking)
- Execution status monitoring and reporting
- Cron expression and interval-based scheduling support

### Out of Scope

- Workflow execution logic (covered by SPEC-011)
- DAG validation and execution ordering (covered by SPEC-010)
- Tool/Agent definitions (covered by SPEC-009)
- Workflow CRUD operations (covered by SPEC-007)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.13.x | Runtime environment |
| FastAPI | 0.115.x | API framework |
| Pydantic | 2.10.x | Schema validation |
| SQLAlchemy | 2.0.x | ORM for schedule records |
| APScheduler | 3.11.x | Job scheduling framework |
| asyncpg | 0.30.x | PostgreSQL async driver |
| PostgreSQL | 16.x | Persistent job store |

### Configuration Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow model (schedule targets)
- SPEC-005: Execution tracking models
- SPEC-011: WorkflowExecutor (execution delegation)

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| SQLAlchemyJobStore supports async operations | High | APScheduler 3.11 async support | Need custom async job store |
| PostgreSQL handles concurrent job updates | High | Row-level locking proven | Need optimistic locking |
| Cron expressions cover trading schedules | High | Standard cron format | May need custom triggers |
| Timezone handling via pytz/zoneinfo | High | APScheduler native support | Daylight saving edge cases |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Single scheduler instance per service | Medium | Multi-instance needs coordination |
| Schedule pause affects all future runs | High | Users may want selective pause |
| History retention of 30 days default | Medium | Storage growth concerns |
| Maximum 1000 active schedules | Medium | Need pagination and limits |

---

## Requirements

### Schedule CRUD Requirements

#### REQ-013-001: Create Schedule with Cron Expression

**Event-Driven Requirement**

**WHEN** a schedule creation request is received with a cron expression, **THEN** the system shall validate the cron syntax, create a schedule record, and register the job with APScheduler.

**Details:**

- Validate cron expression format (5 or 6 fields)
- Support timezone specification (default: Asia/Seoul)
- Calculate and store next_run_at timestamp
- Return schedule ID and next run time

**Example:**
```python
{
    "workflow_id": "uuid",
    "trigger_type": "cron",
    "cron_expression": "30 9,15 * * 1-5",  # 9:30 and 15:00, weekdays
    "timezone": "Asia/Seoul",
    "is_active": true,
    "metadata": {"description": "Trading session schedule"}
}
```

#### REQ-013-002: Create Schedule with Interval

**Event-Driven Requirement**

**WHEN** a schedule creation request is received with an interval trigger, **THEN** the system shall create a schedule that runs at fixed intervals.

**Details:**

- Support seconds, minutes, hours, days intervals
- Optional start_date and end_date constraints
- Calculate next_run_at based on interval

**Example:**
```python
{
    "workflow_id": "uuid",
    "trigger_type": "interval",
    "interval_seconds": 300,  # Every 5 minutes
    "start_date": "2026-01-16T09:00:00+09:00",
    "end_date": "2026-01-16T16:00:00+09:00",
    "is_active": true
}
```

#### REQ-013-003: Read Schedules with Filtering and Pagination

**Event-Driven Requirement**

**WHEN** a list schedules request is received, **THEN** the system shall return schedules matching the filter criteria with pagination support.

**Filter Options:**

- `workflow_id`: Filter by specific workflow
- `is_active`: Filter by active/inactive status
- `trigger_type`: Filter by cron/interval
- `page` and `page_size`: Pagination parameters

**Response Format:**
```python
{
    "items": [Schedule],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
}
```

#### REQ-013-004: Update Schedule Configuration

**Event-Driven Requirement**

**WHEN** a schedule update request is received, **THEN** the system shall update the schedule record and reschedule the job with APScheduler.

**Updatable Fields:**

- `cron_expression` or `interval_seconds`
- `timezone`
- `is_active`
- `start_date`, `end_date`
- `metadata`

**Constraints:**

- Cannot change `workflow_id` (create new schedule instead)
- Cannot change `trigger_type` (create new schedule instead)
- Must recalculate `next_run_at` after update

#### REQ-013-005: Delete/Deactivate Schedule

**Event-Driven Requirement**

**WHEN** a schedule deletion request is received, **THEN** the system shall remove the job from APScheduler and soft-delete the schedule record.

**Details:**

- Soft delete: Set `is_active = false`, `deleted_at = now()`
- Hard delete: Optional flag for permanent removal
- Remove job from APScheduler job store
- Preserve history records for audit

---

### APScheduler Integration Requirements

#### REQ-013-006: AsyncIOScheduler Configuration

**Ubiquitous Requirement**

The system shall **always** use APScheduler's AsyncIOScheduler with PostgreSQL job store for job persistence.

**Configuration:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(
        url=settings.DATABASE_URL.replace('+asyncpg', ''),
        tablename='apscheduler_jobs'
    )
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    job_defaults={
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 60
    }
)
```

#### REQ-013-007: PostgreSQL Job Store Persistence

**Ubiquitous Requirement**

The system shall **always** persist scheduled jobs to PostgreSQL to survive service restarts.

**Persistence Guarantees:**

- Jobs survive application restart
- Jobs survive container restart
- Jobs survive database failover (with replica)
- Missed jobs execute on startup (coalesce mode)

**Database Table:**
```sql
CREATE TABLE apscheduler_jobs (
    id VARCHAR(191) PRIMARY KEY,
    next_run_time TIMESTAMP WITH TIME ZONE,
    job_state BYTEA NOT NULL
);

CREATE INDEX ix_apscheduler_jobs_next_run_time
    ON apscheduler_jobs(next_run_time);
```

#### REQ-013-008: Scheduler Lifecycle Management

**Event-Driven Requirement**

**WHEN** the application starts, **THEN** the scheduler shall start and resume all active jobs from the job store.

**WHEN** the application shuts down, **THEN** the scheduler shall gracefully shutdown, allowing running jobs to complete.

**Lifecycle Methods:**
```python
async def startup_scheduler():
    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs")

async def shutdown_scheduler():
    scheduler.shutdown(wait=True)
    logger.info("Scheduler shutdown complete")
```

---

### Schedule Features Requirements

#### REQ-013-009: Next Run Time Calculation

**Event-Driven Requirement**

**WHEN** a schedule is created or updated, **THEN** the system shall calculate and store the next run time.

**WHEN** a job executes, **THEN** the system shall update the next run time for subsequent executions.

**Details:**

- Use APScheduler's trigger.get_next_fire_time()
- Store in `schedules.next_run_at` column
- Update `last_run_at` after each execution
- Handle timezone conversions correctly

#### REQ-013-010: Schedule Pause/Resume Functionality

**Event-Driven Requirement**

**WHEN** a pause request is received for a schedule, **THEN** the system shall pause the job in APScheduler and mark the schedule as paused.

**WHEN** a resume request is received for a paused schedule, **THEN** the system shall resume the job and recalculate the next run time.

**Pause Behavior:**

- Job remains in job store but does not fire
- `schedules.is_paused = true`
- `schedules.paused_at = now()`
- `next_run_at` preserved for resume

**Resume Behavior:**

- Recalculate `next_run_at` from current time
- `schedules.is_paused = false`
- `schedules.resumed_at = now()`

#### REQ-013-011: Schedule History Tracking

**Ubiquitous Requirement**

The system shall **always** record execution history for each scheduled run.

**History Record:**
```python
@dataclass
class ScheduleExecutionHistory:
    id: UUID
    schedule_id: UUID
    workflow_execution_id: UUID | None
    triggered_at: datetime
    status: str  # triggered, completed, failed, missed
    duration_ms: float | None
    error_message: str | None
```

**Retention Policy:**

- Default: 30 days retention
- Configurable per schedule
- Automatic cleanup via scheduled job

#### REQ-013-012: Execution Status Monitoring

**Event-Driven Requirement**

**WHEN** a schedule status request is received, **THEN** the system shall return current status including next run time, last run result, and execution statistics.

**Status Response:**
```python
{
    "schedule_id": "uuid",
    "workflow_id": "uuid",
    "is_active": true,
    "is_paused": false,
    "next_run_at": "2026-01-16T15:30:00+09:00",
    "last_run_at": "2026-01-16T09:30:00+09:00",
    "last_run_status": "completed",
    "statistics": {
        "total_runs": 150,
        "successful_runs": 148,
        "failed_runs": 2,
        "average_duration_ms": 1250
    }
}
```

---

### API Endpoint Requirements

#### REQ-013-013: POST /api/v1/schedules - Create Schedule

**Event-Driven Requirement**

**WHEN** a POST request is received at `/api/v1/schedules`, **THEN** the system shall create a new schedule and return the schedule details.

**Request Body:**
```json
{
    "workflow_id": "uuid",
    "trigger_type": "cron",
    "cron_expression": "30 9 * * 1-5",
    "timezone": "Asia/Seoul",
    "is_active": true,
    "metadata": {}
}
```

**Response:** `201 Created` with `ScheduleResponse`

#### REQ-013-014: GET /api/v1/schedules - List Schedules

**Event-Driven Requirement**

**WHEN** a GET request is received at `/api/v1/schedules`, **THEN** the system shall return a paginated list of schedules.

**Query Parameters:**

- `workflow_id` (optional): Filter by workflow
- `is_active` (optional): Filter by status
- `trigger_type` (optional): Filter by trigger type
- `page` (default: 1)
- `page_size` (default: 20, max: 100)

**Response:** `200 OK` with `PaginatedScheduleResponse`

#### REQ-013-015: GET /api/v1/schedules/{id} - Get Schedule Details

**Event-Driven Requirement**

**WHEN** a GET request is received at `/api/v1/schedules/{id}`, **THEN** the system shall return the schedule details including status and statistics.

**Response:** `200 OK` with `ScheduleDetailResponse`

#### REQ-013-016: PUT /api/v1/schedules/{id} - Update Schedule

**Event-Driven Requirement**

**WHEN** a PUT request is received at `/api/v1/schedules/{id}`, **THEN** the system shall update the schedule configuration and reschedule the job.

**Request Body:**
```json
{
    "cron_expression": "0 10 * * 1-5",
    "timezone": "Asia/Seoul",
    "is_active": true,
    "metadata": {}
}
```

**Response:** `200 OK` with `ScheduleResponse`

#### REQ-013-017: DELETE /api/v1/schedules/{id} - Delete Schedule

**Event-Driven Requirement**

**WHEN** a DELETE request is received at `/api/v1/schedules/{id}`, **THEN** the system shall soft-delete the schedule and remove the job from APScheduler.

**Query Parameters:**

- `hard_delete` (optional, default: false): Permanently delete record

**Response:** `204 No Content`

#### REQ-013-018: POST /api/v1/schedules/{id}/pause - Pause Schedule

**Event-Driven Requirement**

**WHEN** a POST request is received at `/api/v1/schedules/{id}/pause`, **THEN** the system shall pause the schedule.

**Response:** `200 OK` with `ScheduleResponse`

#### REQ-013-019: POST /api/v1/schedules/{id}/resume - Resume Schedule

**Event-Driven Requirement**

**WHEN** a POST request is received at `/api/v1/schedules/{id}/resume`, **THEN** the system shall resume the paused schedule and recalculate next run time.

**Response:** `200 OK` with `ScheduleResponse`

---

## Specifications

### SPEC-013-A: File Structure

```
backend/
  app/
    models/
      schedule.py                # Schedule ORM model (NEW)
    schemas/
      schedule.py                # Schedule Pydantic schemas (NEW)
    services/
      schedule/
        __init__.py
        service.py               # ScheduleService (NEW)
        scheduler.py             # PersistentScheduler wrapper (NEW)
        triggers.py              # Trigger builders (NEW)
    api/
      v1/
        schedules.py             # Schedule API endpoints (NEW)
    core/
      scheduler.py               # Scheduler lifecycle (UPDATE)
```

### SPEC-013-B: Schedule Model

```python
# models/schedule.py
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"


class Schedule(Base, TimestampMixin):
    """Schedule model for persistent job scheduling.

    TAG: [SPEC-013] [SCHEDULE] [MODEL]
    """

    __tablename__ = "schedules"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()"
    )

    # Workflow reference
    workflow_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Trigger configuration
    trigger_type: Mapped[TriggerType] = mapped_column(
        SAEnum(TriggerType),
        nullable=False
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    interval_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Asia/Seoul"
    )

    # Schedule constraints
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True
    )
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Execution tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # APScheduler job reference
    job_id: Mapped[Optional[str]] = mapped_column(
        String(191),
        nullable=True,
        unique=True
    )

    # Metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="schedules"
    )
    history: Mapped[list["ScheduleHistory"]] = relationship(
        "ScheduleHistory",
        back_populates="schedule",
        cascade="all, delete-orphan"
    )


class ScheduleHistory(Base):
    """Schedule execution history.

    TAG: [SPEC-013] [SCHEDULE] [HISTORY]
    """

    __tablename__ = "schedule_history"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()"
    )
    schedule_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    workflow_execution_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="SET NULL"),
        nullable=True
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    duration_ms: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    schedule: Mapped["Schedule"] = relationship(
        "Schedule",
        back_populates="history"
    )
```

### SPEC-013-C: Schedule Schemas

```python
# schemas/schedule.py
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"


class ScheduleBase(BaseModel):
    """Base schedule schema."""

    workflow_id: UUID
    trigger_type: TriggerType
    timezone: str = Field(default="Asia/Seoul")
    is_active: bool = Field(default=True)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScheduleCreate(ScheduleBase):
    """Schema for creating a schedule.

    TAG: [SPEC-013] [SCHEMA] [CREATE]
    """

    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str], info) -> Optional[str]:
        if v is None:
            return v
        # Validate cron expression format
        parts = v.split()
        if len(parts) not in (5, 6):
            raise ValueError("Cron expression must have 5 or 6 fields")
        return v

    @field_validator("interval_seconds")
    @classmethod
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Interval must be at least 1 second")
        return v


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule.

    TAG: [SPEC-013] [SCHEMA] [UPDATE]
    """

    model_config = ConfigDict(extra="forbid")

    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None


class ScheduleResponse(BaseModel):
    """Schedule response schema.

    TAG: [SPEC-013] [SCHEMA] [RESPONSE]
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    timezone: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool
    is_paused: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ScheduleStatistics(BaseModel):
    """Schedule execution statistics."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    average_duration_ms: Optional[float] = None


class ScheduleDetailResponse(ScheduleResponse):
    """Detailed schedule response with statistics.

    TAG: [SPEC-013] [SCHEMA] [DETAIL]
    """

    statistics: ScheduleStatistics = Field(default_factory=ScheduleStatistics)
    last_run_status: Optional[str] = None


class PaginatedScheduleResponse(BaseModel):
    """Paginated schedule list response."""

    items: list[ScheduleResponse]
    total: int
    page: int
    page_size: int
    pages: int
```

### SPEC-013-D: Persistent Scheduler Service

```python
# services/schedule/scheduler.py
from datetime import datetime, UTC
from typing import Any, Callable, Optional
from uuid import UUID
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)


class PersistentScheduler:
    """APScheduler wrapper with PostgreSQL persistence.

    TAG: [SPEC-013] [SCHEDULER] [PERSISTENT]

    Provides persistent job scheduling that survives application
    restarts using PostgreSQL job store.
    """

    def __init__(self):
        # Configure PostgreSQL job store
        # Note: SQLAlchemyJobStore uses sync driver
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")

        self.jobstores = {
            'default': SQLAlchemyJobStore(
                url=sync_url,
                tablename='apscheduler_jobs'
            )
        }

        self.job_defaults = {
            'coalesce': True,  # Combine missed runs
            'max_instances': 1,  # Only one instance per job
            'misfire_grace_time': 60  # 60 second grace period
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=self.jobstores,
            job_defaults=self.job_defaults,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        self._started = False

    def start(self) -> None:
        """Start the scheduler.

        TAG: [SPEC-013] [SCHEDULER] [START]
        """
        if not self._started:
            self.scheduler.start()
            self._started = True
            job_count = len(self.scheduler.get_jobs())
            logger.info(f"Scheduler started with {job_count} persisted jobs")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler gracefully.

        TAG: [SPEC-013] [SCHEDULER] [SHUTDOWN]
        """
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler shutdown complete")

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        timezone: str = "Asia/Seoul",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        kwargs: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add a cron-triggered job.

        TAG: [SPEC-013] [SCHEDULER] [CRON]
        """
        trigger = CronTrigger.from_crontab(
            cron_expression,
            timezone=timezone
        )

        if start_date:
            trigger.start_date = start_date
        if end_date:
            trigger.end_date = end_date

        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True
        )

        logger.info(f"Added cron job: {job_id}, next run: {job.next_run_time}")
        return job.id

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        interval_seconds: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        kwargs: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add an interval-triggered job.

        TAG: [SPEC-013] [SCHEDULER] [INTERVAL]
        """
        trigger = IntervalTrigger(
            seconds=interval_seconds,
            start_date=start_date,
            end_date=end_date,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True
        )

        logger.info(f"Added interval job: {job_id}, next run: {job.next_run_time}")
        return job.id

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler.

        TAG: [SPEC-013] [SCHEDULER] [REMOVE]
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job.

        TAG: [SPEC-013] [SCHEDULER] [PAUSE]
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        TAG: [SPEC-013] [SCHEDULER] [RESUME]
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")
            return False

    def get_next_run_time(self, job_id: str) -> Optional[datetime]:
        """Get the next scheduled run time for a job.

        TAG: [SPEC-013] [SCHEDULER] [NEXT]
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    def get_job(self, job_id: str) -> Optional[Any]:
        """Get job details."""
        return self.scheduler.get_job(job_id)

    def get_all_jobs(self) -> list[Any]:
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()


# Singleton instance
persistent_scheduler = PersistentScheduler()
```

### SPEC-013-E: Schedule Service

```python
# services/schedule/service.py
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule, ScheduleHistory, TriggerType
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleDetailResponse,
    ScheduleStatistics,
    PaginatedScheduleResponse,
)
from app.services.schedule.scheduler import persistent_scheduler
from app.services.workflow.executor import DAGExecutor

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for managing schedules.

    TAG: [SPEC-013] [SERVICE]
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduler = persistent_scheduler

    async def create_schedule(
        self,
        data: ScheduleCreate,
    ) -> Schedule:
        """Create a new schedule.

        TAG: [SPEC-013] [SERVICE] [CREATE]
        """
        # Create schedule record
        schedule = Schedule(
            workflow_id=data.workflow_id,
            trigger_type=data.trigger_type,
            cron_expression=data.cron_expression,
            interval_seconds=data.interval_seconds,
            timezone=data.timezone,
            start_date=data.start_date,
            end_date=data.end_date,
            is_active=data.is_active,
            metadata_=data.metadata,
        )

        self.db.add(schedule)
        await self.db.flush()

        # Register job with scheduler if active
        if schedule.is_active:
            job_id = await self._register_job(schedule)
            schedule.job_id = job_id
            schedule.next_run_at = self.scheduler.get_next_run_time(job_id)

        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(f"Created schedule: {schedule.id}")
        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """Get a schedule by ID.

        TAG: [SPEC-013] [SERVICE] [GET]
        """
        result = await self.db.execute(
            select(Schedule).where(
                Schedule.id == schedule_id,
                Schedule.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_schedule_detail(
        self,
        schedule_id: UUID,
    ) -> Optional[ScheduleDetailResponse]:
        """Get schedule with statistics.

        TAG: [SPEC-013] [SERVICE] [DETAIL]
        """
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None

        # Get statistics
        stats = await self._get_statistics(schedule_id)
        last_status = await self._get_last_run_status(schedule_id)

        return ScheduleDetailResponse(
            **ScheduleResponse.model_validate(schedule).model_dump(),
            statistics=stats,
            last_run_status=last_status
        )

    async def list_schedules(
        self,
        workflow_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        trigger_type: Optional[TriggerType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedScheduleResponse:
        """List schedules with filtering and pagination.

        TAG: [SPEC-013] [SERVICE] [LIST]
        """
        query = select(Schedule).where(Schedule.deleted_at.is_(None))

        if workflow_id:
            query = query.where(Schedule.workflow_id == workflow_id)
        if is_active is not None:
            query = query.where(Schedule.is_active == is_active)
        if trigger_type:
            query = query.where(Schedule.trigger_type == trigger_type)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Schedule.created_at.desc())

        result = await self.db.execute(query)
        schedules = list(result.scalars().all())

        return PaginatedScheduleResponse(
            items=[ScheduleResponse.model_validate(s) for s in schedules],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size
        )

    async def update_schedule(
        self,
        schedule_id: UUID,
        data: ScheduleUpdate,
    ) -> Optional[Schedule]:
        """Update a schedule.

        TAG: [SPEC-013] [SERVICE] [UPDATE]
        """
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return None

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "metadata":
                setattr(schedule, "metadata_", value)
            else:
                setattr(schedule, field, value)

        schedule.updated_at = datetime.now(UTC)

        # Reschedule job if needed
        if schedule.job_id:
            self.scheduler.remove_job(schedule.job_id)

        if schedule.is_active and not schedule.is_paused:
            job_id = await self._register_job(schedule)
            schedule.job_id = job_id
            schedule.next_run_at = self.scheduler.get_next_run_time(job_id)
        else:
            schedule.job_id = None
            schedule.next_run_at = None

        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(f"Updated schedule: {schedule_id}")
        return schedule

    async def delete_schedule(
        self,
        schedule_id: UUID,
        hard_delete: bool = False,
    ) -> bool:
        """Delete a schedule.

        TAG: [SPEC-013] [SERVICE] [DELETE]
        """
        schedule = await self.get_schedule(schedule_id)
        if not schedule:
            return False

        # Remove from scheduler
        if schedule.job_id:
            self.scheduler.remove_job(schedule.job_id)

        if hard_delete:
            await self.db.delete(schedule)
        else:
            schedule.deleted_at = datetime.now(UTC)
            schedule.is_active = False
            schedule.job_id = None

        await self.db.commit()

        logger.info(f"Deleted schedule: {schedule_id} (hard={hard_delete})")
        return True

    async def pause_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """Pause a schedule.

        TAG: [SPEC-013] [SERVICE] [PAUSE]
        """
        schedule = await self.get_schedule(schedule_id)
        if not schedule or schedule.is_paused:
            return None

        if schedule.job_id:
            self.scheduler.pause_job(schedule.job_id)

        schedule.is_paused = True
        schedule.paused_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(f"Paused schedule: {schedule_id}")
        return schedule

    async def resume_schedule(self, schedule_id: UUID) -> Optional[Schedule]:
        """Resume a paused schedule.

        TAG: [SPEC-013] [SERVICE] [RESUME]
        """
        schedule = await self.get_schedule(schedule_id)
        if not schedule or not schedule.is_paused:
            return None

        if schedule.job_id:
            self.scheduler.resume_job(schedule.job_id)
            schedule.next_run_at = self.scheduler.get_next_run_time(
                schedule.job_id
            )

        schedule.is_paused = False
        schedule.paused_at = None

        await self.db.commit()
        await self.db.refresh(schedule)

        logger.info(f"Resumed schedule: {schedule_id}")
        return schedule

    async def _register_job(self, schedule: Schedule) -> str:
        """Register a job with the scheduler."""
        job_id = f"schedule-{schedule.id}"

        if schedule.trigger_type == TriggerType.CRON:
            return self.scheduler.add_cron_job(
                job_id=job_id,
                func=self._execute_scheduled_workflow,
                cron_expression=schedule.cron_expression,
                timezone=schedule.timezone,
                start_date=schedule.start_date,
                end_date=schedule.end_date,
                kwargs={"schedule_id": str(schedule.id)}
            )
        else:
            return self.scheduler.add_interval_job(
                job_id=job_id,
                func=self._execute_scheduled_workflow,
                interval_seconds=schedule.interval_seconds,
                start_date=schedule.start_date,
                end_date=schedule.end_date,
                kwargs={"schedule_id": str(schedule.id)}
            )

    async def _execute_scheduled_workflow(
        self,
        schedule_id: str,
    ) -> None:
        """Execute workflow for a scheduled job.

        TAG: [SPEC-013] [SERVICE] [EXECUTE]
        """
        # This method is called by APScheduler
        # Implementation delegates to WorkflowExecutor from SPEC-011
        pass

    async def _get_statistics(
        self,
        schedule_id: UUID,
    ) -> ScheduleStatistics:
        """Get execution statistics for a schedule."""
        query = select(
            func.count().label("total"),
            func.count().filter(
                ScheduleHistory.status == "completed"
            ).label("successful"),
            func.count().filter(
                ScheduleHistory.status == "failed"
            ).label("failed"),
            func.avg(ScheduleHistory.duration_ms).label("avg_duration")
        ).where(ScheduleHistory.schedule_id == schedule_id)

        result = await self.db.execute(query)
        row = result.one()

        return ScheduleStatistics(
            total_runs=row.total or 0,
            successful_runs=row.successful or 0,
            failed_runs=row.failed or 0,
            average_duration_ms=row.avg_duration
        )

    async def _get_last_run_status(
        self,
        schedule_id: UUID,
    ) -> Optional[str]:
        """Get the status of the last execution."""
        query = select(ScheduleHistory.status).where(
            ScheduleHistory.schedule_id == schedule_id
        ).order_by(ScheduleHistory.triggered_at.desc()).limit(1)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
```

### SPEC-013-F: Schedule API Endpoints

```python
# api/v1/schedules.py
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, CurrentUser
from app.models.schedule import TriggerType
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleDetailResponse,
    PaginatedScheduleResponse,
)
from app.services.schedule.service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Schedule",
    description="Create a new schedule for workflow execution.",
)
async def create_schedule(
    data: ScheduleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ScheduleResponse:
    """Create a new schedule.

    TAG: [SPEC-013] [API] [CREATE]
    """
    service = ScheduleService(db)
    schedule = await service.create_schedule(data)
    return ScheduleResponse.model_validate(schedule)


@router.get(
    "",
    response_model=PaginatedScheduleResponse,
    summary="List Schedules",
    description="Get a paginated list of schedules with optional filtering.",
)
async def list_schedules(
    db: DBSession,
    current_user: CurrentUser,
    workflow_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    trigger_type: Optional[TriggerType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedScheduleResponse:
    """List schedules with filtering and pagination.

    TAG: [SPEC-013] [API] [LIST]
    """
    service = ScheduleService(db)
    return await service.list_schedules(
        workflow_id=workflow_id,
        is_active=is_active,
        trigger_type=trigger_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleDetailResponse,
    summary="Get Schedule Details",
    description="Get schedule details including execution statistics.",
)
async def get_schedule(
    schedule_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScheduleDetailResponse:
    """Get schedule details with statistics.

    TAG: [SPEC-013] [API] [GET]
    """
    service = ScheduleService(db)
    result = await service.get_schedule_detail(schedule_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return result


@router.put(
    "/{schedule_id}",
    response_model=ScheduleResponse,
    summary="Update Schedule",
    description="Update schedule configuration.",
)
async def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ScheduleResponse:
    """Update a schedule.

    TAG: [SPEC-013] [API] [UPDATE]
    """
    service = ScheduleService(db)
    schedule = await service.update_schedule(schedule_id, data)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    return ScheduleResponse.model_validate(schedule)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Schedule",
    description="Delete a schedule (soft delete by default).",
)
async def delete_schedule(
    schedule_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(False),
) -> None:
    """Delete a schedule.

    TAG: [SPEC-013] [API] [DELETE]
    """
    service = ScheduleService(db)
    deleted = await service.delete_schedule(schedule_id, hard_delete)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )


@router.post(
    "/{schedule_id}/pause",
    response_model=ScheduleResponse,
    summary="Pause Schedule",
    description="Pause a schedule to temporarily stop executions.",
)
async def pause_schedule(
    schedule_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScheduleResponse:
    """Pause a schedule.

    TAG: [SPEC-013] [API] [PAUSE]
    """
    service = ScheduleService(db)
    schedule = await service.pause_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or already paused"
        )

    return ScheduleResponse.model_validate(schedule)


@router.post(
    "/{schedule_id}/resume",
    response_model=ScheduleResponse,
    summary="Resume Schedule",
    description="Resume a paused schedule.",
)
async def resume_schedule(
    schedule_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ScheduleResponse:
    """Resume a paused schedule.

    TAG: [SPEC-013] [API] [RESUME]
    """
    service = ScheduleService(db)
    schedule = await service.resume_schedule(schedule_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or not paused"
        )

    return ScheduleResponse.model_validate(schedule)
```

---

## Constraints

### Technical Constraints

- All schedule operations must be async/await compatible
- Must use Pydantic v2 `model_config = ConfigDict(from_attributes=True)`
- APScheduler job store must use synchronous SQLAlchemy driver
- Timezone handling must use IANA timezone names

### Performance Constraints

- Maximum 1000 active schedules per deployment
- Schedule list queries must complete within 100ms (indexed)
- Job registration must complete within 50ms
- History retention: 30 days default (configurable)

### Security Constraints

- Schedule operations require authentication
- Users can only manage schedules for their workflows
- Audit logging for all schedule modifications
- No arbitrary code execution in triggers

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow model (schedule targets)
- SPEC-005: WorkflowExecution model (history tracking)
- SPEC-011: DAGExecutor (execution delegation)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| apscheduler | >=3.11.0 | Job scheduling framework |
| sqlalchemy | >=2.0.0 | ORM and job store |
| asyncpg | >=0.30.0 | PostgreSQL async driver |
| pytz | >=2024.1 | Timezone handling |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| APScheduler job store sync operations | Medium | Medium | Use dedicated thread pool |
| Missed jobs on extended downtime | Low | High | Coalesce + grace period config |
| Timezone conversion errors | Medium | Medium | Strict IANA timezone validation |
| Job store table locking | Low | Medium | Row-level locking, connection pooling |

---

## Related SPECs

- **SPEC-003**: Workflow Domain Models (schedule targets)
- **SPEC-005**: Execution Tracking Models (history storage)
- **SPEC-011**: Workflow Execution Engine (execution delegation)

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial SPEC creation |
