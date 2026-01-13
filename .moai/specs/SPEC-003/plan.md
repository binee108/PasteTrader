# SPEC-003: Implementation Plan

## Tags

`[SPEC-003]` `[WORKFLOW]` `[NODE]` `[EDGE]` `[DAG]` `[BACKEND]`

---

## Implementation Overview

이 문서는 PasteTrader의 Workflow Domain Models 구현 계획을 정의합니다. DAG 기반 워크플로우 정의를 위한 핵심 모델(Workflow, Node, Edge)을 구현합니다.

---

## Milestones

### Milestone 1: Workflow 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/workflow.py` - Workflow 모델 정의

**Tasks:**

1. Workflow 모델 클래스 생성
   - UUIDMixin, TimestampMixin, SoftDeleteMixin 상속
   - owner_id FK 설정 (users 테이블 참조)
   - name, description 필드 정의
   - config, variables JSONB 필드 정의

2. 낙관적 잠금 구현
   - version 컬럼 추가
   - 업데이트 시 version 증가 로직

3. is_active 플래그 구현
   - 워크플로우 활성화/비활성화 지원
   - 쿼리 필터 헬퍼 메서드

4. Relationship 정의
   - nodes: one-to-many relationship
   - edges: one-to-many relationship
   - cascade="all, delete-orphan" 설정

**Technical Approach:**
```python
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Workflow(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workflows"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    variables: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    nodes: Mapped[list["Node"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    edges: Mapped[list["Edge"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
```

**Dependencies:** SPEC-001 완료 필수, User 모델 존재

---

### Milestone 2: Node 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/workflow.py` - Node 모델 추가

**Tasks:**

1. Node 모델 클래스 생성
   - UUIDMixin, TimestampMixin 상속 (SoftDeleteMixin 제외 - CASCADE 삭제)
   - workflow_id FK 설정 (CASCADE)
   - node_type enum 필드

2. UI 관련 필드 구현
   - position_x, position_y Float 필드
   - React Flow 호환성 확보

3. Node 설정 필드 구현
   - config JSONB 필드
   - input_schema, output_schema JSONB 필드
   - timeout_seconds, retry_config 필드

4. 외래 키 참조 필드 구현
   - tool_id FK (nullable, tools 테이블)
   - agent_id FK (nullable, agents 테이블)

5. Relationship 정의
   - workflow: many-to-one relationship
   - outgoing_edges, incoming_edges: 양방향 엣지 관계

**Technical Approach:**
```python
from sqlalchemy import CheckConstraint, Enum as SQLAlchemyEnum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

class Node(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "nodes"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(
        SQLAlchemyEnum(NodeType, name="node_type_enum", create_type=True),
        nullable=False,
    )
    position_x: Mapped[float] = mapped_column(Float, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tools.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
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

---

### Milestone 3: Edge 모델 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/workflow.py` - Edge 모델 추가

**Tasks:**

1. Edge 모델 클래스 생성
   - UUIDMixin 상속 (TimestampMixin 일부만 - created_at만)
   - workflow_id, source_node_id, target_node_id FK 설정

2. Handle 필드 구현
   - source_handle, target_handle nullable 문자열
   - 다중 출력/입력 연결점 지원

3. 조건 및 우선순위 필드 구현
   - condition JSONB 필드 (조건부 분기)
   - priority 정수 필드 (실행 순서)
   - label 문자열 필드 (UI 표시용)

4. 제약 조건 구현
   - UniqueConstraint: 연결 중복 방지
   - CheckConstraint: 자기 참조 방지

5. Relationship 정의
   - workflow: many-to-one
   - source_node, target_node: 노드 참조

**Technical Approach:**
```python
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

class Edge(Base, UUIDMixin):
    __tablename__ = "edges"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
        nullable=False,
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="edges")
    source_node: Mapped["Node"] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped["Node"] = relationship(foreign_keys=[target_node_id])

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

---

### Milestone 4: 모듈 통합 및 Export (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/__init__.py` 업데이트
- 타입 힌트 정리

**Tasks:**

1. __init__.py 업데이트
   - Workflow, Node, Edge 모델 export
   - __all__ 리스트 업데이트

2. Forward Reference 해결
   - TYPE_CHECKING 블록으로 순환 import 방지
   - relationship의 문자열 참조 확인

3. 타입 힌트 검증
   - mypy 통과 확인
   - Mapped 타입 일관성 확인

**Technical Approach:**
```python
# backend/app/models/__init__.py
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ExecutionStatus, ModelProvider, NodeType, ToolType
from app.models.workflow import Edge, Node, Workflow

__all__ = [
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Enums
    "NodeType",
    "ToolType",
    "ModelProvider",
    "ExecutionStatus",
    # Workflow Models
    "Workflow",
    "Node",
    "Edge",
]
```

---

### Milestone 5: Alembic 마이그레이션 생성 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/alembic/versions/xxx_add_workflow_models.py`

**Tasks:**

1. 마이그레이션 자동 생성
   - `alembic revision --autogenerate -m "add workflow models"`
   - 생성된 파일 검토 및 수정

2. 인덱스 추가 확인
   - idx_workflows_owner
   - idx_workflows_owner_active
   - idx_nodes_workflow
   - idx_nodes_type
   - idx_edges_workflow
   - idx_edges_source
   - idx_edges_target

3. 마이그레이션 테스트
   - upgrade 테스트
   - downgrade 테스트

---

### Milestone 6: 테스트 작성 (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/tests/unit/test_models/test_workflow.py`
- `backend/tests/integration/test_models/test_workflow_integration.py`

**Tasks:**

1. 단위 테스트 작성
   - Workflow 모델 생성 테스트
   - Node 모델 생성 테스트 (각 타입별)
   - Edge 모델 생성 테스트
   - Mixin 동작 테스트

2. 관계 테스트 작성
   - Workflow-Node 관계 테스트
   - Workflow-Edge 관계 테스트
   - Node-Edge 관계 테스트

3. 제약 조건 테스트 작성
   - 엣지 유일성 제약 테스트
   - 자기 참조 방지 테스트
   - CASCADE 삭제 테스트

4. 통합 테스트 작성
   - 전체 워크플로우 CRUD 테스트
   - 낙관적 잠금 테스트
   - 복잡한 DAG 구조 테스트

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    models/
      __init__.py        # exports: Workflow, Node, Edge
      base.py            # Base, Mixins (기존)
      enums.py           # NodeType, etc. (기존)
      workflow.py        # Workflow, Node, Edge (신규)
  alembic/
    versions/
      xxx_add_workflow_models.py  # 마이그레이션 (신규)
  tests/
    unit/
      test_models/
        test_workflow.py          # 단위 테스트 (신규)
    integration/
      test_models/
        test_workflow_integration.py  # 통합 테스트 (신규)
```

### Data Flow Diagram

```
User (owner)
    │
    ▼
Workflow
    │
    ├──────────────────┐
    │                  │
    ▼                  ▼
  Nodes              Edges
  (1..N)             (0..M)
    │                  │
    ├──────────────────┤
    ▼                  ▼
source_node ─────► target_node
```

### Relationship Diagram

```
                 ┌─────────────┐
                 │    users    │
                 └──────┬──────┘
                        │ 1
                        │
                        │ *
                 ┌──────▼──────┐
                 │  workflows  │
                 └──────┬──────┘
                        │ 1
           ┌────────────┼────────────┐
           │ *          │            │ *
    ┌──────▼──────┐     │     ┌──────▼──────┐
    │    nodes    │     │     │    edges    │
    └──────┬──────┘     │     └──────┬──────┘
           │            │            │
           │       ┌────┘            │
           │       │                 │
    ┌──────▼──────┐│          ┌──────▼──────┐
    │   tools     ││          │ source_node │
    └─────────────┘│          │ target_node │
    ┌─────────────┐│          └─────────────┘
    │   agents    │◄┘
    └─────────────┘
```

---

## Technical Approach

### JSONB Config 구조

**Workflow Config 예시:**
```json
{
  "timeout": 3600,
  "retry_policy": "exponential",
  "max_concurrent_nodes": 5,
  "error_handling": "stop_on_first_error"
}
```

**Node Config 예시 (trigger 타입):**
```json
{
  "trigger_type": "schedule",
  "cron_expression": "0 9 * * 1-5",
  "timezone": "Asia/Seoul"
}
```

**Node Config 예시 (condition 타입):**
```json
{
  "condition_expression": "{{ output.price > 50000 }}",
  "true_handle": "high_price",
  "false_handle": "low_price"
}
```

**Edge Condition 예시:**
```json
{
  "type": "expression",
  "value": "{{ source_output.status == 'success' }}"
}
```

### Retry Config 구조

```json
{
  "max_retries": 3,
  "delay": 1,
  "backoff_multiplier": 2,
  "max_delay": 60
}
```

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Tool/Agent FK가 아직 없음 | SET NULL ondelete, 임시 테이블 또는 FK defer |
| 복잡한 관계로 쿼리 성능 저하 | selectin loading, 적절한 인덱싱 |
| JSONB 스키마 변경 | Pydantic 모델로 검증, 마이그레이션 스크립트 |
| 동시 편집 충돌 | version 기반 낙관적 잠금 구현 |

---

## Output Files Summary

| File Path | Purpose |
|-----------|---------|
| `backend/app/models/workflow.py` | Workflow, Node, Edge 모델 정의 |
| `backend/app/models/__init__.py` | 모델 export 업데이트 |
| `backend/alembic/versions/xxx_add_workflow_models.py` | 마이그레이션 파일 |
| `backend/tests/unit/test_models/test_workflow.py` | 단위 테스트 |
| `backend/tests/integration/test_models/test_workflow_integration.py` | 통합 테스트 |

---

## Definition of Done

- [ ] Workflow, Node, Edge 모델 구현 완료
- [ ] 모든 relationship 정상 동작
- [ ] CASCADE 삭제 정상 동작
- [ ] 제약 조건 (UNIQUE, CHECK) 정상 동작
- [ ] Alembic 마이그레이션 성공
- [ ] 단위 테스트 85%+ 커버리지
- [ ] 통합 테스트 통과
- [ ] ruff 린팅 에러 없음
- [ ] mypy 타입 체크 통과
- [ ] 코드 리뷰 승인

---

## Next Steps After Completion

1. **SPEC-004**: Tool & Agent Registry 모델 구현 (tool_id, agent_id FK 완성)
2. **SPEC-005**: Execution Tracking Models 구현 (WorkflowExecution, NodeExecution)
3. **SPEC-007**: Workflow API Endpoints 구현
