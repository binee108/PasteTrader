# SPEC-011: Workflow Execution Engine

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-011 |
| Title | Workflow Execution Engine |
| Created | 2026-01-15 |
| Status | In Progress |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 4 - Workflow Engine |

## Tags

`[SPEC-011]` `[EXECUTION]` `[DAG]` `[ASYNCIO]` `[WORKFLOW]` `[ENGINE]` `[BACKEND]`

---

## Overview

이 SPEC은 PasteTrader 워크플로우 엔진의 핵심인 DAG 토폴로지 정렬 기반 비동기 실행 엔진을 정의합니다. SPEC-010 DAG Validator를 활용하여 워크플로우 구조를 검증한 후, asyncio 기반 병렬 노드 실행과 ExecutionContext를 통한 노드 간 데이터 전달을 구현합니다.

### Scope

- 워크플로우 실행 엔진 모듈 (`backend/app/services/workflow/executor.py`)
- ExecutionContext 관리 (`backend/app/services/workflow/context.py`)
- DAG 토폴로지 정렬 (Kahn's Algorithm)
- asyncio.TaskGroup 기반 병렬 노드 실행
- 에러 핸들링 및 지수 백오프 재시도
- 조건 노드 분기 처리
- 타임아웃 및 취소 지원
- ExecutionLog 통합

### Out of Scope

- 개별 노드 프로세서 구현 (SPEC-012)
- 스케줄러 통합 (SPEC-008에서 처리)
- 실시간 WebSocket 실행 상태 업데이트 (미래 SPEC)
- 분산 실행 (미래 SPEC)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115.x | API framework |
| Pydantic | 2.10.x | Schema validation |
| SQLAlchemy | 2.0.x | Async ORM |
| Python | 3.13.x | Runtime environment |
| asyncio | built-in | Async execution (TaskGroup, timeout) |

### Configuration Dependencies

- SPEC-001: Base models, Mixins, Enums
- SPEC-003: Workflow, Node, Edge models
- SPEC-005: WorkflowExecution, NodeExecution, ExecutionLog models
- SPEC-010: DAG Validator (topological sort, cycle detection)

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| asyncio.TaskGroup provides structured concurrency | High | Python 3.11+ standard library | Need fallback to gather() |
| Kahn's algorithm scales to 500+ nodes | High | O(V+E) complexity | Need level-based batching |
| ExecutionContext thread-safety via asyncio.Lock | High | Standard async pattern | Need alternative concurrency control |
| Node execution can complete within timeout_seconds | Medium | Configurable per node | May need forced termination |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Nodes in same topological level have no dependencies | High | Sequential fallback needed |
| Failed nodes should block downstream execution | High | Add failure isolation policy |
| Retry with exponential backoff is sufficient | Medium | Add circuit breaker pattern |

---

## Requirements

### Core Execution Requirements

#### REQ-011-001: DAG 토폴로지 정렬 기반 실행

**Event-Driven Requirement**

**WHEN** 워크플로우 실행이 요청되면, **THEN** 시스템은 DAG 토폴로지 정렬을 수행하여 노드 실행 순서를 결정해야 합니다.

**Details:**

- Algorithm: Kahn's Algorithm (SPEC-010의 topological_sort_levels 활용)
- Output: 실행 레벨별로 그룹화된 노드 목록
- Performance: O(V+E) time complexity
- 같은 레벨의 노드는 병렬 실행 가능

**Response:**
```json
{
  "execution_order": [
    {"level": 0, "node_ids": ["trigger-1"]},
    {"level": 1, "node_ids": ["tool-1", "tool-2"]},
    {"level": 2, "node_ids": ["agent-1"]}
  ]
}
```

#### REQ-011-002: asyncio.TaskGroup 기반 병렬 실행

**Ubiquitous Requirement**

시스템은 **항상** 같은 토폴로지 레벨의 노드들을 asyncio.TaskGroup을 사용하여 병렬로 실행해야 합니다.

**Details:**

- Structured concurrency with TaskGroup
- 동시 실행 노드 수 제한 (Semaphore)
- 한 노드 실패 시 다른 병렬 노드는 계속 실행

**Code Pattern:**
```python
async with asyncio.TaskGroup() as tg:
    tasks = [
        tg.create_task(self._execute_node(node, context))
        for node in level_nodes
    ]
```

#### REQ-011-003: ExecutionContext 노드 간 데이터 전달

**Ubiquitous Requirement**

시스템은 **항상** ExecutionContext를 통해 노드 간 데이터를 전달해야 합니다.

**Details:**

- Thread-safe context (asyncio.Lock)
- 선행 노드 출력을 후속 노드 입력으로 매핑
- 변수 저장 및 조회 지원
- 워크플로우 레벨 변수 지원

**Interface:**
```python
class ExecutionContext:
    async def get_input(self, node: Node, edges: list[Edge]) -> dict
    async def set_output(self, node_id: UUID, data: dict) -> None
    async def get_variable(self, name: str) -> Any
    async def set_variable(self, name: str, value: Any) -> None
```

---

### Error Handling Requirements

#### REQ-011-004: 지수 백오프 재시도

**Event-Driven Requirement**

**WHEN** 노드 실행이 일시적 오류로 실패하면, **THEN** 시스템은 노드의 retry_config에 따라 지수 백오프로 재시도해야 합니다.

**Details:**

- Node.retry_config: `{"max_retries": 3, "delay": 1}`
- Exponential backoff: `delay * (2 ** attempt)`
- retry_count를 NodeExecution에 기록
- 최종 실패 시 error_message 저장

**Retry Pattern:**
```python
for attempt in range(max_retries + 1):
    try:
        result = await self._execute_node(node, context)
        return result
    except TransientError:
        if attempt < max_retries:
            await asyncio.sleep(delay * (2 ** attempt))
        else:
            raise
```

#### REQ-011-005: 실패 격리 정책

**Event-Driven Requirement**

**WHEN** 노드가 실패하면, **THEN** 시스템은 해당 노드의 모든 하류(downstream) 노드를 BLOCKED로 표시해야 합니다.

**Details:**

- BFS로 실패 노드의 모든 하류 노드 탐색
- 하류 노드를 SKIPPED 상태로 표시
- 독립적인 다른 브랜치는 계속 실행
- 실패 원인을 로그에 기록

**Error Response:**
```json
{
  "node_id": "tool-1",
  "status": "FAILED",
  "error_message": "Connection timeout",
  "blocked_downstream": ["agent-1", "aggregator-1"]
}
```

---

### Node Type Specific Requirements

#### REQ-011-006: 조건 노드 분기 처리

**Event-Driven Requirement**

**WHEN** CONDITION 타입 노드를 실행하면, **THEN** 시스템은 조건을 평가하고 매칭되는 엣지만 따라가야 합니다.

**Details:**

- node.config에서 조건 표현식 파싱
- context 변수를 사용하여 조건 평가
- 우선순위(priority)에 따라 엣지 선택
- 매칭되지 않는 경로의 노드는 SKIPPED

**Condition Evaluation:**
```python
# Edge conditions: {"expression": "rsi < 30", "handle": "oversold"}
for edge in sorted(outgoing_edges, key=lambda e: e.priority):
    if evaluate_condition(edge.condition, context):
        return [edge.target_node_id]
return []  # No matching condition
```

#### REQ-011-007: 트리거 노드 처리

**Event-Driven Requirement**

**WHEN** 워크플로우 실행이 시작되면, **THEN** 시스템은 TRIGGER 노드를 실행하고 입력 데이터를 컨텍스트에 저장해야 합니다.

**Details:**

- 입력 데이터를 ExecutionContext.variables에 저장
- 트리거 메타데이터 (trigger_type, triggered_at) 기록
- 트리거 노드는 항상 레벨 0

---

### Timeout and Cancellation Requirements

#### REQ-011-008: 노드 타임아웃 처리

**Unwanted Behavior Requirement**

시스템은 **절대** Node.timeout_seconds를 초과하여 노드를 실행해서는 안 됩니다.

**Details:**

- asyncio.timeout() 사용
- 타임아웃 시 NodeTimeoutError 발생
- 노드를 FAILED 상태로 표시
- 타임아웃 정보를 로그에 기록

**Timeout Pattern:**
```python
try:
    async with asyncio.timeout(node.timeout_seconds):
        result = await self._execute_node(node, context)
except asyncio.TimeoutError:
    raise NodeTimeoutError(f"Node {node.id} timed out after {node.timeout_seconds}s")
```

#### REQ-011-009: 워크플로우 취소 지원

**Event-Driven Requirement**

**WHEN** 워크플로우 취소가 요청되면, **THEN** 시스템은 실행 중인 모든 노드를 gracefully 종료해야 합니다.

**Details:**

- Cancellation flag 설정
- 실행 중인 태스크 취소
- 대기 중인 노드를 CANCELLED 상태로 표시
- 이미 완료된 노드는 그대로 유지

---

### Logging and Monitoring Requirements

#### REQ-011-010: ExecutionLog 통합

**Ubiquitous Requirement**

시스템은 **항상** 워크플로우 및 노드 실행 이벤트를 ExecutionLog에 기록해야 합니다.

**Details:**

- 워크플로우 시작/종료 로그
- 각 노드 실행 시작/완료/실패 로그
- 에러 발생 시 ERROR 레벨 로그
- 재시도 시 WARN 레벨 로그

**Log Levels:**
- INFO: 정상 실행 이벤트
- WARN: 재시도, 경고 조건
- ERROR: 실패, 타임아웃
- DEBUG: 상세 실행 정보

---

### State Management Requirements

#### REQ-011-011: 실행 상태 전이

**Ubiquitous Requirement**

시스템은 **항상** 올바른 상태 전이를 따라야 합니다.

**WorkflowExecution 상태 전이:**
```
PENDING -> RUNNING -> COMPLETED
                   -> FAILED
         -> CANCELLED
```

**NodeExecution 상태 전이:**
```
PENDING -> RUNNING -> COMPLETED
                   -> FAILED
                   -> SKIPPED (조건 미충족 또는 상류 실패)
         -> CANCELLED
```

#### REQ-011-012: 동시성 제어

**Unwanted Behavior Requirement**

시스템은 **절대** 지정된 max_parallel_nodes를 초과하여 동시에 노드를 실행해서는 안 됩니다.

**Details:**

- asyncio.Semaphore 사용
- 기본값: 10개 동시 노드
- 구성 가능한 제한
- 리소스 고갈 방지

---

## Specifications

### SPEC-011-A: File Structure

```
backend/
  app/
    services/
      workflow/                    # Package from SPEC-010
        __init__.py               # Add new exports
        executor.py               # NEW - Workflow Executor
        context.py                # NEW - ExecutionContext
        # Existing from SPEC-010:
        validator.py              # DAG Validator
        graph.py                  # Graph data structures
        algorithms.py             # Graph algorithms
        exceptions.py             # Add execution exceptions
  tests/
    services/
      workflow/
        test_executor.py          # NEW - Executor tests
        test_context.py           # NEW - Context tests
        test_integration.py       # NEW - Integration tests
```

### SPEC-011-B: ExecutionContext Interface

```python
# services/workflow/context.py
from typing import Any, Optional
from uuid import UUID
import asyncio

from app.models.workflow import Node, Edge


class ExecutionContext:
    """Thread-safe context for passing data between nodes.

    TAG: [SPEC-011] [EXECUTION] [CONTEXT]

    Provides:
    - Node output storage and retrieval
    - Variable management for workflow-level data
    - Async-safe operations with Lock
    - Input resolution from predecessor nodes
    """

    def __init__(
        self,
        workflow_execution_id: UUID,
        input_data: dict[str, Any],
    ):
        self._workflow_execution_id = workflow_execution_id
        self._variables: dict[str, Any] = dict(input_data)
        self._node_outputs: dict[UUID, dict[str, Any]] = {}
        self._errors: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    @property
    def workflow_execution_id(self) -> UUID:
        return self._workflow_execution_id

    async def get_input(
        self,
        node: Node,
        incoming_edges: list[Edge],
    ) -> dict[str, Any]:
        """Get input data for a node from predecessor outputs.

        Aggregates outputs from all predecessor nodes based on incoming edges.
        """
        async with self._lock:
            input_data = dict(self._variables)  # Start with workflow variables
            for edge in incoming_edges:
                predecessor_output = self._node_outputs.get(
                    edge.source_node_id, {}
                )
                # Apply edge mapping if defined
                if edge.condition and "mapping" in edge.condition:
                    # Custom mapping logic
                    pass
                else:
                    input_data.update(predecessor_output)
            return input_data

    async def set_output(
        self,
        node_id: UUID,
        data: dict[str, Any],
    ) -> None:
        """Store output data from a node."""
        async with self._lock:
            self._node_outputs[node_id] = data

    async def get_output(self, node_id: UUID) -> Optional[dict[str, Any]]:
        """Get output data for a specific node."""
        async with self._lock:
            return self._node_outputs.get(node_id)

    async def get_variable(self, name: str) -> Any:
        """Get a workflow variable."""
        async with self._lock:
            return self._variables.get(name)

    async def set_variable(self, name: str, value: Any) -> None:
        """Set a workflow variable."""
        async with self._lock:
            self._variables[name] = value

    async def add_error(
        self,
        node_id: UUID,
        error_type: str,
        message: str,
    ) -> None:
        """Record an execution error."""
        async with self._lock:
            self._errors.append({
                "node_id": str(node_id),
                "error_type": error_type,
                "message": message,
            })

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self._errors) > 0

    async def get_all_outputs(self) -> dict[UUID, dict[str, Any]]:
        """Get all node outputs."""
        async with self._lock:
            return dict(self._node_outputs)
```

### SPEC-011-C: WorkflowExecutor Interface

```python
# services/workflow/executor.py
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID
from datetime import datetime, UTC
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.models.workflow import Workflow, Node, Edge
from app.models.execution import WorkflowExecution, NodeExecution
from app.models.enums import ExecutionStatus, NodeType, TriggerType, LogLevel
from app.services.execution_service import (
    WorkflowExecutionService,
    NodeExecutionService,
    ExecutionLogService,
)
from app.services.workflow.context import ExecutionContext
from app.services.workflow.validator import DAGValidator
from app.services.workflow import algorithms
from app.services.workflow.graph import Graph
from app.services.workflow.exceptions import (
    DAGValidationError,
    NodeTimeoutError,
    ExecutionCancelledError,
)


@dataclass
class NodeResult:
    """Result of a single node execution."""
    node_id: UUID
    status: ExecutionStatus
    output_data: dict[str, Any]
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    workflow_execution_id: UUID
    status: ExecutionStatus
    output_data: dict[str, Any]
    node_results: list[NodeResult]
    duration_seconds: float
    error_message: Optional[str] = None


class WorkflowExecutor:
    """DAG-based workflow execution engine.

    TAG: [SPEC-011] [EXECUTION] [ENGINE]

    Features:
    - Topological sort based execution order
    - Parallel execution within levels (asyncio.TaskGroup)
    - ExecutionContext for node data passing
    - Error handling with retry and isolation
    - Timeout and cancellation support
    """

    def __init__(
        self,
        db: AsyncSession,
        max_parallel_nodes: int = 10,
    ):
        self.db = db
        self._semaphore = asyncio.Semaphore(max_parallel_nodes)
        self._cancelled = False
        self._validator = DAGValidator(db)

    async def execute(
        self,
        workflow_id: UUID,
        input_data: dict[str, Any],
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> ExecutionResult:
        """Execute a workflow.

        TAG: [SPEC-011] [EXECUTION]

        Steps:
        1. Load workflow with nodes and edges
        2. Validate DAG structure
        3. Create WorkflowExecution record
        4. Build DAG and topological sort
        5. Execute nodes level by level
        6. Return final result
        """
        start_time = datetime.now(UTC)

        # 1. Load workflow
        workflow = await self._load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # 2. Validate DAG
        validation = await self._validator.validate_workflow(workflow_id)
        if not validation.is_valid:
            raise DAGValidationError(
                message="Workflow validation failed",
                error_code="VALIDATION_FAILED",
                details={"errors": [e.model_dump() for e in validation.errors]},
            )

        # 3. Create WorkflowExecution
        execution = await WorkflowExecutionService.create(
            self.db,
            workflow_id=workflow_id,
            input_data=input_data,
            trigger_type=trigger_type,
        )
        await WorkflowExecutionService.start(self.db, execution.id)

        # 4. Build DAG and get execution order
        graph = self._build_graph(workflow)
        levels = algorithms.topological_sort_levels(graph)

        # 5. Create ExecutionContext
        context = ExecutionContext(execution.id, input_data)

        # 6. Execute level by level
        node_results: list[NodeResult] = []
        node_map = {node.id: node for node in workflow.nodes}
        edge_map = self._build_edge_map(workflow.edges)

        try:
            for level_idx, level_node_ids in enumerate(levels):
                level_nodes = [node_map[nid] for nid in level_node_ids]

                await self._log(
                    execution.id,
                    LogLevel.INFO,
                    f"Executing level {level_idx} with {len(level_nodes)} nodes",
                )

                level_results = await self._execute_level(
                    level_nodes,
                    context,
                    edge_map,
                    execution.id,
                )
                node_results.extend(level_results)

                # Check for failures
                failed = [r for r in level_results if r.status == ExecutionStatus.FAILED]
                if failed:
                    # Mark downstream nodes as blocked
                    await self._mark_downstream_blocked(
                        [r.node_id for r in failed],
                        graph,
                        levels[level_idx + 1:] if level_idx + 1 < len(levels) else [],
                        node_map,
                        execution.id,
                    )

            # 7. Complete workflow
            final_outputs = await context.get_all_outputs()
            await WorkflowExecutionService.complete(
                self.db,
                execution.id,
                output_data=final_outputs,
            )

            duration = (datetime.now(UTC) - start_time).total_seconds()

            return ExecutionResult(
                workflow_execution_id=execution.id,
                status=ExecutionStatus.COMPLETED,
                output_data=final_outputs,
                node_results=node_results,
                duration_seconds=duration,
            )

        except Exception as e:
            await WorkflowExecutionService.fail(
                self.db,
                execution.id,
                error_message=str(e),
            )
            duration = (datetime.now(UTC) - start_time).total_seconds()

            return ExecutionResult(
                workflow_execution_id=execution.id,
                status=ExecutionStatus.FAILED,
                output_data={},
                node_results=node_results,
                duration_seconds=duration,
                error_message=str(e),
            )

    async def cancel(self, execution_id: UUID) -> None:
        """Cancel a running workflow execution.

        TAG: [SPEC-011] [CANCELLATION]
        """
        self._cancelled = True
        await WorkflowExecutionService.cancel(self.db, execution_id)

    async def _execute_level(
        self,
        nodes: list[Node],
        context: ExecutionContext,
        edge_map: dict[UUID, list[Edge]],
        execution_id: UUID,
    ) -> list[NodeResult]:
        """Execute all nodes in a level in parallel."""
        if self._cancelled:
            raise ExecutionCancelledError("Workflow execution was cancelled")

        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    self._execute_node_with_semaphore(
                        node, context, edge_map, execution_id
                    )
                )
                for node in nodes
            ]

        return [task.result() for task in tasks]

    async def _execute_node_with_semaphore(
        self,
        node: Node,
        context: ExecutionContext,
        edge_map: dict[UUID, list[Edge]],
        execution_id: UUID,
    ) -> NodeResult:
        """Execute node with semaphore for concurrency control."""
        async with self._semaphore:
            return await self._execute_node_with_retry(
                node, context, edge_map, execution_id
            )

    async def _execute_node_with_retry(
        self,
        node: Node,
        context: ExecutionContext,
        edge_map: dict[UUID, list[Edge]],
        execution_id: UUID,
    ) -> NodeResult:
        """Execute node with retry logic."""
        max_retries = node.retry_config.get("max_retries", 3)
        delay = node.retry_config.get("delay", 1)

        # Create NodeExecution record
        node_execution = await NodeExecutionService.create(
            self.db,
            workflow_execution_id=execution_id,
            node_id=node.id,
            execution_order=0,  # TODO: Calculate actual order
        )

        for attempt in range(max_retries + 1):
            try:
                result = await self._execute_node_with_timeout(
                    node, context, edge_map, node_execution.id
                )
                return result

            except NodeTimeoutError as e:
                await NodeExecutionService.fail(
                    self.db,
                    node_execution.id,
                    error_message=str(e),
                )
                return NodeResult(
                    node_id=node.id,
                    status=ExecutionStatus.FAILED,
                    output_data={},
                    error_message=str(e),
                )

            except Exception as e:
                if attempt < max_retries:
                    await NodeExecutionService.increment_retry(
                        self.db, node_execution.id
                    )
                    await self._log(
                        execution_id,
                        LogLevel.WARN,
                        f"Node {node.name} failed, retrying ({attempt + 1}/{max_retries})",
                        node_execution.id,
                    )
                    await asyncio.sleep(delay * (2 ** attempt))
                else:
                    await NodeExecutionService.fail(
                        self.db,
                        node_execution.id,
                        error_message=str(e),
                    )
                    return NodeResult(
                        node_id=node.id,
                        status=ExecutionStatus.FAILED,
                        output_data={},
                        error_message=str(e),
                    )

        # Should not reach here
        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.FAILED,
            output_data={},
            error_message="Unknown error",
        )

    async def _execute_node_with_timeout(
        self,
        node: Node,
        context: ExecutionContext,
        edge_map: dict[UUID, list[Edge]],
        node_execution_id: UUID,
    ) -> NodeResult:
        """Execute node with timeout."""
        start_time = datetime.now(UTC)

        await NodeExecutionService.start(self.db, node_execution_id, {})

        try:
            async with asyncio.timeout(node.timeout_seconds):
                result = await self._execute_node(node, context, edge_map)

            await NodeExecutionService.complete(
                self.db,
                node_execution_id,
                output_data=result.output_data,
            )

            return result

        except asyncio.TimeoutError:
            raise NodeTimeoutError(
                f"Node {node.name} timed out after {node.timeout_seconds}s"
            )

    async def _execute_node(
        self,
        node: Node,
        context: ExecutionContext,
        edge_map: dict[UUID, list[Edge]],
    ) -> NodeResult:
        """Execute a single node.

        This is a placeholder that will be replaced by NodeProcessor (SPEC-012).
        """
        start_time = datetime.now(UTC)

        # Get input from predecessors
        incoming_edges = [e for e in edge_map.get(node.id, [])
                         if e.target_node_id == node.id]
        input_data = await context.get_input(node, incoming_edges)

        # Execute based on node type
        # TODO: Delegate to NodeProcessor (SPEC-012)
        output_data: dict[str, Any] = {}

        if node.node_type == NodeType.TRIGGER:
            # Trigger nodes pass through input data
            output_data = input_data

        elif node.node_type == NodeType.CONDITION:
            # Evaluate condition and set result
            # TODO: Implement condition evaluation
            output_data = {"condition_result": True}

        else:
            # Other nodes: placeholder
            output_data = {"processed": True, "input": input_data}

        # Store output
        await context.set_output(node.id, output_data)

        duration = (datetime.now(UTC) - start_time).total_seconds()

        return NodeResult(
            node_id=node.id,
            status=ExecutionStatus.COMPLETED,
            output_data=output_data,
            duration_seconds=duration,
        )

    # Helper methods

    async def _load_workflow(self, workflow_id: UUID) -> Optional[Workflow]:
        """Load workflow with nodes and edges."""
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .where(Workflow.deleted_at.is_(None))
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
        )
        return result.scalar_one_or_none()

    def _build_graph(self, workflow: Workflow) -> Graph[UUID]:
        """Build graph from workflow."""
        graph = Graph[UUID]()
        for node in workflow.nodes:
            graph.add_node(node.id)
        for edge in workflow.edges:
            graph.add_edge(edge.source_node_id, edge.target_node_id)
        return graph

    def _build_edge_map(
        self,
        edges: list[Edge],
    ) -> dict[UUID, list[Edge]]:
        """Build edge lookup map."""
        edge_map: dict[UUID, list[Edge]] = {}
        for edge in edges:
            if edge.target_node_id not in edge_map:
                edge_map[edge.target_node_id] = []
            edge_map[edge.target_node_id].append(edge)
        return edge_map

    async def _mark_downstream_blocked(
        self,
        failed_node_ids: list[UUID],
        graph: Graph[UUID],
        remaining_levels: list[list[UUID]],
        node_map: dict[UUID, Node],
        execution_id: UUID,
    ) -> None:
        """Mark downstream nodes as blocked due to upstream failure."""
        blocked = set()
        for failed_id in failed_node_ids:
            queue = list(graph.get_successors(failed_id))
            while queue:
                node_id = queue.pop(0)
                if node_id not in blocked:
                    blocked.add(node_id)
                    queue.extend(graph.get_successors(node_id))

        for node_id in blocked:
            await self._log(
                execution_id,
                LogLevel.WARN,
                f"Node {node_map[node_id].name} blocked due to upstream failure",
            )

    async def _log(
        self,
        execution_id: UUID,
        level: LogLevel,
        message: str,
        node_execution_id: Optional[UUID] = None,
        data: Optional[dict] = None,
    ) -> None:
        """Log execution event."""
        await ExecutionLogService.create(
            self.db,
            workflow_execution_id=execution_id,
            node_execution_id=node_execution_id,
            level=level,
            message=message,
            data=data,
        )
```

### SPEC-011-D: Exception Definitions

```python
# Add to services/workflow/exceptions.py

class ExecutionError(Exception):
    """Base exception for execution errors.

    TAG: [SPEC-011] [EXECUTION] [EXCEPTIONS]
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[UUID] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.node_id = node_id
        self.details = details or {}


class NodeTimeoutError(ExecutionError):
    """Raised when node execution exceeds timeout."""

    def __init__(self, message: str, node_id: Optional[UUID] = None):
        super().__init__(message, node_id)


class NodeExecutionError(ExecutionError):
    """Raised when node execution fails."""

    def __init__(
        self,
        message: str,
        node_id: UUID,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, node_id)
        self.original_error = original_error


class ExecutionCancelledError(ExecutionError):
    """Raised when execution is cancelled."""

    def __init__(self, message: str = "Execution was cancelled"):
        super().__init__(message)


class ConditionEvaluationError(ExecutionError):
    """Raised when condition evaluation fails."""

    def __init__(self, message: str, node_id: UUID, expression: str):
        super().__init__(message, node_id, {"expression": expression})
```

---

## Constraints

### Technical Constraints

- Python 3.12+ (asyncio.TaskGroup requires 3.11+)
- SPEC-010 DAG Validator 의존
- 기존 execution_service.py와 통합
- Pydantic v2 `model_config = ConfigDict(from_attributes=True)`

### Performance Constraints

- 100개 노드 워크플로우 실행 시 오버헤드 < 500ms
- 메모리 사용량: 그래프 크기의 3배 이하
- 동시 실행 노드 기본 제한: 10개

### Security Constraints

- 입력 데이터 검증
- 조건 표현식 샌드박스 실행
- 민감 데이터 로깅 마스킹

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base models and mixins
- SPEC-003: Workflow, Node, Edge models
- SPEC-005: WorkflowExecution, NodeExecution, ExecutionLog models
- SPEC-010: DAG Validator (topological sort, cycle detection)

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | API framework |
| pydantic | >=2.10.0 | Schema validation |
| sqlalchemy[asyncio] | >=2.0.0 | Database access |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 노드 실행 무한 대기 | Medium | High | 타임아웃 및 취소 메커니즘 |
| 메모리 누수 | Low | Medium | Context 정리, 약한 참조 |
| 동시성 문제 | Medium | High | asyncio.Lock 사용 |
| SPEC-010 미완성 | Low | High | 병렬 개발, 인터페이스 추상화 |

---

## Related SPECs

- **SPEC-001**: Database Foundation Setup (base models)
- **SPEC-003**: Workflow Domain Models (Workflow, Node, Edge)
- **SPEC-005**: Execution Tracking Models (WorkflowExecution, NodeExecution)
- **SPEC-010**: DAG Validation Service (topological sort, validation)
- **SPEC-012**: Node Processor Framework (개별 노드 타입 처리)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1.0 | 2026-01-16 | workflow-tdd | WorkflowExecutor 구현 (REQ-011-001~005, 007~011), ExecutionContext 구현 (100% 커버리지), Execution 예외 클래스 구현 (100% 커버리지), REQ-011-006는 SPEC-012로 이관 |
| 1.0.0 | 2026-01-15 | workflow-spec | Initial SPEC creation |
