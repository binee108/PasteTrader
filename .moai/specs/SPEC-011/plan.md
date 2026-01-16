# SPEC-011: Implementation Plan

## Tags

`[SPEC-011]` `[EXECUTION]` `[ASYNCIO]` `[IMPLEMENTATION]` `[BACKEND]`

---

## Implementation Overview

이 문서는 PasteTrader의 Workflow Execution Engine 구현 계획을 정의합니다. SPEC-010 DAG Validator와의 통합을 통해 워크플로우 구조 검증 후 asyncio 기반 병렬 실행을 구현합니다.

### 구현 전략

| 기존 파일 | 상태 | 충돌 위험 |
|----------|------|----------|
| `services/workflow/validator.py` | 참조만 함 | 없음 |
| `services/execution_service.py` | 사용 (수정 없음) | 없음 |
| `services/workflow/__init__.py` | Export 추가 | 매우 낮음 |

**신규 파일 (충돌 없음):**
- `services/workflow/executor.py` - NEW (실행 엔진)
- `services/workflow/context.py` - NEW (ExecutionContext)
- `tests/services/workflow/test_executor.py` - NEW (실행 엔진 테스트)
- `tests/services/workflow/test_context.py` - NEW (컨텍스트 테스트)
- `tests/services/workflow/test_integration.py` - NEW (통합 테스트)

---

## Milestones

### Milestone 1: ExecutionContext 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/context.py`
- `backend/tests/services/workflow/test_context.py`

**Tasks:**

1. ExecutionContext 클래스 구현
   - Node output 저장/조회
   - Variable 관리
   - asyncio.Lock 기반 Thread-safety
   - Predecessor output에서 input 해결

2. 단위 테스트 작성
   - 동시 접근 안전성 테스트
   - 다중 predecessor input 해결 테스트
   - Variable get/set 테스트

**Technical Approach:**

```python
# services/workflow/context.py
class ExecutionContext:
    """Thread-safe context for passing data between nodes.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT]
    """

    def __init__(
        self,
        workflow_execution_id: UUID,
        input_data: dict[str, Any],
    ):
        self._workflow_execution_id = workflow_execution_id
        self._variables: dict[str, Any] = dict(input_data)
        self._node_outputs: dict[UUID, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_input(
        self,
        node: Node,
        incoming_edges: list[Edge],
    ) -> dict[str, Any]:
        """Get input data for a node from predecessor outputs."""
        async with self._lock:
            input_data = dict(self._variables)
            for edge in incoming_edges:
                predecessor_output = self._node_outputs.get(
                    edge.source_node_id, {}
                )
                input_data.update(predecessor_output)
            return input_data

    async def set_output(self, node_id: UUID, data: dict) -> None:
        """Store output data from a node."""
        async with self._lock:
            self._node_outputs[node_id] = data
```

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_context.py -xvs

# Lint and type check
cd backend && uv run ruff check app/services/workflow/context.py
cd backend && uv run basedpyright app/services/workflow/context.py

# Commit
git add backend/app/services/workflow/context.py backend/tests/services/workflow/test_context.py
git commit -m "feat(workflow): implement ExecutionContext for node data passing"
```

**Verification Criteria:**
- [ ] ExecutionContext가 노드 출력을 올바르게 저장/조회
- [ ] 동시 접근이 thread-safe (asyncio.Lock)
- [ ] predecessor 출력에서 input 올바르게 집계
- [ ] 테스트 통과 및 에지 케이스 커버

---

### Milestone 2: DAGGraph 및 TopologicalSorter 구현 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/executor.py` (DAGGraph 부분)

**Tasks:**

1. DAGGraph 클래스 구현 (SPEC-010의 Graph 재사용 또는 확장)
   - 노드와 엣지에서 그래프 구축
   - Adjacency와 in-degree 추적
   - Entry nodes, successors, predecessors 조회

2. topological_sort 함수 구현
   - Kahn's algorithm 구현
   - 실행 레벨별 노드 그룹화 반환
   - 사이클 감지 (DAGValidationError 발생)

3. 단위 테스트
   - 선형 DAG (A -> B -> C)
   - 다이아몬드 DAG (A -> B,C -> D)
   - 복잡한 병렬 DAG
   - 사이클 감지

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "dag or topological"

# Lint and type check
cd backend && uv run ruff check app/services/workflow/executor.py
cd backend && uv run basedpyright app/services/workflow/executor.py

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement DAGGraph and topological sort"
```

**Verification Criteria:**
- [ ] Topological sort가 올바른 레벨 그룹화 반환
- [ ] Entry nodes 올바르게 식별
- [ ] 사이클 감지 및 적절한 에러 발생
- [ ] 복잡한 DAG 패턴 올바르게 정렬

---

### Milestone 3: WorkflowExecutor 핵심 실행 로직 (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/executor.py` (WorkflowExecutor 클래스)

**Tasks:**

1. WorkflowExecutor.execute() 구현
   - 워크플로우 로드 (노드/엣지 포함)
   - DAG 검증 (SPEC-010 활용)
   - WorkflowExecution 레코드 생성
   - DAG 구축 및 토폴로지 정렬
   - ExecutionContext 생성
   - 레벨별 노드 실행
   - 최종 결과 반환

2. 상태 전이 관리
   - PENDING -> RUNNING -> COMPLETED/FAILED

3. 단위 테스트
   - 성공적인 워크플로우 실행
   - 워크플로우 미발견 에러
   - 빈 워크플로우 (노드 없음)

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "executor"

# Lint and type check
cd backend && uv run ruff check app/services/workflow/executor.py
cd backend && uv run basedpyright app/services/workflow/executor.py

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement WorkflowExecutor core execution logic"
```

**Verification Criteria:**
- [ ] 워크플로우 노드/엣지와 함께 올바르게 로드
- [ ] WorkflowExecution 레코드 PENDING 상태로 생성
- [ ] 상태 전이 올바르게 수행 (PENDING -> RUNNING -> COMPLETED/FAILED)
- [ ] 최종 출력이 WorkflowExecution.output_data에 저장

---

### Milestone 4: 병렬 노드 실행 (asyncio.TaskGroup) (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/executor.py` (병렬 실행 부분)

**Tasks:**

1. _execute_level() 구현
   - asyncio.TaskGroup 기반 병렬 실행
   - 동일 레벨 노드 동시 실행

2. _execute_node_with_semaphore() 구현
   - 동시 실행 노드 수 제한
   - 리소스 고갈 방지

3. 단위 테스트
   - 다중 노드 동시 실행 확인
   - 의존성에 따른 실행 순서 확인
   - 타이밍 검증 (병렬이 순차보다 빠름)

**Technical Approach:**

```python
async def _execute_level(
    self,
    nodes: list[Node],
    context: ExecutionContext,
) -> list[NodeResult]:
    """Execute all nodes in a level in parallel using TaskGroup."""
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(self._execute_node_with_semaphore(node, context))
            for node in nodes
        ]
    return [task.result() for task in tasks]
```

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "parallel"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement parallel node execution with asyncio.TaskGroup"
```

**Verification Criteria:**
- [ ] 같은 레벨의 노드가 병렬로 실행
- [ ] 레벨 간 의존성 준수
- [ ] 병렬 실행 중 Context가 thread-safe
- [ ] 타이밍 테스트로 성능 향상 확인

---

### Milestone 5: 에러 핸들링 및 재시도 로직 (Secondary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/executor.py` (재시도 로직)

**Tasks:**

1. _execute_node_with_retry() 구현
   - 지수 백오프 재시도
   - 최종 실패 시 에러 저장
   - 취소 지원

2. 단위 테스트
   - 일시적 실패 시 재시도
   - 최대 재시도 초과
   - 지수 백오프 타이밍
   - 워크플로우 레벨 에러 전파

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "error or retry"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement error handling and retry logic"
```

**Verification Criteria:**
- [ ] 재시도 횟수가 NodeExecution.retry_count에 기록
- [ ] 지수 백오프 올바르게 동작
- [ ] 에러 메시지가 NodeExecution.error_message에 저장
- [ ] 최대 재시도 초과 시 워크플로우 gracefully 실패

---

### Milestone 6: 조건부 분기 (Condition Node) 처리 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/services/workflow/executor.py` (조건 평가 부분)

**Tasks:**

1. _evaluate_condition() 구현
   - node.config에서 조건 표현식 파싱
   - context 변수 대상 조건 평가
   - 우선순위에 따른 엣지 선택

2. 단위 테스트
   - 단순 boolean 조건
   - 비교 연산자
   - 우선순위 기반 엣지 선택
   - 기본(else) 경로

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "condition"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement condition node evaluation and branching"
```

**Verification Criteria:**
- [ ] node.config에서 조건 표현식 올바르게 파싱
- [ ] 조건 평가에서 context 변수 접근 가능
- [ ] 우선순위 기반 엣지 선택 동작
- [ ] 건너뛴 노드가 SKIPPED 상태로 표시

---

### Milestone 7: 타임아웃 처리 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/services/workflow/executor.py` (타임아웃 부분)

**Tasks:**

1. _execute_node_with_timeout() 구현
   - asyncio.timeout() 사용
   - 타임아웃 시 NodeTimeoutError 발생
   - 노드 FAILED 상태로 표시

2. 단위 테스트
   - 노드 타임아웃 올바르게 트리거
   - 타임아웃 에러 전파
   - 노드별 커스텀 타임아웃

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "timeout"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement node timeout handling"
```

**Verification Criteria:**
- [ ] Node.timeout_seconds 준수
- [ ] 타임아웃 시 asyncio.TimeoutError 트리거
- [ ] 노드가 타임아웃 메시지와 함께 FAILED 표시
- [ ] 설정에 따라 워크플로우 계속 또는 실패

---

### Milestone 8: 워크플로우 취소 기능 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/services/workflow/executor.py` (취소 부분)

**Tasks:**

1. cancel() 구현
   - 취소 플래그 설정
   - 실행 중인 태스크 취소
   - 대기 중인 노드 CANCELLED 표시

2. 단위 테스트
   - 대기 중인 워크플로우 취소
   - 실행 중인 워크플로우 취소
   - 이미 완료된 워크플로우 취소 불가

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "cancel"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): implement workflow cancellation support"
```

**Verification Criteria:**
- [ ] 취소 플래그가 실행 중인 태스크에 전파
- [ ] 실행 중인 노드 gracefully 중지
- [ ] 대기 중인 노드 CANCELLED 표시
- [ ] 이미 터미널 상태인 실행은 취소 거부

---

### Milestone 9: ExecutionLog 통합 (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/services/workflow/executor.py` (로깅 부분)

**Tasks:**

1. _log() 구현
   - 실행 단계별 로그 기록
   - 워크플로우 시작/종료 로그
   - 노드 실행 로그
   - 에러 로그

2. 단위 테스트
   - 워크플로우 시작/종료 로그 확인
   - 노드 실행 로그 확인
   - ERROR 레벨로 에러 로그 확인

**Commands:**
```bash
# Run tests
cd backend && uv run pytest tests/services/workflow/test_executor.py -xvs -k "log"

# Commit
git add backend/app/services/workflow/executor.py backend/tests/services/workflow/test_executor.py
git commit -m "feat(workflow): integrate ExecutionLog for execution tracing"
```

**Verification Criteria:**
- [ ] 워크플로우 시작/종료 로그 기록
- [ ] 각 노드 실행 로그 기록
- [ ] 적절한 레벨로 에러 로그 기록
- [ ] ExecutionLogService를 통해 로그 조회 가능

---

### Milestone 10: 모듈 초기화 및 통합 테스트 (Final Goal)

**Priority:** High

**Deliverables:**
- `backend/app/services/workflow/__init__.py` (업데이트)
- `backend/tests/services/workflow/test_integration.py`

**Tasks:**

1. 모듈 초기화 업데이트
   - ExecutionContext, WorkflowExecutor export 추가

2. 통합 테스트 작성
   - 엔드투엔드 워크플로우 실행
   - 모든 노드 타입을 포함한 복잡한 DAG
   - 에러 복구 시나리오

3. 전체 테스트 스위트 실행
   - 커버리지 85%+ 유지

**Commands:**
```bash
# Run all tests
cd backend && uv run pytest tests/services/workflow/ -xvs

# Run full test suite with coverage
cd backend && uv run pytest --cov=app --cov-report=term-missing

# Commit
git add backend/app/services/workflow/ backend/tests/services/workflow/
git commit -m "feat(workflow): complete SPEC-011 Workflow Execution Engine implementation"
```

**Verification Criteria:**
- [ ] 모든 모듈 올바르게 export
- [ ] 통합 테스트 통과
- [ ] 테스트 커버리지 85%+ 유지
- [ ] 기존 테스트에 회귀 없음

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    services/
      workflow/                      # Package from SPEC-010
        __init__.py                  # Updated exports
        executor.py                  # NEW - WorkflowExecutor
        context.py                   # NEW - ExecutionContext
        validator.py                 # From SPEC-010
        graph.py                     # From SPEC-010
        algorithms.py                # From SPEC-010
        exceptions.py                # Updated - Execution exceptions
  tests/
    services/
      workflow/
        test_executor.py             # NEW - Executor tests
        test_context.py              # NEW - Context tests
        test_integration.py          # NEW - Integration tests
```

### Dependency Flow

```
api/v1/executions.py (future)
       │
       ▼
services/workflow/executor.py
       │
       ├──────────────────────┐
       ▼                      ▼
services/workflow/        services/workflow/context.py
validator.py (SPEC-010)
       │
       ▼
services/workflow/algorithms.py
       │
       ▼
services/workflow/graph.py
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution Flow                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. execute(workflow_id, input_data)                        │
│     │                                                        │
│     ▼                                                        │
│  2. Load Workflow (nodes, edges)                            │
│     │                                                        │
│     ▼                                                        │
│  3. Validate DAG (SPEC-010 DAGValidator)                    │
│     │                                                        │
│     ▼                                                        │
│  4. Create WorkflowExecution (PENDING)                      │
│     │                                                        │
│     ▼                                                        │
│  5. Build Graph & Topological Sort                          │
│     │                                                        │
│     ▼                                                        │
│  6. Create ExecutionContext(input_data)                     │
│     │                                                        │
│     ▼                                                        │
│  7. For each level:                                         │
│     │   ┌─────────────────────────────────┐                 │
│     │   │  asyncio.TaskGroup              │                 │
│     │   │  ┌──────┐ ┌──────┐ ┌──────┐    │                 │
│     │   │  │Node A│ │Node B│ │Node C│    │                 │
│     │   │  └──────┘ └──────┘ └──────┘    │                 │
│     │   └─────────────────────────────────┘                 │
│     │                                                        │
│     ▼                                                        │
│  8. Complete WorkflowExecution (COMPLETED/FAILED)           │
│     │                                                        │
│     ▼                                                        │
│  9. Return ExecutionResult                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## TDD Approach

### Test Sequence

1. **Context Tests First**
   - ExecutionContext 기본 동작
   - Thread-safety 검증
   - Input resolution 로직

2. **Executor Unit Tests**
   - DAG 구축 및 정렬
   - 레벨별 실행
   - 에러 핸들링

3. **Integration Tests**
   - 전체 워크플로우 실행
   - 복잡한 DAG 시나리오
   - 성능 검증

### RED-GREEN-REFACTOR Cycle

1. 실패하는 테스트 작성
2. 테스트 통과를 위한 최소 코드 구현
3. 명확성과 성능을 위한 리팩토링

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| SPEC-010 미완성 | 인터페이스 추상화, Mock 사용 |
| 동시성 문제 | asyncio.Lock 사용, 충분한 테스트 |
| 메모리 누수 | Context 정리, 타임아웃 적용 |
| 테스트 커버리지 부족 | TDD 접근, 90%+ 목표 |

---

## Output Files Summary

| File Path | Purpose | Priority |
|-----------|---------|----------|
| `services/workflow/context.py` | ExecutionContext 구현 | High |
| `services/workflow/executor.py` | WorkflowExecutor 구현 | High |
| `services/workflow/__init__.py` | 모듈 export 업데이트 | High |
| `tests/services/workflow/test_context.py` | Context 테스트 | High |
| `tests/services/workflow/test_executor.py` | Executor 테스트 | High |
| `tests/services/workflow/test_integration.py` | 통합 테스트 | High |

---

## Definition of Done

- [ ] ExecutionContext 구현 및 테스트 완료
- [ ] WorkflowExecutor 구현 및 테스트 완료
- [ ] 병렬 실행 (asyncio.TaskGroup) 동작 확인
- [ ] 에러 핸들링 및 재시도 로직 동작 확인
- [ ] 조건 노드 분기 처리 동작 확인
- [ ] 타임아웃 및 취소 기능 동작 확인
- [ ] ExecutionLog 통합 완료
- [ ] 통합 테스트 통과
- [ ] 테스트 커버리지 85%+
- [ ] ruff lint 통과
- [ ] basedpyright 타입 체크 통과

---

## Next Steps After Completion

1. **SPEC-012**: Node Processor Framework (개별 노드 타입 처리)
2. **API Endpoint**: 워크플로우 실행 API 추가
3. **WebSocket**: 실시간 실행 상태 업데이트
4. **Monitoring**: 실행 메트릭 수집 및 대시보드

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [acceptance.md](acceptance.md) - 인수 기준
- [SPEC-010/spec.md](../SPEC-010/spec.md) - DAG Validation Service
- [SPEC-005/spec.md](../SPEC-005/spec.md) - Execution Tracking Models

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-15 | workflow-spec | Initial implementation plan |
