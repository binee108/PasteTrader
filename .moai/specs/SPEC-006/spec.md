# SPEC-006: Schedule Configuration Model

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-006 |
| Title | Schedule Configuration Model |
| Created | 2026-01-13 |
| Status | Draft |
| Priority | Medium (P1) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 2 - Execution Models |

## Tags

`[SPEC-006]` `[DATABASE]` `[SCHEDULE]` `[WORKFLOW]` `[APSCHEDULER]` `[BACKEND]`

---

## Overview

이 SPEC은 PasteTrader의 워크플로우 예약 실행을 위한 Schedule 모델을 정의합니다. APScheduler와 통합하여 cron, interval, date 기반 스케줄링을 지원하며, 워크플로우 자동 실행의 핵심 인프라를 제공합니다.

### Scope

- Schedule 모델: 워크플로우 예약 설정 관리
- ScheduleType Enum: cron, interval, date 스케줄 유형
- APScheduler Job 메타데이터 저장
- 다음 실행 시간 추적
- 스케줄 활성화/비활성화 관리

### Out of Scope

- APScheduler 서비스 구현 (SPEC-026)
- Schedule CRUD API 엔드포인트 (SPEC-027)
- Schedule UI 컴포넌트 (SPEC-028)
- 실시간 스케줄 모니터링 (별도 SPEC)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16.x | Primary database |
| SQLAlchemy | 2.0.x | Async ORM |
| asyncpg | 0.30.x | PostgreSQL async driver |
| APScheduler | 3.10.x | Background scheduler |
| Pydantic | 2.10.x | Schema validation |

### Configuration Dependencies

- SPEC-001에서 정의된 Base 모델 및 Mixin 사용
- SPEC-003에서 정의된 Workflow 모델 참조
- SPEC-002에서 정의된 User 모델 참조
- `backend/app/models/enums.py`: ScheduleType enum 추가

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| APScheduler 3.x PostgreSQL JobStore 사용 가능 | High | APScheduler 공식 문서 | 별도 Job Store 구현 필요 |
| 스케줄 수는 워크플로우당 10개 미만 | Medium | 일반적인 사용 패턴 | 인덱스 전략 재검토 |
| Cron 표현식은 5필드 또는 6필드 지원 | High | APScheduler CronTrigger | 표현식 파싱 라이브러리 추가 |
| Timezone은 UTC 기준으로 저장 | High | 글로벌 표준 관행 | Timezone 변환 로직 필요 |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| 하나의 Workflow에 여러 Schedule 연결 가능 | High | 1:1 관계로 변경 필요 |
| APScheduler Job ID와 Schedule ID 매핑 관리 | High | Job 동기화 문제 발생 |
| 스케줄 비활성화 시 Job 일시 중지 | Medium | Job 삭제/재생성 전략 필요 |

---

## Requirements

### REQ-001: Schedule 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** 워크플로우 예약 실행을 위한 Schedule 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_id | UUID | FK -> workflows(id), NOT NULL | 대상 워크플로우 |
| user_id | UUID | FK -> users(id), NOT NULL | 스케줄 생성자 |
| name | VARCHAR(255) | NOT NULL | 스케줄 이름 |
| description | TEXT | NULL | 스케줄 설명 |
| schedule_type | ScheduleType | NOT NULL | 스케줄 유형 (cron, interval, date) |
| schedule_config | JSONB | NOT NULL | 스케줄 설정 (type별 상이) |
| timezone | VARCHAR(50) | NOT NULL, DEFAULT 'UTC' | 타임존 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 활성화 상태 |
| job_id | VARCHAR(255) | UNIQUE, NULL | APScheduler Job ID |
| next_run_at | TIMESTAMPTZ | NULL | 다음 실행 예정 시각 |
| last_run_at | TIMESTAMPTZ | NULL | 마지막 실행 시각 |
| run_count | INTEGER | NOT NULL, DEFAULT 0 | 총 실행 횟수 |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | 추가 메타데이터 |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 (TimestampMixin) |
| updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 (TimestampMixin) |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 (SoftDeleteMixin) |

### REQ-002: ScheduleType Enum 정의

**Ubiquitous Requirement**

시스템은 **항상** 스케줄 유형을 구분하는 ScheduleType enum을 제공해야 합니다.

**Details:**

| Value | Description | APScheduler Trigger |
|-------|-------------|---------------------|
| cron | Cron 표현식 기반 스케줄 | CronTrigger |
| interval | 고정 간격 스케줄 | IntervalTrigger |
| date | 일회성 예약 실행 | DateTrigger |

### REQ-003: Schedule Config 구조 정의

**State-Driven Requirement**

**IF** schedule_type이 특정 유형이면 **THEN** schedule_config는 해당 유형의 스키마를 따라야 합니다.

**Cron Schedule Config:**
```json
{
  "cron_expression": "0 9 * * 1-5",
  "year": null,
  "month": null,
  "day": null,
  "week": null,
  "day_of_week": "mon-fri",
  "hour": 9,
  "minute": 0,
  "second": 0,
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z"
}
```

**Interval Schedule Config:**
```json
{
  "weeks": 0,
  "days": 0,
  "hours": 1,
  "minutes": 0,
  "seconds": 0,
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": null
}
```

**Date Schedule Config:**
```json
{
  "run_date": "2026-06-15T10:30:00Z"
}
```

### REQ-004: Workflow-Schedule 관계

**Ubiquitous Requirement**

시스템은 **항상** Workflow와 Schedule 간 일대다 관계를 지원해야 합니다.

**Details:**
- 하나의 Workflow에 여러 Schedule 연결 가능
- Schedule 삭제 시 Workflow에 영향 없음 (Soft Delete)
- Workflow 삭제 시 연결된 Schedule도 Soft Delete

### REQ-005: APScheduler Job ID 관리

**Event-Driven Requirement**

**WHEN** Schedule이 활성화될 때, **THEN** APScheduler에 Job이 등록되고 job_id가 저장되어야 합니다.

**WHEN** Schedule이 비활성화될 때, **THEN** APScheduler에서 Job이 일시 중지되어야 합니다.

**WHEN** Schedule이 삭제될 때, **THEN** APScheduler에서 Job이 제거되어야 합니다.

### REQ-006: 다음 실행 시간 추적

**Event-Driven Requirement**

**WHEN** 스케줄이 등록되거나 실행 완료될 때, **THEN** next_run_at이 APScheduler로부터 계산되어 업데이트되어야 합니다.

**Details:**
- Cron/Interval: 다음 실행 시간 자동 계산
- Date: 실행 후 null로 설정 (일회성)
- 비활성 스케줄: next_run_at = null

### REQ-007: 스케줄 실행 이력 추적

**Event-Driven Requirement**

**WHEN** 스케줄에 의해 워크플로우가 실행될 때, **THEN** last_run_at과 run_count가 업데이트되어야 합니다.

**Details:**
- WorkflowExecution.metadata에 schedule_id 기록
- TriggerType.SCHEDULE로 실행 기록

### REQ-008: Soft Delete 지원

**Unwanted Requirement**

시스템은 Schedule 데이터를 **영구 삭제하지 않아야** 합니다.

**Details:**
- SoftDeleteMixin 상속으로 deleted_at 필드 사용
- 삭제된 스케줄은 APScheduler에서 Job 제거
- 복원 시 Job 재등록 필요

### REQ-009: 스케줄 메타데이터 관리

**Optional Requirement**

가능하면 시스템은 Schedule의 metadata 필드를 통해 추가 정보를 저장합니다.

**Metadata Structure:**
```json
{
  "priority": "normal",
  "tags": ["daily", "market-open"],
  "notification": {
    "on_success": false,
    "on_failure": true,
    "channels": ["slack", "email"]
  },
  "max_instances": 1,
  "coalesce": true,
  "misfire_grace_time": 60
}
```

### REQ-010: 동시 실행 방지 옵션

**Optional Requirement**

가능하면 시스템은 동일 스케줄의 동시 실행을 제어하는 옵션을 제공합니다.

**Details:**
- metadata.max_instances로 동시 실행 인스턴스 수 제한
- 기본값: 1 (동시 실행 방지)
- APScheduler max_instances 설정과 연동

---

## Specifications

### SPEC-006-A: 파일 구조

```
backend/
  app/
    models/
      __init__.py          # 모델 exports 업데이트
      enums.py             # ScheduleType enum 추가
      schedule.py          # Schedule 모델 (신규)
```

### SPEC-006-B: ScheduleType Enum 스펙

```python
class ScheduleType(str, Enum):
    """Schedule type classification.

    TAG: [SPEC-006] [SCHEDULE] [ENUM]

    Defines the types of schedules supported by APScheduler.
    """

    CRON = "cron"
    INTERVAL = "interval"
    DATE = "date"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
```

### SPEC-006-C: Schedule 모델 스펙

```python
class Schedule(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Workflow schedule configuration model.

    TAG: [SPEC-006] [SCHEDULE] [MODEL]

    Stores scheduling configuration for automated workflow execution
    using APScheduler integration.
    """

    __tablename__ = "schedules"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    schedule_type: Mapped[ScheduleType] = mapped_column(
        String(50),
        nullable=False,
    )
    schedule_config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        server_default="UTC",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    job_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="schedules")
    user: Mapped["User"] = relationship(back_populates="schedules")

    @property
    def is_one_time(self) -> bool:
        """Check if this is a one-time schedule."""
        return self.schedule_type == ScheduleType.DATE

    @property
    def is_recurring(self) -> bool:
        """Check if this is a recurring schedule."""
        return self.schedule_type in (ScheduleType.CRON, ScheduleType.INTERVAL)

    @property
    def is_expired(self) -> bool:
        """Check if the schedule has expired."""
        if self.schedule_type == ScheduleType.DATE:
            run_date = self.schedule_config.get("run_date")
            if run_date and self.last_run_at:
                return True
        end_date = self.schedule_config.get("end_date")
        if end_date:
            return datetime.now(UTC) > datetime.fromisoformat(end_date)
        return False

    def record_execution(self) -> None:
        """Record a schedule execution."""
        self.last_run_at = datetime.now(UTC)
        self.run_count += 1
```

### SPEC-006-D: 인덱스 전략

```sql
-- Schedule indexes
CREATE INDEX idx_schedules_workflow ON schedules(workflow_id);
CREATE INDEX idx_schedules_user ON schedules(user_id);
CREATE INDEX idx_schedules_type ON schedules(schedule_type);
CREATE INDEX idx_schedules_active ON schedules(is_active) WHERE is_active = true;
CREATE INDEX idx_schedules_next_run ON schedules(next_run_at) WHERE next_run_at IS NOT NULL;
CREATE INDEX idx_schedules_job_id ON schedules(job_id) WHERE job_id IS NOT NULL;
CREATE INDEX idx_schedules_workflow_active ON schedules(workflow_id, is_active);

-- Soft delete filter index
CREATE INDEX idx_schedules_not_deleted ON schedules(id) WHERE deleted_at IS NULL;
```

---

## Constraints

### Technical Constraints

- SPEC-001의 Base 모델 및 Mixin 사용 필수
- ScheduleType은 APScheduler Trigger 유형과 일치
- job_id는 전역 고유해야 함 (UNIQUE 제약)
- timezone은 pytz 유효 timezone이어야 함
- schedule_config는 schedule_type에 맞는 스키마 필수

### Performance Constraints

- 스케줄 목록 조회 200ms 이내
- 다음 실행 시간 계산 50ms 이내
- 활성 스케줄 필터링 100ms 이내

### Security Constraints

- 스케줄은 생성자(user_id) 또는 워크플로우 소유자만 수정 가능
- metadata 내 민감 정보 저장 금지
- job_id는 예측 불가능한 형식 권장 (UUID 기반)

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base 모델, Mixins, Enums
- SPEC-002: User 모델 (user_id FK)
- SPEC-003: Workflow 모델 (workflow_id FK)
- SPEC-005: WorkflowExecution 모델 (트리거 연동)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| asyncpg | >=0.30.0 | PostgreSQL driver |
| APScheduler | >=3.10.0 | Background scheduler |
| pytz | >=2024.1 | Timezone handling |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| APScheduler Job과 DB 동기화 불일치 | Medium | High | Job 등록 시 트랜잭션 관리, 정기 동기화 작업 |
| 대량 스케줄로 인한 성능 저하 | Low | Medium | 인덱스 최적화, 배치 처리 |
| Timezone 처리 오류 | Medium | Medium | UTC 기준 저장, 표시 시 변환 |
| Misfire 처리 복잡성 | Medium | Low | APScheduler misfire_grace_time 활용 |

---

## Related SPECs

- SPEC-001: Database Foundation Setup (이 SPEC의 선행 조건)
- SPEC-002: User Authentication Model (user_id FK)
- SPEC-003: Workflow Domain Models (workflow_id FK)
- SPEC-005: Execution Tracking Models (트리거 연동)
- SPEC-026: APScheduler Integration (서비스 구현)
- SPEC-027: Schedule Management Service (CRUD 서비스)
- SPEC-028: Schedule UI (프론트엔드)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-13 | workflow-spec | 최초 SPEC 작성 |
