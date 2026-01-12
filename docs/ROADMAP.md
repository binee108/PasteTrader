# PasteTrader MVP Roadmap

> **Version**: 0.1.0 (Alpha)
> **Target**: Q1 2025
> **Last Updated**: 2026-01-12

## Overview

PasteTrader는 AI 기반 트레이딩 워크플로우 자동화 플랫폼입니다. 이 로드맵은 MVP 완성을 위한 단계별 구현 계획을 정의합니다.

### Development Approach
- **Backend First**: DB 모델 → API → 서비스 레이어 순서
- **Priority Feature**: Workflow Engine (DAG 패턴 기반)
- **Methodology**: SPEC-First TDD

---

## Phase Summary

| Phase | Name | Complexity | Duration | Status |
|-------|------|------------|----------|--------|
| 0 | Database Foundation | S-M | Week 1 | ✅ Implemented |
| 1 | Workflow Core Models | M-L | Week 1 | 🔲 Pending |
| 2 | Execution Models | M | Week 2 | 🔲 Pending |
| 3 | API Layer | M-L | Week 2 | 🔲 Pending |
| 4 | Workflow Engine | XL | Week 3-4 | 🔲 Pending |
| 5 | LLM Integration | L | Week 5 | 🔲 Pending |
| 6 | Content Parsing | M | Week 8 | 🔲 Pending |
| 7 | Frontend UI | XL | Week 6-7 | 🔲 Pending |
| 8 | Scheduler Integration | M | Week 8 | 🔲 Pending |
| 9 | Stock Screening | L | Week 9+ | 🔲 Pending |

---

## Phase Details

### Phase 0: Database Foundation

**Objective**: Alembic 설정 및 기본 모델 구조 확립

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Alembic 초기 설정 | S | SPEC-001 | `backend/alembic/` |
| Base 모델 (TimestampMixin, SoftDeleteMixin) | S | SPEC-001 | `backend/app/models/base.py` |
| User 모델 및 기본 인증 | M | SPEC-002 | `backend/app/models/user.py` |

**Dependencies**: None

**Deliverables**:
- [x] Alembic configuration with async support
- [x] Base model with common mixins (UUIDMixin, TimestampMixin, SoftDeleteMixin)
- [x] User model with password hashing (SPEC-002)
- [x] Security utilities with bcrypt hashing (SPEC-002)
- [x] Email normalization and validation (SPEC-002)
- [x] User schemas and service layer (SPEC-002)
- [x] Centralized logging module (SPEC-002)
- [x] Initial migration script
- [x] Migration safety check (CONFIRM_PRODUCTION_MIGRATION)
- [x] Soft delete filtering in Service Layer
- [x] Test coverage 89.02% (877 tests passed)

---

### Phase 1: Workflow Core Models ⭐ Critical Path

**Objective**: DAG 기반 워크플로우 정의를 위한 핵심 모델 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Workflow 모델 | M | SPEC-003 | `backend/app/models/workflow.py` |
| Node 모델 (6가지 타입) | L | SPEC-003 | `backend/app/models/workflow.py` |
| Edge 모델 | M | SPEC-003 | `backend/app/models/workflow.py` |
| Tool 모델 | M | SPEC-004 | `backend/app/models/tool.py` |
| Agent 모델 | M | SPEC-004 | `backend/app/models/agent.py` |

**Node Types**:
1. `tool` - 외부 도구 실행
2. `agent` - LLM 에이전트 호출
3. `condition` - 분기 로직
4. `adapter` - 데이터 변환
5. `trigger` - 트리거/이벤트
6. `aggregator` - 결과 집계

**Dependencies**: Phase 0

**Deliverables**:
- [ ] Workflow model with JSONB config
- [ ] Node model with 6 type enum
- [ ] Edge model with condition support
- [ ] Tool registry model
- [ ] Agent configuration model
- [ ] Migration scripts

---

### Phase 2: Execution Models

**Objective**: 워크플로우 실행 이력 및 상태 추적 모델 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| WorkflowExecution 모델 | M | SPEC-005 | `backend/app/models/execution.py` |
| NodeExecution 모델 | M | SPEC-005 | `backend/app/models/execution.py` |
| ExecutionLog 모델 | S | SPEC-005 | `backend/app/models/execution.py` |
| Schedule 모델 | M | SPEC-006 | `backend/app/models/schedule.py` |

**Execution Status Enum**:
- `pending`, `running`, `completed`, `failed`, `cancelled`, `timeout`, `skipped`

**Dependencies**: Phase 0, Phase 1

**Deliverables**:
- [ ] WorkflowExecution with trigger tracking
- [ ] NodeExecution with retry support
- [ ] ExecutionLog for detailed debugging
- [ ] Schedule model for APScheduler
- [ ] Migration scripts

---

### Phase 3: API Layer

**Objective**: RESTful API 엔드포인트 및 Pydantic 스키마 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Workflow Schemas | M | SPEC-007 | `backend/app/schemas/workflow.py` |
| Workflow CRUD API | L | SPEC-007 | `backend/app/api/v1/workflows.py` |
| Execution API | M | SPEC-008 | `backend/app/api/v1/executions.py` |
| Tool/Agent API | M | SPEC-009 | `backend/app/api/v1/tools.py` |

**API Endpoints**:
```
POST   /api/v1/workflows           - Create workflow
GET    /api/v1/workflows           - List workflows
GET    /api/v1/workflows/{id}      - Get workflow
PUT    /api/v1/workflows/{id}      - Update workflow
DELETE /api/v1/workflows/{id}      - Delete workflow
POST   /api/v1/workflows/{id}/execute - Execute workflow
GET    /api/v1/executions/{id}     - Get execution status
GET    /api/v1/executions/{id}/logs - Get execution logs
```

**Dependencies**: Phase 1, Phase 2

**Deliverables**:
- [ ] Pydantic schemas (Create, Update, Response)
- [ ] Workflow CRUD endpoints
- [ ] Execution endpoints
- [ ] Tool/Agent management endpoints
- [ ] OpenAPI documentation

---

### Phase 4: Workflow Engine ⭐ Critical Path

**Objective**: DAG 기반 워크플로우 실행 엔진 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| DAG Validator | M | SPEC-010 | `backend/app/services/workflow/validator.py` |
| DAG Executor | XL | SPEC-011 | `backend/app/services/workflow/executor.py` |
| Node Processors | XL | SPEC-012 | `backend/app/services/workflow/nodes/` |
| Parallel Execution | L | SPEC-011 | asyncio integration |

**Node Processor Interface**:
```python
class NodeProcessor(ABC):
    async def execute(self, node: Node, context: ExecutionContext) -> NodeResult:
        ...
```

**Processor Types**:
- `ToolNodeProcessor` - HTTP/MCP/Python 도구 실행
- `AgentNodeProcessor` - LLM 에이전트 호출
- `ConditionNodeProcessor` - 조건부 분기
- `AdapterNodeProcessor` - 데이터 변환
- `TriggerNodeProcessor` - 이벤트 처리
- `AggregatorNodeProcessor` - 결과 집계

**Dependencies**: Phase 3

**Deliverables**:
- [ ] DAG cycle detection
- [ ] Topological sort execution
- [ ] 6 node type processors
- [ ] Async parallel execution
- [ ] Error handling & retry logic
- [ ] Execution context management

---

### Phase 5: LLM Integration

**Objective**: Multi-Provider LLM 클라이언트 및 에이전트 통합

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Provider Abstraction | L | SPEC-013 | `backend/app/services/llm/base.py` |
| Anthropic Provider | M | SPEC-014 | `backend/app/services/llm/anthropic.py` |
| OpenAI Provider | M | SPEC-015 | `backend/app/services/llm/openai.py` |
| Z.AI Provider | M | SPEC-016 | `backend/app/services/llm/zhipuai.py` |
| Agent Node Processor | L | SPEC-017 | Integration with Phase 4 |

**Provider Interface**:
```python
class LLMProvider(ABC):
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        ...

    async def generate_with_tools(self, prompt: str, tools: list[Tool]) -> LLMResponse:
        ...
```

**Dependencies**: Phase 4

**Deliverables**:
- [ ] Abstract LLMProvider base class
- [ ] Anthropic Claude integration
- [ ] OpenAI GPT integration
- [ ] Z.AI GLM integration
- [ ] ReAct pattern implementation
- [ ] Tool calling support

---

### Phase 6: Content Parsing

**Objective**: 다양한 입력 소스에서 트레이딩 전략 추출

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Parser Framework | M | SPEC-018 | `backend/app/services/parsers/base.py` |
| Text Parser | S | SPEC-018 | `backend/app/services/parsers/text.py` |
| PDF Parser | M | SPEC-019 | `backend/app/services/parsers/pdf.py` |
| YouTube Parser | M | SPEC-020 | `backend/app/services/parsers/youtube.py` |

**Parser Interface**:
```python
class ContentParser(ABC):
    async def parse(self, source: str | bytes) -> ParsedContent:
        ...
```

**Dependencies**: Phase 5 (LLM for analysis)

**Deliverables**:
- [ ] Abstract parser framework
- [ ] Plain text parsing
- [ ] PDF text extraction (PyMuPDF)
- [ ] YouTube transcript extraction
- [ ] LLM-based strategy analysis

---

### Phase 7: Frontend UI

**Objective**: React Flow 기반 워크플로우 에디터 및 대시보드 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Workflow Canvas | XL | SPEC-021 | `frontend/components/workflow/Canvas.tsx` |
| Custom Nodes | L | SPEC-022 | `frontend/components/workflow/nodes/` |
| Node Config Panel | L | SPEC-023 | `frontend/components/workflow/ConfigPanel.tsx` |
| Execution Monitor | M | SPEC-024 | `frontend/components/workflow/Monitor.tsx` |
| Dashboard | M | SPEC-025 | `frontend/app/dashboard/` |

**Custom Node Types**:
- ToolNode, AgentNode, ConditionNode, AdapterNode, TriggerNode, AggregatorNode

**Dependencies**: Phase 3 (API)

**Deliverables**:
- [ ] React Flow canvas with zoom/pan
- [ ] 6 custom node components
- [ ] Drag-and-drop node creation
- [ ] Node configuration panel
- [ ] Real-time execution monitor
- [ ] Workflow list dashboard
- [ ] Zustand state management

---

### Phase 8: Scheduler Integration

**Objective**: APScheduler 기반 워크플로우 예약 실행

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| APScheduler 설정 | M | SPEC-026 | `backend/app/services/scheduler/config.py` |
| Schedule Service | M | SPEC-027 | `backend/app/services/scheduler/service.py` |
| Schedule UI | M | SPEC-028 | `frontend/components/workflow/Scheduler.tsx` |

**Schedule Types**:
- `cron` - Cron expression
- `interval` - Fixed interval
- `date` - One-time execution

**Dependencies**: Phase 4, Phase 7

**Deliverables**:
- [ ] APScheduler async integration
- [ ] Schedule CRUD service
- [ ] Job persistence in PostgreSQL
- [ ] Schedule management UI
- [ ] Next run time calculation

---

### Phase 9: Stock Screening (MVP Stretch Goal)

**Objective**: 조건 기반 주식 스크리닝 기능

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Stock Data Integration | L | SPEC-029 | `backend/app/services/stock/data.py` |
| Screening Service | L | SPEC-030 | `backend/app/services/stock/screener.py` |
| Stock Node Types | M | SPEC-031 | `backend/app/services/workflow/nodes/stock.py` |

**Data Sources** (External APIs):
- Korea Investment API
- Yahoo Finance
- Custom data providers

**Dependencies**: Phase 4, Phase 5

**Deliverables**:
- [ ] Market data fetching
- [ ] Technical indicator calculation
- [ ] Condition-based filtering
- [ ] Signal generation
- [ ] Stock-specific node processors

---

## Dependency Graph

```
Phase 0 ─────┬──────────────────────────────────────────────┐
             │                                              │
             v                                              │
Phase 1 ─────┬───> Phase 3 ───> Phase 4 ───> Phase 5       │
             │         │            │            │          │
             v         │            v            v          │
Phase 2 ────────────────┘      Phase 7 <─────────┘          │
             │                     │                        │
             v                     v                        │
        Phase 8 <──────────────────┘                        │
             │                                              │
             v                                              v
        Phase 6 ───────────────────────────────────────────>│
             │                                              │
             v                                              v
        Phase 9 ◄───────────────────────────────────────────
```

### Critical Path
1. **Phase 0** → **Phase 1** → **Phase 3** → **Phase 4** → Phase 5
2. Phase 4 (Workflow Engine)가 핵심 병목 지점

---

## SPEC Document Mapping

| SPEC ID | Phase | Title | Priority | Status |
|---------|-------|-------|----------|--------|
| SPEC-001 | 0 | Database Foundation Setup | P0 | ✅ |
| SPEC-002 | 0 | User Authentication Model | P0 | ✅ |
| SPEC-003 | 1 | Workflow Domain Models | P0 | |
| SPEC-004 | 1 | Tool & Agent Registry | P0 | |
| SPEC-005 | 2 | Execution Tracking Models | P0 | |
| SPEC-006 | 2 | Schedule Configuration Model | P1 | |
| SPEC-007 | 3 | Workflow API Endpoints | P0 | |
| SPEC-008 | 3 | Execution API Endpoints | P0 | |
| SPEC-009 | 3 | Tool/Agent API Endpoints | P1 | |
| SPEC-010 | 4 | DAG Validation Service | P0 | |
| SPEC-011 | 4 | Workflow Execution Engine | P0 | |
| SPEC-012 | 4 | Node Processor Framework | P0 | |
| SPEC-013 | 5 | LLM Provider Abstraction | P0 | |
| SPEC-014 | 5 | Anthropic Provider | P0 | |
| SPEC-015 | 5 | OpenAI Provider | P1 | |
| SPEC-016 | 5 | Z.AI Provider | P2 | |
| SPEC-017 | 5 | Agent Node Integration | P0 | |
| SPEC-018 | 6 | Content Parser Framework | P1 | |
| SPEC-019 | 6 | PDF Parser | P1 | |
| SPEC-020 | 6 | YouTube Parser | P2 | |
| SPEC-021 | 7 | React Flow Canvas | P0 | |
| SPEC-022 | 7 | Custom Node Components | P0 | |
| SPEC-023 | 7 | Node Configuration Panel | P1 | |
| SPEC-024 | 7 | Execution Monitor UI | P1 | |
| SPEC-025 | 7 | Dashboard | P2 | |
| SPEC-026 | 8 | APScheduler Integration | P1 | |
| SPEC-027 | 8 | Schedule Management Service | P1 | |
| SPEC-028 | 8 | Schedule UI | P2 | |
| SPEC-029 | 9 | Stock Data Integration | P2 | |
| SPEC-030 | 9 | Stock Screening Service | P2 | |
| SPEC-031 | 9 | Stock Node Types | P2 | |

**Priority Legend**:
- P0: MVP 필수
- P1: MVP 권장
- P2: MVP 이후

---

## Database Schema Overview

### Core Tables

```
users                 - 사용자 계정
workflows             - 워크플로우 정의 (DAG)
nodes                 - 워크플로우 노드 (6가지 타입)
edges                 - 노드 간 연결
tools                 - 외부 도구 레지스트리
agents                - LLM 에이전트 설정
workflow_executions   - 실행 이력
node_executions       - 노드별 실행 상태
execution_logs        - 상세 로그
schedules             - APScheduler 작업
```

### Key Design Decisions

1. **JSONB for Config**: 유연한 노드/에이전트 설정 저장
2. **Soft Delete**: `deleted_at` 컬럼으로 감사 추적
3. **Optimistic Locking**: `version` 컬럼으로 동시 편집 제어
4. **6 Node Types**: 확장 가능한 노드 타입 시스템

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Workflow Generation Success | 90%+ | Weekly |
| LLM Analysis Accuracy | 85%+ | Monthly |
| Schedule Execution Stability | 99.5% | Daily |
| API Response Time (p95) | < 500ms | Continuous |
| Test Coverage | 80%+ | Per PR |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API 비용 초과 | High | Z.AI 폴백, 캐싱 적극 활용 |
| DAG 실행 복잡성 | High | 단계별 검증, 충분한 테스트 |
| React Flow 학습 곡선 | Medium | 공식 예제 기반 구현 |
| 외부 API 의존성 | Medium | 재시도 로직, 폴백 전략 |

---

## Next Steps

### Current Status (2026-01-12)

**Completed**:
- ✅ Phase 0: Database Foundation (SPEC-001, SPEC-002)
  - Alembic 설정 완료 (SPEC-001)
  - Base 모델 구현 (UUIDMixin, TimestampMixin, SoftDeleteMixin) (SPEC-001)
  - Soft Delete 필터링 구현 (SPEC-001)
  - Migration Safety 체크 추가 (SPEC-001)
  - User Authentication Model 구현 (SPEC-002)
    - User 모델 (email, hashed_password, is_active, is_superuser)
    - Security utilities (bcrypt 비밀번호 해싱)
    - Email normalization and validation utilities
    - User schemas (UserCreate, UserUpdate, UserResponse, UserLogin)
    - User service layer (CRUD operations)
    - Centralized logging module
  - 테스트 커버리지 89.02% 달성 (877 tests passed)
  - TRUST 5 퀄리티 게이트 통과
  - 문서 동기화 완료
  - PR 생성: https://github.com/binee108/PasteTrader/pull/1

**Next Session Goals**:
1. **Phase 1: Workflow Core Models** (SPEC-003, SPEC-004)
   - Workflow 모델 구현
   - Node 모델 (6가지 타입)
   - Edge 모델
   - Tool 모델
   - Agent 모델

2. **Phase 2: Execution Models** (SPEC-005, SPEC-006)
   - WorkflowExecution 모델
   - NodeExecution 모델
   - ExecutionLog 모델
   - Schedule 모델

### Commands for Next Session

```bash
# Phase 1 시작
/moai:1-plan "Workflow Domain Models"

# 또는 Phase 2 시작
/moai:1-plan "Execution Tracking Models"
```

### Recommended Sequence

1. **Week 2**: Phase 1 (Workflow Core Models) + Phase 2 (Execution Models)
2. **Week 3**: Phase 3 (API Layer)
3. **Week 4-5**: Phase 4 (Workflow Engine) ⭐ Critical Path

---

*Generated by MoAI-ADK • PasteTrader MVP Planning Session*
