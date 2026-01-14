# PasteTrader MVP Roadmap

> **Version**: 0.1.0 (Alpha)
> **Target**: Q1 2025
> **Last Updated**: 2026-01-14

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
| 1 | Workflow Core Models | M-L | Week 1 | ✅ Implemented |
| 2 | Execution Models | M | Week 2 | ✅ Implemented |
| 3 | API Layer | M-L | Week 2 | ✅ Implemented |
| 4 | Workflow Engine | XL | Week 3-4 | 🔲 Pending |
| 5 | LLM Integration | L | Week 5 | 🔲 Pending |
| 6 | Content Parsing | M | Week 8 | 🔲 Pending |
| 7 | Frontend UI | XL | Week 6-7 | 🔲 Pending |
| 8 | Scheduler Integration | M | Week 8 | 🚧 Partially Complete |
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
- [x] Workflow model with JSONB config
- [x] Node model with 6 type enum
- [x] Edge model with condition support
- [x] Tool registry model
- [x] Agent configuration model
- [x] Migration scripts

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
- [x] WorkflowExecution with trigger tracking
- [x] NodeExecution with retry support
- [x] ExecutionLog for detailed debugging
- [x] Schedule model for APScheduler (SPEC-006)
- [x] Migration scripts

---

### Phase 3: API Layer ✅ Implemented (2026-01-14)

**Objective**: RESTful API 엔드포인트 및 Pydantic 스키마 구현

| Task | Complexity | SPEC | Output |
|------|------------|------|--------|
| Workflow Schemas | M | SPEC-007 | `backend/app/schemas/workflow.py` |
| Workflow CRUD API | L | SPEC-007 | `backend/app/api/v1/workflows.py` |
| Execution API | M | SPEC-008 | `backend/app/api/v1/executions.py` |
| Tool/Agent API | M | SPEC-009 | `backend/app/api/v1/tools.py` |

**API Endpoints Summary** (45 Total):

```
Workflow API (20 endpoints):
  GET    /api/v1/workflows/                      - List workflows
  POST   /api/v1/workflows/                      - Create workflow
  GET    /api/v1/workflows/{id}                  - Get workflow
  GET    /api/v1/workflows/{id}/full             - Get workflow with nodes/edges
  PUT    /api/v1/workflows/{id}                  - Update workflow
  DELETE /api/v1/workflows/{id}                  - Delete workflow
  POST   /api/v1/workflows/{id}/duplicate        - Duplicate workflow
  POST   /api/v1/workflows/{id}/execute          - Execute workflow ⭐
  GET    /api/v1/workflows/{id}/nodes            - List nodes
  POST   /api/v1/workflows/{id}/nodes            - Create node
  POST   /api/v1/workflows/{id}/nodes/batch      - Create nodes batch
  GET    /api/v1/workflows/{id}/nodes/{node_id}  - Get node
  PUT    /api/v1/workflows/{id}/nodes/{node_id}  - Update node
  DELETE /api/v1/workflows/{id}/nodes/{node_id}  - Delete node
  GET    /api/v1/workflows/{id}/edges            - List edges
  POST   /api/v1/workflows/{id}/edges            - Create edge
  POST   /api/v1/workflows/{id}/edges/batch      - Create edges batch
  DELETE /api/v1/workflows/{id}/edges/{edge_id}  - Delete edge
  PUT    /api/v1/workflows/{id}/graph            - Update entire graph

Execution API (12 endpoints):
  GET    /api/v1/executions/                     - List executions
  POST   /api/v1/executions/                     - Create execution
  GET    /api/v1/executions/{id}                 - Get execution
  GET    /api/v1/executions/{id}/detail          - Get execution with details
  POST   /api/v1/executions/{id}/cancel          - Cancel execution
  GET    /api/v1/executions/{id}/statistics      - Get execution statistics
  GET    /api/v1/executions/{id}/nodes           - List node executions
  GET    /api/v1/executions/{id}/nodes/{ne_id}   - Get node execution
  GET    /api/v1/executions/{id}/logs            - List execution logs
  GET    /api/v1/executions/{id}/nodes/{ne_id}/logs - Get node logs
  GET    /api/v1/executions/workflows/{wf_id}/executions - List by workflow
  GET    /api/v1/executions/workflows/{wf_id}/statistics - Workflow stats

Tool API (6 endpoints):
  GET    /api/v1/tools/                          - List tools
  POST   /api/v1/tools/                          - Create tool
  GET    /api/v1/tools/{id}                      - Get tool
  PUT    /api/v1/tools/{id}                      - Update tool
  DELETE /api/v1/tools/{id}                      - Delete tool
  POST   /api/v1/tools/{id}/test                 - Test tool

Agent API (7 endpoints):
  GET    /api/v1/agents/                         - List agents
  POST   /api/v1/agents/                         - Create agent
  GET    /api/v1/agents/{id}                     - Get agent
  PUT    /api/v1/agents/{id}                     - Update agent
  DELETE /api/v1/agents/{id}                     - Delete agent
  POST   /api/v1/agents/{id}/tools               - Add tool to agent
  DELETE /api/v1/agents/{id}/tools/{tool_id}     - Remove tool from agent
```

**Dependencies**: Phase 1, Phase 2

**Deliverables**:
- [x] Pydantic schemas (Create, Update, Response) - All 4 files complete
- [x] Workflow CRUD endpoints (20 endpoints)
- [x] Execution endpoints (12 endpoints with nested resources)
- [x] Tool/Agent management endpoints (13 endpoints)
- [x] OpenAPI documentation (auto-generated by FastAPI)
- [x] Comprehensive test coverage (89.41%, 938 tests)

**Implementation Summary**:
- **Total Endpoints**: 45 REST API endpoints
- **Schema Files**: 4 files (1,563 total lines)
  - `backend/app/schemas/workflow.py` (613 lines)
  - `backend/app/schemas/execution.py` (608 lines)
  - `backend/app/schemas/tool.py` (186 lines)
  - `backend/app/schemas/agent.py` (156 lines)
- **API Router Files**: 4 files (2,613 total lines)
  - `backend/app/api/v1/workflows.py` (1,160 lines)
  - `backend/app/api/v1/executions.py` (762 lines)
  - `backend/app/api/v1/tools.py` (323 lines)
  - `backend/app/api/v1/agents.py` (368 lines)
- **Test Files**: 4 files (3,462 total lines)
  - `tests/test_api/test_api_workflows.py` (2,065 lines)
  - `tests/test_api/test_api_executions.py` (886 lines)
  - `tests/test_api/test_api_tools.py` (227 lines)
  - `tests/test_api/test_api_agents.py` (284 lines)

**Quality Gate**: ✅ PASSED (SPEC-007 acceptance criteria)
- Test Coverage: 89.41% (Target: 80%+)
- Total Tests: 938 (all passing)
- All endpoints: COMPLETE

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

### Phase 8: Scheduler Integration 🚧 Partially Complete

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

**Completed**:
- [x] Schedule model for APScheduler (SPEC-006)
- [x] Job persistence in PostgreSQL (SPEC-006)
- [x] Schedule model tests (`tests/test_models_schedule.py`)

**Remaining**:
- [ ] APScheduler async integration (scheduler service directory missing)
- [ ] Schedule CRUD service (`backend/app/services/scheduler/` not implemented)
- [ ] Schedule API endpoints (no `schedules.py` in `api/v1/`)
- [ ] Schedule management UI
- [ ] Next run time calculation

**Blocking Issues**:
- No dedicated scheduler service implementation
- APScheduler integration incomplete (model-only)
- No API endpoints for schedule management

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
| SPEC-003 | 1 | Workflow Domain Models | P0 | ✅ |
| SPEC-004 | 1 | Tool & Agent Registry | P0 | ✅ |
| SPEC-005 | 2 | Execution Tracking Models | P0 | ✅ |
| SPEC-006 | 2 | Schedule Configuration Model | P1 | ✅ |
| SPEC-007 | 3 | Workflow API Endpoints | P0 | ✅ Complete (89.41% coverage) |
| SPEC-008 | 3/8 | Execution API Endpoints & APScheduler Integration | P0 | 🚧 Partial (API done, Scheduler pending) |
| SPEC-009 | 3 | Tool/Agent API Endpoints | P1 | ✅ |
| SPEC-010 | 4 | DAG Validation Service | P0 | 🔲 |
| SPEC-011 | 4 | Workflow Execution Engine | P0 | 🔲 |
| SPEC-012 | 4 | Node Processor Framework | P0 | 🔲 |
| SPEC-013 | 5 | LLM Provider Abstraction | P0 | 🔲 |
| SPEC-014 | 5 | Anthropic Provider | P0 | 🔲 |
| SPEC-015 | 5 | OpenAI Provider | P1 | 🔲 |
| SPEC-016 | 5 | Z.AI Provider | P2 | 🔲 |
| SPEC-017 | 5 | Agent Node Integration | P0 | 🔲 |
| SPEC-018 | 6 | Content Parser Framework | P1 | 🔲 |
| SPEC-019 | 6 | PDF Parser | P1 | 🔲 |
| SPEC-020 | 6 | YouTube Parser | P2 | 🔲 |
| SPEC-021 | 7 | React Flow Canvas | P0 | 🔲 |
| SPEC-022 | 7 | Custom Node Components | P0 | 🔲 |
| SPEC-023 | 7 | Node Configuration Panel | P1 | 🔲 |
| SPEC-024 | 7 | Execution Monitor UI | P1 | 🔲 |
| SPEC-025 | 7 | Dashboard | P2 | 🔲 |
| SPEC-026 | 8 | APScheduler Integration | P1 | 🔲 |
| SPEC-027 | 8 | Schedule Management Service | P1 | 🔲 |
| SPEC-028 | 8 | Schedule UI | P2 | 🔲 |
| SPEC-029 | 9 | Stock Data Integration | P2 | 🔲 |
| SPEC-030 | 9 | Stock Screening Service | P2 | 🔲 |
| SPEC-031 | 9 | Stock Node Types | P2 | 🔲 |

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

| Metric | Target | Current | Measurement |
|--------|--------|---------|-------------|
| Workflow Generation Success | 90%+ | N/A | Weekly |
| LLM Analysis Accuracy | 85%+ | N/A | Monthly |
| Schedule Execution Stability | 99.5% | N/A | Daily |
| API Response Time (p95) | < 500ms | N/A | Continuous |
| Test Coverage | 80%+ | 89.41% ✅ | Per PR |

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

### Current Status (2026-01-14)

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

- ✅ Phase 1: Workflow Core Models (SPEC-003, SPEC-004)
  - Workflow 모델 구현 (SPEC-003)
    - JSONB 기반 설정 저장
    - 버전 관리 및 활성/비활성 상태
  - Node 모델 구현 (SPEC-003)
    - 6가지 노드 타입 (tool, agent, condition, adapter, trigger, aggregator)
    - JSONB 기반 파라미터 저장
  - Edge 모델 구현 (SPEC-003)
    - 조건부 분기 지원
    - 다중 에지 지원
  - Tool 모델 구현 (SPEC-004)
    - 도구 레지스트리
    - 암호화된 API 키 저장
  - Agent 모델 구현 (SPEC-004)
    - LLM 에이전트 설정
    - Provider 및 모델 구성
  - 마이그레이션 스크립트 작성

- ✅ Phase 2: Execution Models (SPEC-005, SPEC-006)
  - WorkflowExecution 모델 구현 (SPEC-005)
    - 트리거 추적
    - 실행 상태 관리
  - NodeExecution 모델 구현 (SPEC-005)
    - 재시도 지원
    - 개별 노드 실행 상태 추적
  - ExecutionLog 모델 구현 (SPEC-005)
    - 상세 디버깅 로그
  - Schedule 모델 구현 (SPEC-006)
    - APScheduler 기반 스케줄 설정
    - Cron, Interval, Date 타입 지원
    - 활성/비활성 상태 관리
  - 마이그레이션 스크립트 작성

- ✅ Phase 3: API Layer (SPEC-007, SPEC-008, SPEC-009)
  - Workflow API 구현 (SPEC-007)
    - 20개 엔드포인트 (Workflow CRUD + Node/Edge 관리)
    - 편의 엔드포인트: POST /workflows/{id}/execute
  - Execution API 구현 (SPEC-008)
    - 12개 엔드포인트 (실행 관리 + 상세 로그)
  - Tool API 구현 (SPEC-009)
    - 6개 엔드포인트 (Tool CRUD + Test)
  - Agent API 구현 (SPEC-009)
    - 7개 엔드포인트 (Agent CRUD + Tool 연결)
  - **총 45개 REST API 엔드포인트 구현**
  - 테스트 커버리지 89.41% 달성 (938 tests passed)
  - TRUST 5 퀄리티 게이트 통과 (SPEC-007)

**Partially Complete**:
- 🚧 Phase 8: Scheduler Integration
  - Schedule 모델 구현 완료 (SPEC-006)
  - Schedule 테스트 완료
  - **필요한 작업**:
    - APScheduler 서비스 구현
    - Schedule API 엔드포인트 구현
    - Schedule 관리 UI 구현

### Next Session Goals

**Recommended Priority Order**:

1. **Phase 4: Workflow Engine** ⭐ **CRITICAL PATH**
   - SPEC-010: DAG Validation Service
   - SPEC-011: Workflow Execution Engine
   - SPEC-012: Node Processor Framework
   - This is the core functionality that enables actual workflow execution

2. **Phase 8: Scheduler Integration** (완료)
   - APScheduler 서비스 구현
   - Schedule API 엔드포인트
   - Schedule 관리 UI

3. **Phase 5: LLM Integration**
   - SPEC-013: LLM Provider Abstraction
   - SPEC-014: Anthropic Provider
   - SPEC-017: Agent Node Integration

### Commands for Next Session

```bash
# Phase 4 시작 (Workflow Engine - CRITICAL PATH)
/moai:1-plan "DAG Validation Service for Workflow Engine"
```

### Recommended Sequence

1. **Week 3-4**: Phase 4 (Workflow Engine) ⭐ **CRITICAL PATH**
   - DAG Validator
   - Workflow Executor
   - Node Processors (6 types)

2. **Week 4**: Phase 8 (Scheduler Integration 완료)
   - APScheduler 서비스
   - Schedule API

3. **Week 5**: Phase 5 (LLM Integration)
   - LLM Provider Abstraction
   - Anthropic/OpenAI/Z.AI Providers

---

*Generated by MoAI-ADK • PasteTrader MVP Planning Session*
