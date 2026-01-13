# SPEC-006: Implementation Plan

## Tags

`[SPEC-006]` `[SCHEDULE]` `[WORKFLOW]` `[APSCHEDULER]` `[BACKEND]`

---

## Implementation Overview

이 문서는 PasteTrader의 Schedule Configuration Model 구현 계획을 정의합니다. Schedule 모델과 ScheduleType enum을 구현하여 APScheduler 기반 워크플로우 예약 실행을 지원합니다.

---

## Milestones

### Milestone 1: ScheduleType Enum 추가 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/enums.py` - ScheduleType enum 추가

**Tasks:**

1. ScheduleType Enum 정의
   - cron, interval, date 유형 정의
   - 기존 Enum 패턴 준수

**Technical Approach:**
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

---

### Milestone 2: Schedule 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/schedule.py` - Schedule 모델 정의

**Tasks:**

1. Schedule 모델 클래스 생성
   - UUIDMixin, TimestampMixin, SoftDeleteMixin 상속
   - workflow_id FK 설정 (workflows 테이블 참조)
   - user_id FK 설정 (users 테이블 참조)

2. 스케줄 설정 필드 구현
   - name, description 필드
   - schedule_type, schedule_config JSONB 필드
   - timezone 필드

3. 실행 관리 필드 구현
   - is_active Boolean 필드
   - job_id (APScheduler Job 연동)
   - next_run_at, last_run_at DateTime 필드
   - run_count Integer 필드
   - metadata JSONB 필드

4. Relationship 정의
   - workflow: many-to-one relationship
   - user: many-to-one relationship

**Technical Approach:**
```python
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ScheduleType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workflow import Workflow

JSONType = JSON().with_variant(JSONB(), "postgresql")


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
            if self.last_run_at:
                return True
        end_date = self.schedule_config.get("end_date")
        if end_date:
            return datetime.now(UTC) > datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        return False

    def record_execution(self) -> None:
        """Record a schedule execution."""
        self.last_run_at = datetime.now(UTC)
        self.run_count += 1

    def activate(self) -> None:
        """Activate the schedule."""
        if self.is_expired:
            raise ValueError("Cannot activate an expired schedule")
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the schedule."""
        self.is_active = False
        self.next_run_at = None
```

**Dependencies:** SPEC-001 완료 필수, Workflow 및 User 모델 존재

---

### Milestone 3: Workflow 모델 관계 업데이트 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/workflow.py` - schedules relationship 추가

**Tasks:**

1. Workflow 모델에 schedules relationship 추가
   - back_populates="workflow" 설정
   - passive_deletes=True (Soft Delete 연동)

**Technical Approach:**
```python
# workflow.py 업데이트
class Workflow(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    # ... 기존 필드 ...

    # New relationship
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="workflow",
        passive_deletes=True,
    )
```

---

### Milestone 4: User 모델 관계 업데이트 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/user.py` - schedules relationship 추가

**Tasks:**

1. User 모델에 schedules relationship 추가
   - back_populates="user" 설정

**Technical Approach:**
```python
# user.py 업데이트
class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    # ... 기존 필드 ...

    # New relationship
    schedules: Mapped[list["Schedule"]] = relationship(
        "Schedule",
        back_populates="user",
        passive_deletes=True,
    )
```

---

### Milestone 5: 모듈 통합 및 Export (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/__init__.py` 업데이트
- `backend/app/models/enums.py` 업데이트

**Tasks:**

1. __init__.py 업데이트
   - Schedule 모델 export
   - ScheduleType enum export
   - __all__ 리스트 업데이트

2. Forward Reference 해결
   - TYPE_CHECKING 블록으로 순환 import 방지

**Technical Approach:**
```python
# backend/app/models/__init__.py
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import (
    AuthMode,
    ExecutionStatus,
    LogLevel,
    ModelProvider,
    NodeType,
    ScheduleType,
    ToolType,
    TriggerType,
)
from app.models.agent import Agent
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.models.schedule import Schedule
from app.models.tool import Tool
from app.models.user import User
from app.models.workflow import Edge, Node, Workflow

__all__ = [
    # Base classes
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Enums
    "NodeType",
    "ToolType",
    "ModelProvider",
    "ExecutionStatus",
    "AuthMode",
    "TriggerType",
    "LogLevel",
    "ScheduleType",
    # Models
    "User",
    "Tool",
    "Agent",
    "Workflow",
    "Node",
    "Edge",
    "WorkflowExecution",
    "NodeExecution",
    "ExecutionLog",
    "Schedule",
]
```

---

### Milestone 6: Alembic 마이그레이션 생성 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/alembic/versions/xxx_add_schedule_model.py`

**Tasks:**

1. 마이그레이션 자동 생성
   - `alembic revision --autogenerate -m "add schedule model"`
   - 생성된 파일 검토 및 수정

2. 인덱스 추가 확인
   - idx_schedules_workflow
   - idx_schedules_user
   - idx_schedules_type
   - idx_schedules_active
   - idx_schedules_next_run
   - idx_schedules_job_id
   - idx_schedules_workflow_active
   - idx_schedules_not_deleted

3. 마이그레이션 테스트
   - upgrade 테스트
   - downgrade 테스트

---

### Milestone 7: 테스트 작성 (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/tests/unit/test_models/test_schedule.py`
- `backend/tests/integration/test_models/test_schedule_integration.py`

**Tasks:**

1. 단위 테스트 작성
   - Schedule 모델 생성 테스트
   - ScheduleType enum 테스트
   - schedule_config 유효성 테스트
   - Mixin 동작 테스트

2. 관계 테스트 작성
   - Workflow-Schedule 관계 테스트
   - User-Schedule 관계 테스트
   - Soft Delete 동작 테스트

3. 속성 테스트 작성
   - is_one_time 테스트
   - is_recurring 테스트
   - is_expired 테스트
   - record_execution 테스트
   - activate/deactivate 테스트

4. 통합 테스트 작성
   - 전체 스케줄 생성 흐름 테스트
   - 스케줄 유형별 config 검증 테스트

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    models/
      __init__.py          # exports: Schedule, ScheduleType
      base.py              # Base, Mixins (기존)
      enums.py             # ScheduleType 추가 (업데이트)
      user.py              # User 모델 (관계 추가)
      workflow.py          # Workflow 모델 (관계 추가)
      schedule.py          # Schedule 모델 (신규)
  alembic/
    versions/
      xxx_add_schedule_model.py  # 마이그레이션 (신규)
  tests/
    unit/
      test_models/
        test_schedule.py         # 단위 테스트 (신규)
    integration/
      test_models/
        test_schedule_integration.py  # 통합 테스트 (신규)
```

### Data Flow Diagram

```
User
  |
  | 1
  |
  | N
  v
Schedule <-------> Workflow
  |                    |
  | 1                  | 1
  |                    |
  | trigger            | N
  v                    v
APScheduler -----> WorkflowExecution
  Job                  |
                       | 1
                       |
                       | N
                       v
                 NodeExecution
```

### Entity Relationship Diagram

```
                  ┌─────────────┐
                  │   users     │
                  └──────┬──────┘
                         │ 1
                         │
                         │ *
          ┌──────────────▼──────────────┐
          │         schedules           │
          │  - id (UUID PK)             │
          │  - workflow_id (FK)         │
          │  - user_id (FK)             │
          │  - name                     │
          │  - description              │
          │  - schedule_type            │
          │  - schedule_config (JSONB)  │
          │  - timezone                 │
          │  - is_active                │
          │  - job_id (UNIQUE)          │
          │  - next_run_at              │
          │  - last_run_at              │
          │  - run_count                │
          │  - metadata (JSONB)         │
          │  - deleted_at               │
          └──────────────┬──────────────┘
                         │ *
                         │
                         │ 1
                  ┌──────▼──────┐
                  │  workflows  │
                  └─────────────┘
```

---

## Technical Approach

### Schedule Config 스키마 예시

**Cron Schedule Config 예시:**
```json
{
  "cron_expression": "0 9 * * 1-5",
  "hour": 9,
  "minute": 0,
  "second": 0,
  "day_of_week": "mon-fri",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z"
}
```

**Interval Schedule Config 예시:**
```json
{
  "hours": 1,
  "minutes": 0,
  "seconds": 0,
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": null
}
```

**Date Schedule Config 예시:**
```json
{
  "run_date": "2026-06-15T10:30:00Z"
}
```

### Metadata 구조 예시

```json
{
  "priority": "high",
  "tags": ["daily", "market-open", "kospi"],
  "notification": {
    "on_success": false,
    "on_failure": true,
    "channels": ["slack"]
  },
  "max_instances": 1,
  "coalesce": true,
  "misfire_grace_time": 60
}
```

### APScheduler Job ID 생성 전략

```python
def generate_job_id(schedule_id: uuid.UUID) -> str:
    """Generate unique APScheduler job ID."""
    return f"schedule_{schedule_id}"
```

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| APScheduler Job 동기화 불일치 | 트랜잭션 관리, 정기 동기화 배치 작업 |
| Timezone 처리 오류 | UTC 기준 저장, pytz 라이브러리 활용 |
| Cron 표현식 파싱 오류 | croniter 라이브러리로 사전 검증 |
| 대량 스케줄 성능 저하 | 인덱스 최적화, 페이지네이션 |

---

## Output Files Summary

| File Path | Purpose |
|-----------|---------|
| `backend/app/models/enums.py` | ScheduleType enum 추가 |
| `backend/app/models/schedule.py` | Schedule 모델 정의 |
| `backend/app/models/workflow.py` | schedules relationship 추가 |
| `backend/app/models/user.py` | schedules relationship 추가 |
| `backend/app/models/__init__.py` | 모델 export 업데이트 |
| `backend/alembic/versions/xxx_add_schedule_model.py` | 마이그레이션 파일 |
| `backend/tests/unit/test_models/test_schedule.py` | 단위 테스트 |
| `backend/tests/integration/test_models/test_schedule_integration.py` | 통합 테스트 |

---

## Definition of Done

- [ ] ScheduleType enum 추가 완료
- [ ] Schedule 모델 구현 완료
- [ ] Workflow 모델에 schedules relationship 추가
- [ ] User 모델에 schedules relationship 추가
- [ ] 모든 relationship 정상 동작
- [ ] Soft Delete 정상 동작
- [ ] 속성 메서드 구현 (is_one_time, is_recurring, is_expired)
- [ ] Alembic 마이그레이션 성공
- [ ] 단위 테스트 85%+ 커버리지
- [ ] 통합 테스트 통과
- [ ] ruff 린팅 에러 없음
- [ ] mypy 타입 체크 통과
- [ ] 코드 리뷰 승인

---

## Next Steps After Completion

1. **SPEC-026**: APScheduler Integration 서비스 구현
2. **SPEC-027**: Schedule Management Service (CRUD 서비스)
3. **SPEC-028**: Schedule UI 컴포넌트
4. **SPEC-007**: Workflow API Endpoints (Schedule API 포함)

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [acceptance.md](acceptance.md) - 인수 조건
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models
- [SPEC-005/spec.md](../SPEC-005/spec.md) - Execution Tracking Models

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-13 | workflow-spec | 최초 구현 계획 작성 |
