# SPEC-013: Schedule Management Service - Acceptance Criteria

## Tags

`[SPEC-013]` `[SCHEDULE]` `[ACCEPTANCE]` `[TESTING]`

---

## Overview

This document defines the acceptance criteria for SPEC-013: Schedule Management Service using Given-When-Then format.

---

## Test Scenarios

### Feature: Schedule CRUD Operations

#### Scenario: Create schedule with cron expression

```gherkin
Given a valid workflow exists with ID "workflow-123"
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules" with:
  | field            | value                |
  | workflow_id      | workflow-123         |
  | trigger_type     | cron                 |
  | cron_expression  | 30 9,15 * * 1-5      |
  | timezone         | Asia/Seoul           |
  | is_active        | true                 |
Then the response status code should be 201
And the response should contain:
  | field            | value                |
  | workflow_id      | workflow-123         |
  | trigger_type     | cron                 |
  | cron_expression  | 30 9,15 * * 1-5      |
  | is_active        | true                 |
  | is_paused        | false                |
And the response should contain a valid "id" UUID
And the response should contain a valid "next_run_at" timestamp
And a job should be registered in APScheduler with ID "schedule-{id}"
```

#### Scenario: Create schedule with interval trigger

```gherkin
Given a valid workflow exists with ID "workflow-456"
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules" with:
  | field              | value                          |
  | workflow_id        | workflow-456                   |
  | trigger_type       | interval                       |
  | interval_seconds   | 300                            |
  | start_date         | 2026-01-16T09:00:00+09:00      |
  | end_date           | 2026-01-16T16:00:00+09:00      |
Then the response status code should be 201
And the response should contain:
  | field              | value                          |
  | trigger_type       | interval                       |
  | interval_seconds   | 300                            |
And the "next_run_at" should be within the start_date and end_date range
```

#### Scenario: Create schedule with invalid cron expression

```gherkin
Given a valid workflow exists
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules" with:
  | field            | value                |
  | workflow_id      | valid-uuid           |
  | trigger_type     | cron                 |
  | cron_expression  | invalid-cron         |
Then the response status code should be 422
And the response should contain an error message about invalid cron expression
```

#### Scenario: List schedules with pagination

```gherkin
Given 50 schedules exist in the system
And the user is authenticated
When the user sends a GET request to "/api/v1/schedules?page=2&page_size=20"
Then the response status code should be 200
And the response should contain:
  | field      | value    |
  | page       | 2        |
  | page_size  | 20       |
  | total      | 50       |
  | pages      | 3        |
And the "items" array should contain 20 schedules
```

#### Scenario: Filter schedules by workflow_id

```gherkin
Given multiple schedules exist for different workflows
And 3 schedules exist for workflow "workflow-123"
And the user is authenticated
When the user sends a GET request to "/api/v1/schedules?workflow_id=workflow-123"
Then the response status code should be 200
And the "items" array should contain exactly 3 schedules
And all items should have workflow_id equal to "workflow-123"
```

#### Scenario: Get schedule details with statistics

```gherkin
Given a schedule exists with ID "schedule-789"
And the schedule has been executed 10 times
And 8 executions were successful
And 2 executions failed
And the user is authenticated
When the user sends a GET request to "/api/v1/schedules/schedule-789"
Then the response status code should be 200
And the response should contain schedule details
And the response should contain statistics:
  | field             | value    |
  | total_runs        | 10       |
  | successful_runs   | 8        |
  | failed_runs       | 2        |
```

#### Scenario: Update schedule cron expression

```gherkin
Given a schedule exists with ID "schedule-update"
And the schedule has cron_expression "0 9 * * *"
And the user is authenticated
When the user sends a PUT request to "/api/v1/schedules/schedule-update" with:
  | field            | value           |
  | cron_expression  | 0 10 * * 1-5    |
Then the response status code should be 200
And the response should contain:
  | field            | value           |
  | cron_expression  | 0 10 * * 1-5    |
And the "next_run_at" should be recalculated
And the APScheduler job should be rescheduled
```

#### Scenario: Soft delete schedule

```gherkin
Given a schedule exists with ID "schedule-delete"
And the schedule has an active APScheduler job
And the user is authenticated
When the user sends a DELETE request to "/api/v1/schedules/schedule-delete"
Then the response status code should be 204
And the schedule should have is_active set to false
And the schedule should have deleted_at set to current timestamp
And the APScheduler job should be removed
And the schedule history should be preserved
```

#### Scenario: Hard delete schedule

```gherkin
Given a schedule exists with ID "schedule-hard-delete"
And the user is authenticated
When the user sends a DELETE request to "/api/v1/schedules/schedule-hard-delete?hard_delete=true"
Then the response status code should be 204
And the schedule record should be permanently deleted from database
And the schedule history should be permanently deleted
```

---

### Feature: Schedule Pause/Resume

#### Scenario: Pause an active schedule

```gherkin
Given a schedule exists with ID "schedule-pause"
And the schedule is_active is true
And the schedule is_paused is false
And the schedule has an active APScheduler job
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules/schedule-pause/pause"
Then the response status code should be 200
And the response should contain:
  | field       | value    |
  | is_paused   | true     |
And the "paused_at" should be set to current timestamp
And the APScheduler job should be paused
And the "next_run_at" should be preserved
```

#### Scenario: Resume a paused schedule

```gherkin
Given a schedule exists with ID "schedule-resume"
And the schedule is_paused is true
And the schedule was paused at "2026-01-15T10:00:00+09:00"
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules/schedule-resume/resume"
Then the response status code should be 200
And the response should contain:
  | field       | value    |
  | is_paused   | false    |
And the "paused_at" should be null
And the "next_run_at" should be recalculated from current time
And the APScheduler job should be resumed
```

#### Scenario: Pause a non-existent schedule

```gherkin
Given no schedule exists with ID "non-existent-id"
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules/non-existent-id/pause"
Then the response status code should be 404
And the response should contain error message "Schedule not found or already paused"
```

#### Scenario: Resume a schedule that is not paused

```gherkin
Given a schedule exists with ID "schedule-not-paused"
And the schedule is_paused is false
And the user is authenticated
When the user sends a POST request to "/api/v1/schedules/schedule-not-paused/resume"
Then the response status code should be 404
And the response should contain error message "Schedule not found or not paused"
```

---

### Feature: APScheduler Persistence

#### Scenario: Jobs survive application restart

```gherkin
Given a schedule exists with ID "schedule-persist"
And the schedule is_active is true
And an APScheduler job is registered with ID "schedule-schedule-persist"
When the application is restarted
Then the APScheduler should load jobs from PostgreSQL job store
And the job "schedule-schedule-persist" should exist in the scheduler
And the "next_run_at" should match the original schedule
```

#### Scenario: Missed jobs execute on recovery

```gherkin
Given a schedule exists with cron "0 * * * *" (every hour)
And the last run was at "2026-01-16T08:00:00+09:00"
And the application was down from 09:00 to 11:30
When the application starts at 11:30
Then the scheduler should detect the missed execution
And the workflow should execute once (coalesced)
And the schedule "last_run_at" should be updated
And the schedule "next_run_at" should be "2026-01-16T12:00:00+09:00"
```

---

### Feature: Schedule History Tracking

#### Scenario: Execution history is recorded on successful run

```gherkin
Given a schedule exists with ID "schedule-history"
And the schedule triggers at "2026-01-16T09:30:00+09:00"
When the scheduled job executes successfully
Then a new ScheduleHistory record should be created with:
  | field                  | value                          |
  | schedule_id            | schedule-history               |
  | triggered_at           | 2026-01-16T09:30:00+09:00      |
  | status                 | completed                      |
And the "workflow_execution_id" should reference the execution
And the "duration_ms" should be recorded
And the schedule "last_run_at" should be updated
```

#### Scenario: Execution history is recorded on failed run

```gherkin
Given a schedule exists with ID "schedule-history-fail"
And the workflow execution fails with error "Connection timeout"
When the scheduled job executes
Then a new ScheduleHistory record should be created with:
  | field          | value               |
  | status         | failed              |
  | error_message  | Connection timeout  |
```

---

### Feature: Next Run Time Calculation

#### Scenario: Next run time calculated for cron trigger

```gherkin
Given the current time is "2026-01-16T08:00:00+09:00" (Thursday)
And a schedule is created with cron "30 9 * * 1-5" (9:30 weekdays)
And timezone is "Asia/Seoul"
Then the "next_run_at" should be "2026-01-16T09:30:00+09:00"
```

#### Scenario: Next run time skips weekend for weekday-only cron

```gherkin
Given the current time is "2026-01-17T16:00:00+09:00" (Friday)
And a schedule is created with cron "30 9 * * 1-5" (9:30 weekdays)
And timezone is "Asia/Seoul"
Then the "next_run_at" should be "2026-01-20T09:30:00+09:00" (Monday)
```

#### Scenario: Next run time calculated for interval trigger

```gherkin
Given the current time is "2026-01-16T09:05:00+09:00"
And a schedule is created with interval_seconds 300 (5 minutes)
And start_date is "2026-01-16T09:00:00+09:00"
Then the "next_run_at" should be "2026-01-16T09:10:00+09:00"
```

---

### Feature: Timezone Handling

#### Scenario: Schedule respects specified timezone

```gherkin
Given a schedule is created with cron "0 9 * * *" (9:00 daily)
And timezone is "America/New_York"
And the current time in UTC is "2026-01-16T12:00:00Z" (7:00 AM EST)
Then the "next_run_at" should be "2026-01-16T14:00:00Z" (9:00 AM EST in UTC)
```

#### Scenario: Invalid timezone is rejected

```gherkin
Given the user is authenticated
When the user sends a POST request to "/api/v1/schedules" with:
  | field      | value               |
  | timezone   | Invalid/Timezone    |
Then the response status code should be 422
And the response should contain an error about invalid timezone
```

---

## Quality Gates

### Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| Schedule Model | 90% |
| ScheduleService | 85% |
| PersistentScheduler | 85% |
| API Endpoints | 90% |
| Overall | 85% |

### Performance Requirements

| Operation | Maximum Response Time |
|-----------|----------------------|
| Create Schedule | 200ms |
| List Schedules (paginated) | 100ms |
| Get Schedule Detail | 100ms |
| Update Schedule | 200ms |
| Pause/Resume Schedule | 100ms |
| Delete Schedule | 100ms |

### Security Requirements

- [ ] All endpoints require authentication
- [ ] Users can only access their own schedules
- [ ] Audit logging for all schedule modifications
- [ ] Input validation prevents injection attacks
- [ ] Rate limiting prevents abuse

---

## Definition of Done

- [ ] All acceptance tests pass
- [ ] Test coverage meets minimum requirements
- [ ] No critical or high severity bugs
- [ ] API documentation generated (OpenAPI)
- [ ] Code review completed
- [ ] Performance requirements met
- [ ] Security requirements verified

---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-16 | binee | Initial acceptance criteria |
