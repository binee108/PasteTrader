# SPEC-003: Workflow Domain Models

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-003 |
| Title | Workflow Domain Models |
| Created | 2026-01-11 |
| Status | Completed |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 1 - Workflow Core Models |

## Tags

`[SPEC-003]` `[WORKFLOW]` `[NODE]` `[EDGE]` `[DAG]` `[BACKEND]`

---

## Overview

이 SPEC은 PasteTrader의 DAG 기반 워크플로우 정의를 위한 핵심 도메인 모델을 정의합니다. Workflow, Node, Edge 모델은 워크플로우 엔진의 기초가 되며, 시각적 워크플로우 편집기와 실행 엔진 모두에서 사용됩니다.

### Scope

- Workflow 모델: DAG 정의를 담는 최상위 컨테이너
- Node 모델: 6가지 타입의 워크플로우 노드 (trigger, tool, agent, condition, adapter, aggregator)
- Edge 모델: 노드 간 연결 및 조건부 분기 지원

### Out of Scope

- Tool 및 Agent 레지스트리 모델 (SPEC-004)
- 워크플로우 실행 모델 (SPEC-005)
- API 엔드포인트 (SPEC-007)
- 워크플로우 엔진 구현 (SPEC-010, SPEC-011)

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
- `backend/app/models/base.py`: UUIDMixin, TimestampMixin, SoftDeleteMixin
- `backend/app/models/enums.py`: NodeType enum

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| PostgreSQL JSONB로 유연한 config 저장 가능 | High | PostgreSQL 공식 문서 | 스키마 변경 필요 |
| CASCADE 삭제로 참조 무결성 유지 | High | SQLAlchemy 표준 패턴 | 수동 정리 로직 필요 |
| Float으로 position 저장이 UI 정밀도 충족 | Medium | React Flow 기본 동작 | Decimal 타입 전환 |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| 워크플로우당 노드 수는 100개 미만 | Medium | 성능 최적화 필요 |
| 동시 편집은 낙관적 잠금으로 충분 | Medium | 실시간 협업 기능 추가 필요 |
| Node 타입은 6가지로 충분 | Medium | 확장 시 Enum 업데이트 |

---

## Requirements

### REQ-001: Workflow 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** DAG 기반 워크플로우를 정의할 수 있는 Workflow 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| owner_id | UUID | FK → users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 워크플로우 이름 |
| description | TEXT | NULL | 설명 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 전역 설정 |
| variables | JSONB | NOT NULL, DEFAULT '{}' | 워크플로우 변수 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 실행 가능 여부 |
| version | INTEGER | NOT NULL, DEFAULT 1 | 낙관적 잠금용 버전 |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 (TimestampMixin) |
| updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 (TimestampMixin) |
| deleted_at | TIMESTAMPTZ | NULL | 삭제 시각 (SoftDeleteMixin) |

### REQ-002: Node 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** 6가지 타입의 워크플로우 노드를 정의할 수 있는 Node 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_id | UUID | FK → workflows(id) ON DELETE CASCADE, NOT NULL | 부모 워크플로우 |
| name | VARCHAR(255) | NOT NULL | 노드 이름 |
| node_type | NodeType | NOT NULL | 노드 타입 (6가지) |
| position_x | FLOAT | NOT NULL, DEFAULT 0 | UI X 좌표 |
| position_y | FLOAT | NOT NULL, DEFAULT 0 | UI Y 좌표 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 노드별 설정 |
| input_schema | JSONB | NULL | 입력 JSON Schema |
| output_schema | JSONB | NULL | 출력 JSON Schema |
| tool_id | UUID | FK → tools(id), NULL | 연결된 도구 (tool 타입용) |
| agent_id | UUID | FK → agents(id), NULL | 연결된 에이전트 (agent 타입용) |
| timeout_seconds | INTEGER | NOT NULL, DEFAULT 300 | 실행 타임아웃 |
| retry_config | JSONB | NOT NULL, DEFAULT '{"max_retries": 3, "delay": 1}' | 재시도 설정 |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 |
| updated_at | TIMESTAMPTZ | NOT NULL | 수정 시각 |

**Node Types (6가지):**

| Type | Description | Required Fields |
|------|-------------|-----------------|
| trigger | 워크플로우 시작점 | config.trigger_type |
| tool | 외부 도구 실행 | tool_id |
| agent | LLM 에이전트 호출 | agent_id |
| condition | 조건부 분기 | config.condition_expression |
| adapter | 데이터 변환 | config.transform_script |
| aggregator | 결과 집계 | config.aggregation_type |

### REQ-003: Edge 모델 정의

**Ubiquitous Requirement**

시스템은 **항상** 노드 간 연결을 정의하는 Edge 모델을 제공해야 합니다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 (UUIDMixin) |
| workflow_id | UUID | FK → workflows(id) ON DELETE CASCADE, NOT NULL | 부모 워크플로우 |
| source_node_id | UUID | FK → nodes(id) ON DELETE CASCADE, NOT NULL | 출발 노드 |
| target_node_id | UUID | FK → nodes(id) ON DELETE CASCADE, NOT NULL | 도착 노드 |
| source_handle | VARCHAR(50) | NULL | 출발 연결점 (다중 출력용) |
| target_handle | VARCHAR(50) | NULL | 도착 연결점 (다중 입력용) |
| condition | JSONB | NULL | 조건식 (condition 노드 분기용) |
| priority | INTEGER | NOT NULL, DEFAULT 0 | 실행 우선순위 |
| label | VARCHAR(100) | NULL | UI 라벨 |
| created_at | TIMESTAMPTZ | NOT NULL | 생성 시각 |

### REQ-004: 워크플로우-노드 관계

**Event-Driven Requirement**

**WHEN** 워크플로우가 삭제될 때, **THEN** 해당 워크플로우의 모든 노드와 엣지가 자동으로 삭제되어야 합니다.

**Details:**
- CASCADE 삭제로 데이터 무결성 보장
- Soft delete 시에도 관계 유지
- 노드 삭제 시 연결된 엣지도 삭제

### REQ-005: 노드-엣지 관계

**Event-Driven Requirement**

**WHEN** 노드가 삭제될 때, **THEN** 해당 노드와 연결된 모든 엣지가 자동으로 삭제되어야 합니다.

**Details:**
- source_node_id 또는 target_node_id가 삭제된 노드를 참조하는 엣지 제거
- CASCADE 삭제로 구현

### REQ-006: 낙관적 잠금 지원

**Event-Driven Requirement**

**WHEN** 워크플로우가 업데이트될 때, **THEN** version 컬럼이 자동으로 증가해야 합니다.

**Details:**
- 동시 편집 감지용 version 필드
- 업데이트 시 version 검증
- 충돌 시 StaleDataError 발생

### REQ-007: 엣지 유일성 제약

**Unwanted Requirement**

시스템은 동일한 source_node_id, target_node_id, source_handle, target_handle 조합의 엣지를 **중복 생성하지 않아야** 합니다.

**Details:**
- UNIQUE 제약으로 중복 방지
- handle이 NULL인 경우도 고려

### REQ-008: Node 타입별 필수 필드 검증

**State-Driven Requirement**

**IF** 노드 타입이 tool이면 **THEN** tool_id가 반드시 설정되어야 합니다.
**IF** 노드 타입이 agent이면 **THEN** agent_id가 반드시 설정되어야 합니다.

**Details:**
- 애플리케이션 레벨 검증
- 데이터베이스 CHECK 제약 또는 트리거로 강화 가능

### REQ-009: 자기 참조 엣지 방지

**Unwanted Requirement**

시스템은 source_node_id와 target_node_id가 동일한 엣지를 **생성하지 않아야** 합니다.

**Details:**
- CHECK 제약으로 self-loop 방지
- 사이클 검증은 애플리케이션 레벨에서 수행

---

## Specifications

### SPEC-003-A: 파일 구조

```
backend/
  app/
    models/
      __init__.py          # 모델 exports 업데이트
      base.py              # 기존 Base, Mixins
      enums.py             # 기존 + 필요시 추가 Enum
      workflow.py          # Workflow, Node, Edge 모델 (신규)
```

### SPEC-003-B: Workflow 모델 스펙

```python
class Workflow(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflows"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    variables: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    nodes: Mapped[list["Node"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[list["Edge"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
```

### SPEC-003-C: Node 모델 스펙

```python
class Node(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "nodes"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(
        SQLAlchemyEnum(NodeType, name="node_type_enum"),
        nullable=False,
    )
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tools.id"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id"),
        nullable=True,
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    retry_config: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"max_retries": 3, "delay": 1},
        server_default='{"max_retries": 3, "delay": 1}',
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="nodes")
```

### SPEC-003-D: Edge 모델 스펙

```python
class Edge(Base, UUIDMixin):
    __tablename__ = "edges"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_handle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_handle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="edges")
    source_node: Mapped["Node"] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped["Node"] = relationship(foreign_keys=[target_node_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "source_node_id", "target_node_id", "source_handle", "target_handle",
            name="uq_edge_connection",
        ),
        CheckConstraint(
            "source_node_id != target_node_id",
            name="ck_no_self_loop",
        ),
    )
```

### SPEC-003-E: 인덱스 전략

```sql
-- Workflow indexes
CREATE INDEX idx_workflows_owner ON workflows(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_workflows_owner_active ON workflows(owner_id, is_active) WHERE deleted_at IS NULL;

-- Node indexes
CREATE INDEX idx_nodes_workflow ON nodes(workflow_id);
CREATE INDEX idx_nodes_type ON nodes(workflow_id, node_type);

-- Edge indexes
CREATE INDEX idx_edges_workflow ON edges(workflow_id);
CREATE INDEX idx_edges_source ON edges(source_node_id);
CREATE INDEX idx_edges_target ON edges(target_node_id);
```

---

## Constraints

### Technical Constraints

- SPEC-001의 Base 모델 및 Mixin 사용 필수
- 모든 외래 키는 ON DELETE CASCADE 적용 (nodes, edges)
- JSONB 컬럼에 GIN 인덱스 적용

### Performance Constraints

- 워크플로우 조회 시 노드/엣지 lazy loading 기본
- 100개 노드 워크플로우 조회 500ms 이내

### Security Constraints

- owner_id를 통한 접근 제어 필수
- Soft delete로 데이터 복구 가능성 유지

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base 모델, Mixins, Enums
- SPEC-002: User 모델 (owner_id FK)
- SPEC-004: Tool, Agent 모델 (tool_id, agent_id FK) - 선택적

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| asyncpg | >=0.30.0 | PostgreSQL driver |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 복잡한 관계로 인한 쿼리 성능 저하 | Medium | Medium | 적절한 인덱싱, lazy loading |
| JSONB 스키마 변경 관리 어려움 | Medium | Low | JSON Schema 검증, 마이그레이션 스크립트 |
| 동시 편집 충돌 | Medium | Medium | 낙관적 잠금, 프론트엔드 알림 |

---

## Related SPECs

- SPEC-001: Database Foundation Setup (이 SPEC의 선행 조건)
- SPEC-002: User Authentication Model (owner_id FK)
- SPEC-004: Tool & Agent Registry (tool_id, agent_id FK)
- SPEC-005: Execution Tracking Models (workflow_id FK)
- SPEC-010: DAG Validation Service (이 모델 사용)
- SPEC-011: Workflow Execution Engine (이 모델 사용)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-11 | workflow-spec | 최초 SPEC 작성 |
| 2.0.0 | 2026-01-13 | manager-tdd | TDD 구현 완료 - 105개 테스트 통과, 100% 커버리지, Git 커밋 8c3f2e1 |
