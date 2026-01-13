# SPEC-005: Execution Tracking Models

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-005 |
| Title | Execution Tracking Models |
| Created | 2026-01-12 |
| Status | Completed |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 2 - Execution Tracking Models |

## Tags

`[SPEC-005]` `[DATABASE]` `[EXECUTION]` `[WORKFLOW]` `[TRACKING]` `[BACKEND]`

---

## Overview

이 SPEC은 PasteTrader 워크플로우 엔진의 실행 추적을 위한 모델을 정의합니다. WorkflowExecution은 워크플로우 실행 인스턴스를 추적하고, NodeExecution은 개별 노드 실행 상태를 기록합니다. ExecutionLog는 실행 중 발생하는 로그를 저장합니다.

### Scope

- WorkflowExecution 모델: 워크플로우 실행 인스턴스 관리
- NodeExecution 모델: 개별 노드 실행 상태 추적
- ExecutionLog 모델: 실행 로그 저장 (선택적)
- 실행 상태 전이 및 추적

### Out of Scope

- 워크플로우 엔진 실행 로직 (SPEC-010, SPEC-011)
- 스케줄러 구현 (SPEC-008)
- 실행 API 엔드포인트 (SPEC-007)
- 실시간 모니터링 UI (별도 SPEC)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16.x | Primary database |
| SQLAlchemy | 2.0.x | Async ORM |
| asyncpg | 0.30.x | PostgreSQL async driver |
| Pydantic | 2.10.x | Schema validation |

### Configuration Dependencies

- SPEC-001에서 정의된 Base 모델 및 Mixin 사용
- SPEC-003에서 정의된 Workflow, Node 모델 참조
- `backend/app/models/enums.py`: ExecutionStatus, TriggerType enum

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| PostgreSQL JSONB로 실행 데이터 저장 가능 | High | PostgreSQL 공식 문서 | 별도 데이터 스토어 필요 |
| 단일 워크플로우 실행의 노드 수는 100개 미만 | Medium | 일반적인 워크플로우 복잡도 | 파티셔닝 또는 샤딩 필요 |
| 실행 로그는 시계열 패턴으로 조회됨 | High | 일반적인 로그 사용 패턴 | 인덱스 전략 재검토 |
| 동시 실행 인스턴스는 워크플로우당 10개 미만 | Medium | 설계 의도 | 큐잉 시스템 필요 |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| 실행 완료 후 데이터는 감사 목적으로 보존됨 | High | 데이터 정책 재정의 필요 |
| 실행 컨텍스트는 JSONB로 충분히 표현됨 | Medium | 별도 컨텍스트 테이블 필요 |
| 재시도 횟수는 노드 레벨에서 관리됨 | High | 실행 레벨 재시도 로직 추가 필요 |

---

## Requirements

### REQ-001: WorkflowExecution 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** 워크플로우 실행 인스턴스를 추적하는 WorkflowExecution 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_id | UUID | FK -> workflows(id), NOT NULL | 실행 대상 워크플로우 |
| trigger_type | TriggerType | NOT NULL | 트리거 유형 (schedule, event, manual) |
| status | ExecutionStatus | NOT NULL, DEFAULT 'pending' | 실행 상태 |
| started_at | TIMESTAMPTZ | NULL | 실행 시작 시각 |
| ended_at | TIMESTAMPTZ | NULL | 실행 종료 시각 |
| input_data | JSONB | NOT NULL, DEFAULT '{}' | 입력 데이터 |
| output_data | JSONB | NULL | 출력 데이터 |
| error_message | TEXT | NULL | 오류 메시지 |
| context | JSONB | NOT NULL, DEFAULT '{}' | 실행 컨텍스트 |
| metadata | JSONB | NOT NULL, DEFAULT '{}' | 추가 메타데이터 |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 (TimestampMixin) |
| updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 (TimestampMixin) |

### REQ-002: NodeExecution 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** 개별 노드 실행 상태를 추적하는 NodeExecution 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_execution_id | UUID | FK -> workflow_executions(id) ON DELETE CASCADE, NOT NULL | 부모 실행 인스턴스 |
| node_id | UUID | FK -> nodes(id), NOT NULL | 실행 대상 노드 |
| status | ExecutionStatus | NOT NULL, DEFAULT 'pending' | 실행 상태 |
| started_at | TIMESTAMPTZ | NULL | 실행 시작 시각 |
| ended_at | TIMESTAMPTZ | NULL | 실행 종료 시각 |
| input_data | JSONB | NOT NULL, DEFAULT '{}' | 노드 입력 데이터 |
| output_data | JSONB | NULL | 노드 출력 데이터 |
| error_message | TEXT | NULL | 오류 메시지 |
| error_traceback | TEXT | NULL | 오류 스택 트레이스 |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | 재시도 횟수 |
| execution_order | INTEGER | NOT NULL | 실행 순서 (토폴로지 정렬 기반) |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 (TimestampMixin) |
| updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 (TimestampMixin) |

### REQ-003: ExecutionLog 모델 정의 (선택적)

**Optional Requirement**

가능하면 시스템은 실행 중 발생하는 로그를 저장하는 ExecutionLog 모델을 제공합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_execution_id | UUID | FK -> workflow_executions(id) ON DELETE CASCADE, NOT NULL | 부모 실행 인스턴스 |
| node_execution_id | UUID | FK -> node_executions(id) ON DELETE CASCADE, NULL | 관련 노드 실행 (옵션) |
| level | LogLevel | NOT NULL | 로그 레벨 (debug, info, warning, error) |
| message | TEXT | NOT NULL | 로그 메시지 |
| data | JSONB | NULL | 추가 로그 데이터 |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | 로그 시각 |

### REQ-004: WorkflowExecution-NodeExecution 관계

**Event-Driven Requirement**

**WHEN** WorkflowExecution이 삭제될 때, **THEN** 해당 실행의 모든 NodeExecution과 ExecutionLog가 자동으로 삭제되어야 합니다.

**Details:**
- CASCADE 삭제로 데이터 무결성 보장
- 대량 삭제 시 성능 고려

### REQ-005: 실행 상태 전이 규칙

**State-Driven Requirement**

**IF** 실행 상태가 특정 상태이면 **THEN** 허용된 상태로만 전이할 수 있습니다.

**Status Transitions:**

| From | Allowed To |
|------|------------|
| pending | running, cancelled |
| running | completed, failed, cancelled |
| completed | (final state) |
| failed | pending (재시도 시) |
| skipped | (final state) |
| cancelled | (final state) |

### REQ-006: 실행 시간 자동 기록

**Event-Driven Requirement**

**WHEN** 실행 상태가 'running'으로 변경될 때, **THEN** started_at이 자동으로 현재 시각으로 설정되어야 합니다.

**WHEN** 실행 상태가 'completed', 'failed', 'skipped', 'cancelled'로 변경될 때, **THEN** ended_at이 자동으로 현재 시각으로 설정되어야 합니다.

### REQ-007: 노드 실행 순서 관리

**Ubiquitous Requirement**

시스템은 **항상** NodeExecution의 execution_order를 통해 노드 실행 순서를 추적해야 합니다.

**Details:**
- execution_order는 토폴로지 정렬 기반으로 설정
- 병렬 실행 노드는 동일한 execution_order를 가질 수 있음

### REQ-008: 실행 컨텍스트 관리

**Ubiquitous Requirement**

시스템은 **항상** WorkflowExecution의 context 필드를 통해 실행 컨텍스트를 관리해야 합니다.

**Context Structure:**
```json
{
  "variables": {},
  "secrets": {},
  "environment": {},
  "parent_execution_id": null,
  "retry_info": {
    "attempt": 1,
    "max_attempts": 3
  }
}
```

### REQ-009: 중복 실행 방지

**Unwanted Requirement**

시스템은 동일한 workflow_id로 'running' 상태의 실행이 동시에 존재하는 것을 **기본적으로 허용하지 않아야** 합니다.

**Details:**
- 동시 실행이 필요한 경우 metadata에 "allow_concurrent": true 설정
- 기본 동작은 단일 실행으로 제한

### REQ-010: 실행 메타데이터 관리

**Optional Requirement**

가능하면 시스템은 WorkflowExecution의 metadata 필드를 통해 추가 정보를 저장합니다.

**Metadata Structure:**
```json
{
  "triggered_by": "user_id or system",
  "schedule_id": "optional_schedule_reference",
  "priority": "normal",
  "tags": ["tag1", "tag2"],
  "allow_concurrent": false,
  "timeout_seconds": 3600
}
```

---

## Specifications

### SPEC-005-A: 파일 구조

```
backend/
  app/
    models/
      __init__.py          # 모델 exports 업데이트
      base.py              # 기존 Base, Mixins
      enums.py             # LogLevel enum 추가 (필요시)
      execution.py         # WorkflowExecution, NodeExecution, ExecutionLog (신규)
```

### SPEC-005-B: WorkflowExecution 모델 스펙

```python
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
    )
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="workflow_execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
```

### SPEC-005-C: NodeExecution 모델 스펙

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
    )
```

### SPEC-005-D: ExecutionLog 모델 스펙

```python
class LogLevel(str, Enum):
    """Log level classification."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


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

### SPEC-005-E: 인덱스 전략

```sql
-- WorkflowExecution indexes
CREATE INDEX idx_workflow_executions_workflow ON workflow_executions(workflow_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_workflow_status ON workflow_executions(workflow_id, status);
CREATE INDEX idx_workflow_executions_created ON workflow_executions(created_at DESC);
CREATE INDEX idx_workflow_executions_trigger ON workflow_executions(trigger_type, status);

-- NodeExecution indexes
CREATE INDEX idx_node_executions_workflow_execution ON node_executions(workflow_execution_id);
CREATE INDEX idx_node_executions_node ON node_executions(node_id);
CREATE INDEX idx_node_executions_status ON node_executions(status);
CREATE INDEX idx_node_executions_order ON node_executions(workflow_execution_id, execution_order);

-- ExecutionLog indexes
CREATE INDEX idx_execution_logs_workflow_execution ON execution_logs(workflow_execution_id);
CREATE INDEX idx_execution_logs_node_execution ON execution_logs(node_execution_id) WHERE node_execution_id IS NOT NULL;
CREATE INDEX idx_execution_logs_timestamp ON execution_logs(timestamp DESC);
CREATE INDEX idx_execution_logs_level ON execution_logs(level, timestamp DESC);
```

---

## Constraints

### Technical Constraints

- SPEC-001의 Base 모델 및 Mixin 사용 필수
- 모든 외래 키는 ON DELETE CASCADE 적용 (node_executions, execution_logs)
- JSONB 컬럼에 GIN 인덱스 적용
- timestamp 컬럼은 timezone-aware 필수

### Performance Constraints

- 워크플로우 실행 목록 조회 500ms 이내
- 단일 실행의 노드 실행 목록 조회 200ms 이내
- 로그 조회 (최근 1000건) 300ms 이내

### Security Constraints

- 실행 데이터는 워크플로우 소유자만 접근 가능
- context 내 secrets 필드는 조회 시 마스킹 처리
- 실행 로그에 민감 정보 저장 금지

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base 모델, Mixins, Enums
- SPEC-003: Workflow, Node 모델 (workflow_id, node_id FK)
- SPEC-002: User 모델 (간접 참조 - Workflow 소유자)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| asyncpg | >=0.30.0 | PostgreSQL driver |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 대량 실행 데이터로 인한 테이블 비대화 | High | Medium | 파티셔닝, 오래된 데이터 아카이빙 |
| 실행 로그의 급격한 증가 | High | High | 로그 레벨 필터링, TTL 정책 |
| 동시 실행 상태 갱신 충돌 | Medium | Medium | 낙관적 잠금, 상태 전이 검증 |
| JSONB 쿼리 성능 저하 | Low | Medium | GIN 인덱스, 자주 조회되는 필드 정규화 |

---

## Related SPECs

- SPEC-001: Database Foundation Setup (이 SPEC의 선행 조건)
- SPEC-003: Workflow Domain Models (workflow_id, node_id FK)
- SPEC-004: Tool & Agent Registry (NodeExecution에서 간접 참조)
- SPEC-007: Workflow API Endpoints (실행 API)
- SPEC-008: Scheduler Implementation (트리거 연동)
- SPEC-010: DAG Validation Service (실행 전 검증)
- SPEC-011: Workflow Execution Engine (실행 로직)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | 최초 SPEC 작성 |
