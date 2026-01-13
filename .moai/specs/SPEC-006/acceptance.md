# SPEC-006 Acceptance Criteria: Schedule Configuration Model

## Tags

`[SPEC-006]` `[ACCEPTANCE]` `[TESTING]`

---

## Overview

Schedule Configuration Model의 완료 조건 및 테스트 시나리오를 정의합니다. Schedule 모델, ScheduleType enum, 그리고 APScheduler 통합을 위한 기능 검증을 다룹니다.

---

## Acceptance Criteria

### AC-001: Schedule 모델 생성

**Given** 데이터베이스에 workflows, users 테이블이 존재하고
**When** Schedule 모델을 사용하여 새로운 스케줄을 생성하면
**Then** schedules 테이블에 레코드가 저장되고 UUID id가 자동 생성된다

**Verification:**
```python
async def test_create_schedule(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Daily Morning Run",
        description="Run workflow every weekday at 9 AM",
        schedule_type=ScheduleType.CRON,
        schedule_config={
            "cron_expression": "0 9 * * 1-5",
            "hour": 9,
            "minute": 0,
            "day_of_week": "mon-fri",
        },
        timezone="Asia/Seoul",
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.id is not None
    assert schedule.is_active is True
    assert schedule.run_count == 0
    assert schedule.created_at is not None
```

---

### AC-002: ScheduleType Enum 검증

**Given** ScheduleType enum이 정의되어 있을 때
**When** 각 스케줄 유형을 사용하면
**Then** cron, interval, date가 지원된다

**Verification:**
```python
def test_schedule_type_enum():
    assert ScheduleType.CRON.value == "cron"
    assert ScheduleType.INTERVAL.value == "interval"
    assert ScheduleType.DATE.value == "date"
    assert str(ScheduleType.CRON) == "cron"
```

---

### AC-003: Cron Schedule 생성

**Given** Schedule 모델이 존재할 때
**When** schedule_type이 CRON인 스케줄을 생성하면
**Then** cron 표현식 기반 설정이 저장된다

**Verification:**
```python
async def test_create_cron_schedule(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Market Open Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={
            "cron_expression": "0 9 * * 1-5",
            "hour": 9,
            "minute": 0,
            "day_of_week": "mon-fri",
            "start_date": "2026-01-01T00:00:00Z",
            "end_date": "2026-12-31T23:59:59Z",
        },
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.schedule_type == ScheduleType.CRON
    assert schedule.schedule_config["hour"] == 9
    assert schedule.is_recurring is True
    assert schedule.is_one_time is False
```

---

### AC-004: Interval Schedule 생성

**Given** Schedule 모델이 존재할 때
**When** schedule_type이 INTERVAL인 스케줄을 생성하면
**Then** 고정 간격 설정이 저장된다

**Verification:**
```python
async def test_create_interval_schedule(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Hourly Check",
        schedule_type=ScheduleType.INTERVAL,
        schedule_config={
            "hours": 1,
            "minutes": 0,
            "seconds": 0,
            "start_date": "2026-01-01T00:00:00Z",
        },
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.schedule_type == ScheduleType.INTERVAL
    assert schedule.schedule_config["hours"] == 1
    assert schedule.is_recurring is True
    assert schedule.is_one_time is False
```

---

### AC-005: Date Schedule 생성 (일회성)

**Given** Schedule 모델이 존재할 때
**When** schedule_type이 DATE인 스케줄을 생성하면
**Then** 일회성 실행 설정이 저장된다

**Verification:**
```python
async def test_create_date_schedule(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="One-time Execution",
        schedule_type=ScheduleType.DATE,
        schedule_config={
            "run_date": "2026-06-15T10:30:00Z",
        },
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.schedule_type == ScheduleType.DATE
    assert schedule.is_one_time is True
    assert schedule.is_recurring is False
```

---

### AC-006: Workflow-Schedule 관계

**Given** Workflow와 Schedule이 존재할 때
**When** Workflow의 schedules를 조회하면
**Then** 해당 워크플로우의 모든 스케줄 목록을 가져올 수 있다

**Verification:**
```python
async def test_workflow_schedule_relationship(db_session, test_workflow, test_user):
    # Create multiple schedules
    for i, schedule_type in enumerate([ScheduleType.CRON, ScheduleType.INTERVAL]):
        schedule = Schedule(
            workflow_id=test_workflow.id,
            user_id=test_user.id,
            name=f"Schedule {i}",
            schedule_type=schedule_type,
            schedule_config={"hours": 1} if schedule_type == ScheduleType.INTERVAL else {"hour": 9},
        )
        db_session.add(schedule)
    await db_session.commit()

    await db_session.refresh(test_workflow)

    assert len(test_workflow.schedules) == 2
    schedule_types = {s.schedule_type for s in test_workflow.schedules}
    assert schedule_types == {ScheduleType.CRON, ScheduleType.INTERVAL}
```

---

### AC-007: User-Schedule 관계

**Given** User와 Schedule이 존재할 때
**When** User의 schedules를 조회하면
**Then** 해당 사용자가 생성한 모든 스케줄 목록을 가져올 수 있다

**Verification:**
```python
async def test_user_schedule_relationship(db_session, test_workflow, test_user):
    # Create schedules for user
    for i in range(3):
        schedule = Schedule(
            workflow_id=test_workflow.id,
            user_id=test_user.id,
            name=f"User Schedule {i}",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": i + 1},
        )
        db_session.add(schedule)
    await db_session.commit()

    await db_session.refresh(test_user)

    assert len(test_user.schedules) == 3
```

---

### AC-008: Schedule 활성화/비활성화

**Given** 활성 상태의 Schedule이 존재할 때
**When** deactivate() 메서드를 호출하면
**Then** is_active가 False로 변경되고 next_run_at이 None이 된다

**Verification:**
```python
async def test_schedule_deactivate(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Active Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
        next_run_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_active is True
    assert schedule.next_run_at is not None

    schedule.deactivate()
    await db_session.commit()

    assert schedule.is_active is False
    assert schedule.next_run_at is None
```

---

### AC-009: Schedule 재활성화

**Given** 비활성 상태의 만료되지 않은 Schedule이 존재할 때
**When** activate() 메서드를 호출하면
**Then** is_active가 True로 변경된다

**Verification:**
```python
async def test_schedule_activate(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Inactive Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
        is_active=False,
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_active is False

    schedule.activate()
    await db_session.commit()

    assert schedule.is_active is True
```

---

### AC-010: 만료된 Schedule 재활성화 방지

**Given** 만료된 Schedule이 존재할 때
**When** activate() 메서드를 호출하면
**Then** ValueError가 발생한다

**Verification:**
```python
async def test_activate_expired_schedule_fails(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Expired Schedule",
        schedule_type=ScheduleType.DATE,
        schedule_config={"run_date": "2020-01-01T00:00:00Z"},
        is_active=False,
        last_run_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_expired is True

    with pytest.raises(ValueError, match="Cannot activate an expired schedule"):
        schedule.activate()
```

---

### AC-011: 실행 기록 (record_execution)

**Given** 활성 Schedule이 존재할 때
**When** record_execution() 메서드를 호출하면
**Then** last_run_at이 현재 시각으로 설정되고 run_count가 증가한다

**Verification:**
```python
async def test_record_execution(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Test Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.run_count == 0
    assert schedule.last_run_at is None

    schedule.record_execution()
    await db_session.commit()

    assert schedule.run_count == 1
    assert schedule.last_run_at is not None

    # Record again
    schedule.record_execution()
    await db_session.commit()

    assert schedule.run_count == 2
```

---

### AC-012: is_one_time 속성

**Given** DATE 타입 Schedule이 존재할 때
**When** is_one_time 속성을 조회하면
**Then** True가 반환된다

**Verification:**
```python
@pytest.mark.parametrize("schedule_type,expected", [
    (ScheduleType.DATE, True),
    (ScheduleType.CRON, False),
    (ScheduleType.INTERVAL, False),
])
async def test_is_one_time(db_session, test_workflow, test_user, schedule_type, expected):
    config = {"run_date": "2026-06-15T00:00:00Z"} if schedule_type == ScheduleType.DATE else {"hour": 9}
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Test",
        schedule_type=schedule_type,
        schedule_config=config,
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_one_time == expected
```

---

### AC-013: is_recurring 속성

**Given** CRON 또는 INTERVAL 타입 Schedule이 존재할 때
**When** is_recurring 속성을 조회하면
**Then** True가 반환된다

**Verification:**
```python
@pytest.mark.parametrize("schedule_type,expected", [
    (ScheduleType.CRON, True),
    (ScheduleType.INTERVAL, True),
    (ScheduleType.DATE, False),
])
async def test_is_recurring(db_session, test_workflow, test_user, schedule_type, expected):
    config = {"run_date": "2026-06-15T00:00:00Z"} if schedule_type == ScheduleType.DATE else {"hour": 9}
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Test",
        schedule_type=schedule_type,
        schedule_config=config,
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_recurring == expected
```

---

### AC-014: is_expired 속성 - DATE 타입

**Given** DATE 타입 Schedule이 실행된 적이 있을 때
**When** is_expired 속성을 조회하면
**Then** True가 반환된다

**Verification:**
```python
async def test_is_expired_date_type(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="One-time",
        schedule_type=ScheduleType.DATE,
        schedule_config={"run_date": "2026-06-15T00:00:00Z"},
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_expired is False

    schedule.record_execution()
    await db_session.commit()

    assert schedule.is_expired is True
```

---

### AC-015: is_expired 속성 - end_date 기반

**Given** end_date가 과거인 Schedule이 존재할 때
**When** is_expired 속성을 조회하면
**Then** True가 반환된다

**Verification:**
```python
async def test_is_expired_by_end_date(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Expired by end_date",
        schedule_type=ScheduleType.CRON,
        schedule_config={
            "hour": 9,
            "end_date": "2020-12-31T23:59:59Z",
        },
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_expired is True
```

---

### AC-016: Soft Delete 동작

**Given** Schedule이 존재할 때
**When** soft_delete() 메서드를 호출하면
**Then** deleted_at이 설정되고 is_deleted가 True가 된다

**Verification:**
```python
async def test_schedule_soft_delete(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="To be deleted",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.is_deleted is False
    assert schedule.deleted_at is None

    schedule.soft_delete()
    await db_session.commit()

    assert schedule.is_deleted is True
    assert schedule.deleted_at is not None
```

---

### AC-017: Soft Delete 복원

**Given** Soft Delete된 Schedule이 존재할 때
**When** restore() 메서드를 호출하면
**Then** deleted_at이 None으로 설정되고 is_deleted가 False가 된다

**Verification:**
```python
async def test_schedule_restore(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Deleted Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
    )
    db_session.add(schedule)
    await db_session.commit()

    schedule.soft_delete()
    await db_session.commit()

    assert schedule.is_deleted is True

    schedule.restore()
    await db_session.commit()

    assert schedule.is_deleted is False
    assert schedule.deleted_at is None
```

---

### AC-018: Job ID 유일성

**Given** job_id가 설정된 Schedule이 존재할 때
**When** 동일한 job_id로 다른 Schedule을 생성하면
**Then** 무결성 오류가 발생한다

**Verification:**
```python
async def test_job_id_unique(db_session, test_workflow, test_user):
    schedule1 = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Schedule 1",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
        job_id="unique_job_123",
    )
    db_session.add(schedule1)
    await db_session.commit()

    schedule2 = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Schedule 2",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 10},
        job_id="unique_job_123",  # Same job_id
    )
    db_session.add(schedule2)

    with pytest.raises(IntegrityError):
        await db_session.commit()
```

---

### AC-019: Timezone 설정

**Given** Schedule을 생성할 때
**When** timezone을 지정하면
**Then** 해당 timezone이 저장된다

**Verification:**
```python
async def test_schedule_timezone(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Seoul Schedule",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
        timezone="Asia/Seoul",
    )
    db_session.add(schedule)
    await db_session.commit()

    assert schedule.timezone == "Asia/Seoul"
```

---

### AC-020: Timestamp 자동 관리

**Given** Schedule이 생성/수정될 때
**When** 레코드가 저장되면
**Then** created_at과 updated_at이 자동으로 설정된다

**Verification:**
```python
async def test_timestamp_management(db_session, test_workflow, test_user):
    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Timestamp Test",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
    )
    db_session.add(schedule)
    await db_session.commit()

    created = schedule.created_at
    updated = schedule.updated_at

    # Update the schedule
    await asyncio.sleep(0.1)
    schedule.name = "Updated Name"
    await db_session.commit()
    await db_session.refresh(schedule)

    assert schedule.created_at == created
    assert schedule.updated_at > updated
```

---

### AC-021: Metadata 저장 및 조회

**Given** Schedule에 metadata 필드가 존재할 때
**When** 복잡한 메타데이터 객체를 저장하면
**Then** 메타데이터가 올바르게 저장되고 조회된다

**Verification:**
```python
async def test_metadata_storage(db_session, test_workflow, test_user):
    metadata = {
        "priority": "high",
        "tags": ["daily", "market"],
        "notification": {
            "on_failure": True,
            "channels": ["slack"],
        },
        "max_instances": 1,
    }

    schedule = Schedule(
        workflow_id=test_workflow.id,
        user_id=test_user.id,
        name="Metadata Test",
        schedule_type=ScheduleType.CRON,
        schedule_config={"hour": 9},
        metadata_=metadata,
    )
    db_session.add(schedule)
    await db_session.commit()

    await db_session.refresh(schedule)

    assert schedule.metadata_["priority"] == "high"
    assert schedule.metadata_["tags"] == ["daily", "market"]
    assert schedule.metadata_["notification"]["on_failure"] is True
```

---

## Quality Gate Criteria

### Test Coverage

| Component | Required Coverage |
|-----------|------------------|
| Schedule Model | >= 90% |
| ScheduleType Enum | 100% |
| Property Methods | 100% |
| State Management | 100% |

### Code Quality

- [ ] ruff lint 통과
- [ ] mypy type check 통과
- [ ] 모든 public 메서드 docstring 작성
- [ ] 테스트 코드 작성 완료

### Performance Checklist

- [ ] 스케줄 목록 조회 200ms 이내
- [ ] 활성 스케줄 필터링 100ms 이내
- [ ] 인덱스 적용 확인

### Migration Verification

- [ ] Alembic upgrade 성공
- [ ] Alembic downgrade 성공
- [ ] 기존 데이터 무결성 유지

---

## Definition of Done

1. **모델 구현 완료**
   - ScheduleType enum 추가
   - Schedule 모델 파일 생성
   - Workflow/User 모델 관계 업데이트

2. **마이그레이션 완료**
   - Alembic 마이그레이션 스크립트 생성
   - 테스트 환경에서 마이그레이션 검증

3. **테스트 완료**
   - 모든 AC 테스트 통과
   - 커버리지 목표 달성
   - 속성 메서드 테스트 100% 커버리지

4. **코드 품질 검증**
   - Lint 통과
   - Type check 통과
   - 문서화 완료

5. **리뷰 완료**
   - PR 생성 및 코드 리뷰
   - 성능 검토 완료

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [plan.md](plan.md) - 구현 계획
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models
- [SPEC-005/acceptance.md](../SPEC-005/acceptance.md) - Execution Tracking 인수 조건

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-13 | workflow-spec | 최초 인수 조건 작성 |
