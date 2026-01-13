# SPEC-005: Implementation Plan

## Tags

`[SPEC-005]` `[EXECUTION]` `[WORKFLOW]` `[TRACKING]` `[BACKEND]`

---

## Implementation Overview

이 문서는 PasteTrader의 Execution Tracking Models 구현 계획을 정의합니다. WorkflowExecution, NodeExecution, ExecutionLog 모델을 구현하여 워크플로우 실행 상태를 추적합니다.

---

## Milestones

### Milestone 1: LogLevel Enum 추가 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/enums.py` - LogLevel enum 추가

**Tasks:**

1. LogLevel Enum 정의
   - debug, info, warning, error 레벨 정의
   - 기존 Enum 패턴 준수

**Technical Approach:**
```python
class LogLevel(str, Enum):
    """Execution log level classification.

    TAG: [SPEC-005] [EXECUTION] [ENUM]
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
```

---

### Milestone 2: WorkflowExecution 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/execution.py` - WorkflowExecution 모델 정의

**Tasks:**

1. WorkflowExecution 모델 클래스 생성
   - UUIDMixin, TimestampMixin 상속
   - workflow_id FK 설정 (workflows 테이블 참조)
   - trigger_type, status 필드 정의

2. 실행 시간 필드 구현
   - started_at, ended_at DateTime 필드
   - nullable=True로 설정

3. 데이터 필드 구현
   - input_data, output_data JSONB 필드
   - error_message Text 필드
   - context, metadata JSONB 필드

4. Relationship 정의
   - workflow: many-to-one relationship
   - node_executions: one-to-many relationship
   - logs: one-to-many relationship

**Technical Approach:**
```python
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ExecutionStatus, TriggerType

JSONType = JSON().with_variant(JSONB(), "postgresql")


class WorkflowExecution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[TriggerType] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default="pending",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    node_executions: Mapped[list["NodeExecution"]] = relationship(
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="NodeExecution.execution_order",
    )
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExecutionLog.timestamp",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        """Check if execution is in terminal state."""
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.CANCELLED,
        )
```

**Dependencies:** SPEC-001 완료 필수, Workflow 모델 존재

---

### Milestone 3: NodeExecution 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/execution.py` - NodeExecution 모델 추가

**Tasks:**

1. NodeExecution 모델 클래스 생성
   - UUIDMixin, TimestampMixin 상속
   - workflow_execution_id FK 설정 (CASCADE)
   - node_id FK 설정

2. 실행 상태 필드 구현
   - status, started_at, ended_at 필드
   - retry_count, execution_order 필드

3. 데이터 필드 구현
   - input_data, output_data JSONB 필드
   - error_message, error_traceback Text 필드

4. Relationship 정의
   - workflow_execution: many-to-one relationship
   - node: many-to-one relationship
   - logs: one-to-many relationship

**Technical Approach:**
```python
class NodeExecution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "node_executions"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("nodes.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default="pending",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_traceback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    execution_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Relationships
    workflow_execution: Mapped["WorkflowExecution"] = relationship(
        back_populates="node_executions"
    )
    node: Mapped["Node"] = relationship()
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="node_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExecutionLog.timestamp",
    )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate node execution duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Check if node execution can be retried."""
        if self.status != ExecutionStatus.FAILED:
            return False
        max_retries = self.node.retry_config.get("max_retries", 3) if self.node else 3
        return self.retry_count < max_retries
```

---

### Milestone 4: ExecutionLog 모델 구현 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/execution.py` - ExecutionLog 모델 추가

**Tasks:**

1. ExecutionLog 모델 클래스 생성
   - UUIDMixin 상속 (TimestampMixin 미사용)
   - workflow_execution_id FK 설정 (CASCADE)
   - node_execution_id FK 설정 (nullable, CASCADE)

2. 로그 필드 구현
   - level (LogLevel enum)
   - message (Text)
   - data (JSONB, nullable)
   - timestamp (DateTime)

3. Relationship 정의
   - workflow_execution: many-to-one
   - node_execution: many-to-one (nullable)

**Technical Approach:**
```python
class ExecutionLog(UUIDMixin, Base):
    __tablename__ = "execution_logs"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("node_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    level: Mapped[LogLevel] = mapped_column(
        String(20),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    workflow_execution: Mapped["WorkflowExecution"] = relationship(
        back_populates="logs"
    )
    node_execution: Mapped["NodeExecution | None"] = relationship(
        back_populates="logs"
    )
```

---

### Milestone 5: Workflow 모델 관계 업데이트 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/workflow.py` - executions relationship 추가

**Tasks:**

1. Workflow 모델에 executions relationship 추가
   - back_populates="workflow" 설정
   - lazy loading 기본

**Technical Approach:**
```python
# workflow.py 업데이트
class Workflow(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    # ... 기존 필드 ...

    # New relationship
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        passive_deletes=True,
    )
```

---

### Milestone 6: 모듈 통합 및 Export (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/__init__.py` 업데이트
- `backend/app/models/enums.py` 업데이트

**Tasks:**

1. __init__.py 업데이트
   - WorkflowExecution, NodeExecution, ExecutionLog 모델 export
   - LogLevel enum export
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
    ToolType,
    TriggerType,
)
from app.models.agent import Agent
from app.models.execution import ExecutionLog, NodeExecution, WorkflowExecution
from app.models.tool import Tool
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
    # Models
    "Tool",
    "Agent",
    "Workflow",
    "Node",
    "Edge",
    "WorkflowExecution",
    "NodeExecution",
    "ExecutionLog",
]
```

---

### Milestone 7: Alembic 마이그레이션 생성 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/alembic/versions/xxx_add_execution_models.py`

**Tasks:**

1. 마이그레이션 자동 생성
   - `alembic revision --autogenerate -m "add execution tracking models"`
   - 생성된 파일 검토 및 수정

2. 인덱스 추가 확인
   - idx_workflow_executions_workflow
   - idx_workflow_executions_status
   - idx_workflow_executions_workflow_status
   - idx_workflow_executions_created
   - idx_node_executions_workflow_execution
   - idx_node_executions_node
   - idx_node_executions_status
   - idx_node_executions_order
   - idx_execution_logs_workflow_execution
   - idx_execution_logs_node_execution
   - idx_execution_logs_timestamp
   - idx_execution_logs_level

3. 마이그레이션 테스트
   - upgrade 테스트
   - downgrade 테스트

---

### Milestone 8: 테스트 작성 (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/tests/unit/test_models/test_execution.py`
- `backend/tests/integration/test_models/test_execution_integration.py`

**Tasks:**

1. 단위 테스트 작성
   - WorkflowExecution 모델 생성 테스트
   - NodeExecution 모델 생성 테스트
   - ExecutionLog 모델 생성 테스트
   - Status 전이 테스트
   - Mixin 동작 테스트

2. 관계 테스트 작성
   - WorkflowExecution-NodeExecution 관계 테스트
   - WorkflowExecution-ExecutionLog 관계 테스트
   - NodeExecution-ExecutionLog 관계 테스트
   - Workflow-WorkflowExecution 관계 테스트

3. CASCADE 삭제 테스트 작성
   - WorkflowExecution 삭제 시 NodeExecution 삭제 확인
   - WorkflowExecution 삭제 시 ExecutionLog 삭제 확인

4. 통합 테스트 작성
   - 전체 실행 흐름 테스트
   - 상태 전이 시나리오 테스트
   - 성능 테스트 (대량 로그 조회)

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    models/
      __init__.py          # exports: WorkflowExecution, NodeExecution, ExecutionLog
      base.py              # Base, Mixins (기존)
      enums.py             # ExecutionStatus, TriggerType, LogLevel (업데이트)
      workflow.py          # Workflow, Node, Edge (기존, 관계 추가)
      execution.py         # WorkflowExecution, NodeExecution, ExecutionLog (신규)
  alembic/
    versions/
      xxx_add_execution_models.py  # 마이그레이션 (신규)
  tests/
    unit/
      test_models/
        test_execution.py          # 단위 테스트 (신규)
    integration/
      test_models/
        test_execution_integration.py  # 통합 테스트 (신규)
```

### Data Flow Diagram

```
Workflow
    |
    | 1
    |
    | N
    v
WorkflowExecution
    |
    +------------------+
    |                  |
    | 1                | 1
    |                  |
    | N                | N
    v                  v
NodeExecution     ExecutionLog
    |                  ^
    | 1                |
    |                  |
    | N                |
    +------------------+
```

### Entity Relationship Diagram

```
                 ┌─────────────┐
                 │  workflows  │
                 └──────┬──────┘
                        │ 1
                        │
                        │ *
         ┌──────────────▼──────────────┐
         │    workflow_executions      │
         │  - id (UUID PK)             │
         │  - workflow_id (FK)         │
         │  - trigger_type             │
         │  - status                   │
         │  - started_at               │
         │  - ended_at                 │
         │  - input_data (JSONB)       │
         │  - output_data (JSONB)      │
         │  - error_message            │
         │  - context (JSONB)          │
         │  - metadata (JSONB)         │
         └──────────────┬──────────────┘
                        │ 1
           ┌────────────┼────────────┐
           │ *          │            │ *
    ┌──────▼──────┐     │     ┌──────▼──────┐
    │node_executions│   │     │execution_logs│
    │  - id (UUID)│    │     │  - id (UUID)│
    │  - workflow_│    │     │  - workflow_│
    │    execution_id│ │     │    execution_id│
    │  - node_id  │    │     │  - node_    │
    │  - status   │    │     │    execution_id│
    │  - started_at│   │     │  - level    │
    │  - ended_at │    │     │  - message  │
    │  - input_data│   │     │  - data     │
    │  - output_data│  │     │  - timestamp│
    │  - error_*  │    │     └─────────────┘
    │  - retry_count│  │
    │  - execution_│   │
    │    order    │    │
    └──────┬──────┘    │
           │ 1         │
           │           │
           │ *         │
    ┌──────▼──────┐    │
    │execution_logs│   │
    │  (node level)│◄──┘
    └─────────────┘
```

---

## Technical Approach

### Context JSONB 구조

**WorkflowExecution Context 예시:**
```json
{
  "variables": {
    "market": "KOSPI",
    "threshold": 0.05
  },
  "secrets": {
    "api_key": "***masked***"
  },
  "environment": {
    "mode": "production",
    "region": "ap-northeast-2"
  },
  "parent_execution_id": null,
  "retry_info": {
    "attempt": 1,
    "max_attempts": 3
  }
}
```

### Metadata JSONB 구조

**WorkflowExecution Metadata 예시:**
```json
{
  "triggered_by": "user_12345",
  "schedule_id": "schedule_789",
  "priority": "high",
  "tags": ["backtest", "momentum"],
  "allow_concurrent": false,
  "timeout_seconds": 3600,
  "correlation_id": "req_abc123"
}
```

### 상태 전이 헬퍼 메서드

```python
class WorkflowExecution(UUIDMixin, TimestampMixin, Base):
    # ... 기존 필드 ...

    def start(self) -> None:
        """Mark execution as running."""
        if self.status != ExecutionStatus.PENDING:
            raise ValueError(f"Cannot start execution in {self.status} state")
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self, output_data: dict | None = None) -> None:
        """Mark execution as completed."""
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Cannot complete execution in {self.status} state")
        self.status = ExecutionStatus.COMPLETED
        self.ended_at = datetime.now(UTC)
        if output_data:
            self.output_data = output_data

    def fail(self, error_message: str) -> None:
        """Mark execution as failed."""
        if self.status != ExecutionStatus.RUNNING:
            raise ValueError(f"Cannot fail execution in {self.status} state")
        self.status = ExecutionStatus.FAILED
        self.ended_at = datetime.now(UTC)
        self.error_message = error_message

    def cancel(self) -> None:
        """Cancel the execution."""
        if self.status not in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
            raise ValueError(f"Cannot cancel execution in {self.status} state")
        self.status = ExecutionStatus.CANCELLED
        self.ended_at = datetime.now(UTC)
```

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| 대량 실행 데이터 | 테이블 파티셔닝 (created_at 기준), 아카이빙 정책 |
| 로그 급격한 증가 | TTL 정책, 로그 레벨 필터링, 비동기 로깅 |
| 동시 상태 갱신 충돌 | 낙관적 잠금 (version), SELECT FOR UPDATE |
| JSONB 쿼리 성능 | GIN 인덱스, 자주 사용되는 필드 정규화 |

---

## Output Files Summary

| File Path | Purpose |
|-----------|---------|
| `backend/app/models/enums.py` | LogLevel enum 추가 |
| `backend/app/models/execution.py` | WorkflowExecution, NodeExecution, ExecutionLog 모델 정의 |
| `backend/app/models/workflow.py` | executions relationship 추가 |
| `backend/app/models/__init__.py` | 모델 export 업데이트 |
| `backend/alembic/versions/xxx_add_execution_models.py` | 마이그레이션 파일 |
| `backend/tests/unit/test_models/test_execution.py` | 단위 테스트 |
| `backend/tests/integration/test_models/test_execution_integration.py` | 통합 테스트 |

---

## Definition of Done

- [ ] LogLevel enum 추가 완료
- [ ] WorkflowExecution, NodeExecution, ExecutionLog 모델 구현 완료
- [ ] Workflow 모델에 executions relationship 추가
- [ ] 모든 relationship 정상 동작
- [ ] CASCADE 삭제 정상 동작
- [ ] 상태 전이 헬퍼 메서드 구현
- [ ] Alembic 마이그레이션 성공
- [ ] 단위 테스트 85%+ 커버리지
- [ ] 통합 테스트 통과
- [ ] ruff 린팅 에러 없음
- [ ] mypy 타입 체크 통과
- [ ] 코드 리뷰 승인

---

## Next Steps After Completion

1. **SPEC-007**: Workflow API Endpoints 구현 (실행 API 포함)
2. **SPEC-008**: Scheduler Implementation (스케줄 기반 트리거)
3. **SPEC-010**: DAG Validation Service 구현
4. **SPEC-011**: Workflow Execution Engine 구현

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [acceptance.md](acceptance.md) - 인수 조건
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | 최초 구현 계획 작성 |
