# SPEC-013: Schedule Management Service - Implementation Plan

## Tags

`[SPEC-013]` `[SCHEDULE]` `[PLAN]` `[IMPLEMENTATION]`

---

## Overview

This document outlines the implementation plan for SPEC-013: Schedule Management Service. The implementation follows a phased approach with clear milestones and task decomposition.

---

## Milestones

### Milestone 1: Database Layer (Primary Goal)

**Objective:** Create Schedule and ScheduleHistory models with PostgreSQL integration.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-001 | Create Schedule model | Implement Schedule SQLAlchemy model with all fields | SPEC-001 models | High |
| T-013-002 | Create ScheduleHistory model | Implement execution history tracking model | T-013-001 | High |
| T-013-003 | Create Alembic migration | Generate and verify migration script | T-013-001, T-013-002 | High |
| T-013-004 | Add database indexes | Create indexes for workflow_id, is_active, next_run_at | T-013-003 | Medium |
| T-013-005 | Update Workflow model | Add schedules relationship to Workflow model | T-013-001 | Medium |

#### Deliverables

- `backend/app/models/schedule.py` - Schedule and ScheduleHistory models
- `backend/alembic/versions/xxx_add_schedule_models.py` - Migration script
- Updated `backend/app/models/workflow.py` - Relationship definition

---

### Milestone 2: APScheduler Integration (Primary Goal)

**Objective:** Configure APScheduler with PostgreSQL job store for persistent scheduling.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-006 | Create PersistentScheduler class | Implement APScheduler wrapper with PostgreSQL job store | - | High |
| T-013-007 | Implement cron job registration | Add method to register cron-triggered jobs | T-013-006 | High |
| T-013-008 | Implement interval job registration | Add method to register interval-triggered jobs | T-013-006 | High |
| T-013-009 | Implement job lifecycle methods | Add pause, resume, remove methods | T-013-006 | High |
| T-013-010 | Add scheduler lifecycle to FastAPI | Integrate start/shutdown with lifespan | T-013-006 | High |
| T-013-011 | Create APScheduler job store table | Create apscheduler_jobs table migration | T-013-003 | Medium |

#### Deliverables

- `backend/app/services/schedule/scheduler.py` - PersistentScheduler implementation
- `backend/app/core/scheduler.py` - FastAPI lifespan integration
- APScheduler job store table migration

---

### Milestone 3: Pydantic Schemas (Secondary Goal)

**Objective:** Define Pydantic v2 schemas for schedule API.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-012 | Create ScheduleCreate schema | Input schema with cron/interval validation | - | High |
| T-013-013 | Create ScheduleUpdate schema | Partial update schema | - | High |
| T-013-014 | Create ScheduleResponse schema | Output schema with model_validate | - | High |
| T-013-015 | Create ScheduleDetailResponse | Extended response with statistics | T-013-014 | Medium |
| T-013-016 | Create PaginatedScheduleResponse | List response with pagination | T-013-014 | Medium |
| T-013-017 | Add cron expression validator | Custom validator for cron syntax | T-013-012 | Medium |

#### Deliverables

- `backend/app/schemas/schedule.py` - All schedule schemas

---

### Milestone 4: Schedule Service (Secondary Goal)

**Objective:** Implement core schedule management business logic.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-018 | Implement create_schedule | Create schedule and register with APScheduler | T-013-001, T-013-006 | High |
| T-013-019 | Implement get_schedule | Retrieve single schedule by ID | T-013-001 | High |
| T-013-020 | Implement list_schedules | List with filtering and pagination | T-013-001 | High |
| T-013-021 | Implement update_schedule | Update and reschedule job | T-013-001, T-013-006 | High |
| T-013-022 | Implement delete_schedule | Soft/hard delete with job removal | T-013-001, T-013-006 | High |
| T-013-023 | Implement pause_schedule | Pause schedule and job | T-013-001, T-013-006 | High |
| T-013-024 | Implement resume_schedule | Resume paused schedule | T-013-001, T-013-006 | High |
| T-013-025 | Implement get_schedule_detail | Get schedule with statistics | T-013-019 | Medium |
| T-013-026 | Implement statistics calculation | Calculate run statistics from history | T-013-002 | Medium |
| T-013-027 | Implement workflow execution callback | Execute workflow when job triggers | SPEC-011 | Medium |

#### Deliverables

- `backend/app/services/schedule/service.py` - ScheduleService implementation
- `backend/app/services/schedule/__init__.py` - Module exports

---

### Milestone 5: API Endpoints (Final Goal)

**Objective:** Implement REST API endpoints for schedule management.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-028 | POST /api/v1/schedules | Create schedule endpoint | T-013-018 | High |
| T-013-029 | GET /api/v1/schedules | List schedules endpoint | T-013-020 | High |
| T-013-030 | GET /api/v1/schedules/{id} | Get schedule detail endpoint | T-013-025 | High |
| T-013-031 | PUT /api/v1/schedules/{id} | Update schedule endpoint | T-013-021 | High |
| T-013-032 | DELETE /api/v1/schedules/{id} | Delete schedule endpoint | T-013-022 | High |
| T-013-033 | POST /api/v1/schedules/{id}/pause | Pause schedule endpoint | T-013-023 | High |
| T-013-034 | POST /api/v1/schedules/{id}/resume | Resume schedule endpoint | T-013-024 | High |
| T-013-035 | Register router with app | Add schedules router to API v1 | T-013-028 to T-013-034 | High |

#### Deliverables

- `backend/app/api/v1/schedules.py` - API router implementation
- Updated `backend/app/api/v1/__init__.py` - Router registration

---

### Milestone 6: Testing (Final Goal)

**Objective:** Comprehensive test coverage for schedule management.

#### Tasks

| Task ID | Task | Description | Dependencies | Priority |
|---------|------|-------------|--------------|----------|
| T-013-036 | Unit tests for Schedule model | Test model validation and relationships | T-013-001 | High |
| T-013-037 | Unit tests for ScheduleService | Test service methods with mocked scheduler | T-013-018 to T-013-027 | High |
| T-013-038 | Unit tests for PersistentScheduler | Test scheduler wrapper methods | T-013-006 | High |
| T-013-039 | Integration tests for API | Test all endpoints with database | T-013-028 to T-013-034 | High |
| T-013-040 | Test cron expression validation | Test valid and invalid cron formats | T-013-017 | Medium |
| T-013-041 | Test scheduler persistence | Test job survival across restarts | T-013-006 | Medium |
| T-013-042 | Test pause/resume functionality | Test job state transitions | T-013-023, T-013-024 | Medium |

#### Deliverables

- `backend/tests/models/test_schedule.py` - Model tests
- `backend/tests/services/test_schedule_service.py` - Service tests
- `backend/tests/services/test_scheduler.py` - Scheduler tests
- `backend/tests/api/test_schedules.py` - API integration tests

---

## Technical Approach

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Schedule Management                       │
├─────────────────────────────────────────────────────────────┤
│  API Layer                                                   │
│  ├── POST /api/v1/schedules                                 │
│  ├── GET /api/v1/schedules                                  │
│  ├── GET /api/v1/schedules/{id}                             │
│  ├── PUT /api/v1/schedules/{id}                             │
│  ├── DELETE /api/v1/schedules/{id}                          │
│  ├── POST /api/v1/schedules/{id}/pause                      │
│  └── POST /api/v1/schedules/{id}/resume                     │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                               │
│  └── ScheduleService                                         │
│      ├── create_schedule()                                  │
│      ├── get_schedule() / get_schedule_detail()             │
│      ├── list_schedules()                                   │
│      ├── update_schedule()                                  │
│      ├── delete_schedule()                                  │
│      ├── pause_schedule()                                   │
│      └── resume_schedule()                                  │
├─────────────────────────────────────────────────────────────┤
│  Scheduler Layer                                             │
│  └── PersistentScheduler                                     │
│      ├── add_cron_job()                                     │
│      ├── add_interval_job()                                 │
│      ├── remove_job()                                       │
│      ├── pause_job()                                        │
│      ├── resume_job()                                       │
│      └── get_next_run_time()                                │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├── Schedule (ORM Model)                                   │
│  ├── ScheduleHistory (ORM Model)                            │
│  └── apscheduler_jobs (APScheduler Job Store)               │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **PostgreSQL Job Store**: Use SQLAlchemyJobStore for job persistence to survive application restarts.

2. **Synchronous Job Store**: APScheduler's SQLAlchemyJobStore requires synchronous database driver. Use psycopg2 for job store while asyncpg for application queries.

3. **Soft Delete**: Default to soft delete for schedules to preserve audit history. Hard delete available as optional parameter.

4. **Singleton Scheduler**: Use singleton pattern for PersistentScheduler to ensure single scheduler instance per application.

5. **Job ID Convention**: Use `schedule-{schedule_id}` format for APScheduler job IDs to enable correlation.

6. **Coalesce Mode**: Enable job coalescing to combine missed executions into single run on recovery.

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| APScheduler sync job store blocks event loop | High | Medium | Use dedicated thread pool for job store operations |
| Job store table locking under high load | Medium | Low | Implement connection pooling, consider async job store |
| Timezone conversion errors | Medium | Medium | Validate IANA timezone names, extensive timezone testing |
| Missed jobs not executed after extended downtime | High | Low | Configure appropriate misfire_grace_time, add monitoring |
| Schedule history table growth | Medium | Medium | Implement automatic cleanup job, configurable retention |

---

## Dependencies

### Internal Dependencies

| Dependency | Status | Required For |
|------------|--------|--------------|
| SPEC-001: Base Models | Completed | Schedule model inheritance |
| SPEC-003: Workflow Models | Completed | Foreign key relationship |
| SPEC-005: Execution Models | Completed | History tracking |
| SPEC-011: Workflow Executor | Completed | Execution callback |

### External Dependencies

| Package | Version | Status |
|---------|---------|--------|
| apscheduler | >=3.11.0 | Available |
| sqlalchemy | >=2.0.0 | Installed |
| asyncpg | >=0.30.0 | Installed |
| psycopg2-binary | >=2.9.0 | To be added |

---

## Implementation Order

1. **Phase 1: Foundation** (Milestones 1, 2)
   - Database models and migrations
   - APScheduler integration

2. **Phase 2: Core Logic** (Milestones 3, 4)
   - Pydantic schemas
   - ScheduleService implementation

3. **Phase 3: API & Testing** (Milestones 5, 6)
   - REST API endpoints
   - Comprehensive testing

---

## Success Criteria

- [ ] All 7 API endpoints implemented and tested
- [ ] PostgreSQL job store persistence verified across restarts
- [ ] Cron and interval triggers working correctly
- [ ] Pause/resume functionality operational
- [ ] Schedule history tracking functional
- [ ] Test coverage >= 85%
- [ ] No critical or high severity bugs

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial plan creation |
