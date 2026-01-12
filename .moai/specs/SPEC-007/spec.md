# SPEC-007: Workflow API Endpoints

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-007 |
| Title | Workflow API Endpoints |
| Created | 2026-01-12 |
| Completed | 2026-01-12 |
| Status | Completed |
| Priority | High (P0) |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | Phase 2 - API Layer |

## Tags

`[SPEC-007]` `[API]` `[WORKFLOW]` `[EXECUTION]` `[BACKEND]` `[FASTAPI]`

---

## Overview

이 SPEC은 PasteTrader 워크플로우 엔진의 API 엔드포인트를 정의합니다. FastAPI + Pydantic v2 스키마 + 의존성 주입 패턴을 사용하여 RESTful API를 구현합니다. Workflow, Node, Edge의 CRUD 작업과 WorkflowExecution, NodeExecution, ExecutionLog의 조회 및 관리 기능을 제공합니다.

### Scope

- Workflow CRUD API (`/api/v1/workflows`)
- Node CRUD API (nested under `/workflows/{id}/nodes`)
- Edge CRUD API (nested under `/workflows/{id}/edges`)
- WorkflowExecution API (`/api/v1/executions`)
- NodeExecution API (nested under executions)
- ExecutionLog API (nested under executions)
- Graph bulk update endpoint

### Out of Scope

- Authentication/Authorization (별도 SPEC)
- Real-time WebSocket (별도 SPEC)
- Workflow Engine execution logic (SPEC-010, SPEC-011)
- Scheduler API (SPEC-008)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.115.x | API framework |
| Pydantic | 2.10.x | Schema validation |
| SQLAlchemy | 2.0.x | Async ORM |
| asyncpg | 0.30.x | PostgreSQL async driver |

### Configuration Dependencies

- SPEC-001에서 정의된 Base 모델 및 Mixin 사용
- SPEC-003에서 정의된 Workflow, Node, Edge 모델 참조
- SPEC-005에서 정의된 WorkflowExecution, NodeExecution, ExecutionLog 모델 참조
- `backend/app/models/enums.py`: ExecutionStatus, TriggerType, LogLevel enum

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| FastAPI의 의존성 주입으로 DB 세션 관리 가능 | High | FastAPI 공식 문서 | 커스텀 미들웨어 필요 |
| Pydantic v2 model_validate로 ORM 변환 가능 | High | Pydantic v2 공식 문서 | Serializer 별도 구현 필요 |
| 단일 요청에서 최대 100개 노드/엣지 처리 | Medium | 일반적인 워크플로우 크기 | Batch 처리 분리 필요 |
| API 응답 시간은 500ms 이내 | High | 설계 목표 | 캐싱 전략 필요 |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| RESTful 패턴으로 충분한 표현력 확보 | High | GraphQL 도입 검토 필요 |
| 중첩 라우팅이 사용자 친화적 | Medium | 평면 라우팅으로 변경 필요 |
| Pagination은 offset 기반으로 충분 | Medium | Cursor 기반 페이지네이션 필요 |

---

## Requirements

### Workflow Endpoints

#### REQ-001: Workflow 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows`를 요청하면, **THEN** 페이지네이션된 워크플로우 목록을 반환해야 합니다.

**Details:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | int | No | 1 | 페이지 번호 |
| size | int | No | 20 | 페이지 크기 (max: 100) |
| sort_by | str | No | created_at | 정렬 필드 |
| sort_order | str | No | desc | 정렬 방향 (asc, desc) |
| is_active | bool | No | None | 활성화 필터 |

**Response:** `200 OK` with `PaginatedResponse[WorkflowResponse]`

#### REQ-002: Workflow 생성

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows`를 요청하면, **THEN** 새 워크플로우를 생성하고 반환해야 합니다.

**Request Body:** `WorkflowCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Yes | 워크플로우 이름 (max: 255) |
| description | str | No | 설명 |
| config | dict | No | 전역 설정 |
| variables | dict | No | 변수 |
| is_active | bool | No | 활성화 상태 (default: true) |

**Response:** `201 Created` with `WorkflowResponse`

#### REQ-003: Workflow 단일 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}`를 요청하면, **THEN** 해당 워크플로우를 반환해야 합니다.

**Response:** `200 OK` with `WorkflowResponse`

**Error:** `404 Not Found` if workflow not found

#### REQ-004: Workflow 전체 조회 (with Nodes/Edges)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}/full`을 요청하면, **THEN** 노드와 엣지를 포함한 전체 워크플로우를 반환해야 합니다.

**Response:** `200 OK` with `WorkflowFullResponse`

```json
{
  "id": "uuid",
  "name": "workflow_name",
  "nodes": [...],
  "edges": [...]
}
```

#### REQ-005: Workflow 수정

**Event-Driven Requirement**

**WHEN** 클라이언트가 `PUT /api/v1/workflows/{id}`를 요청하면, **THEN** 워크플로우를 업데이트하고 버전을 증가시켜야 합니다.

**Request Body:** `WorkflowUpdate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | No | 워크플로우 이름 |
| description | str | No | 설명 |
| config | dict | No | 전역 설정 |
| variables | dict | No | 변수 |
| is_active | bool | No | 활성화 상태 |

**Response:** `200 OK` with `WorkflowResponse`

#### REQ-006: Workflow 삭제 (Soft Delete)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `DELETE /api/v1/workflows/{id}`를 요청하면, **THEN** 워크플로우를 소프트 삭제해야 합니다.

**Response:** `204 No Content`

#### REQ-007: Workflow 복제

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows/{id}/duplicate`를 요청하면, **THEN** 워크플로우와 모든 노드/엣지를 복제해야 합니다.

**Request Body:** `WorkflowDuplicate` (optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | No | 새 이름 (default: "Copy of {original}") |

**Response:** `201 Created` with `WorkflowResponse`

---

### Node Endpoints

#### REQ-008: Node 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}/nodes`를 요청하면, **THEN** 해당 워크플로우의 모든 노드를 반환해야 합니다.

**Response:** `200 OK` with `list[NodeResponse]`

#### REQ-009: Node 생성

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows/{id}/nodes`를 요청하면, **THEN** 새 노드를 생성하고 반환해야 합니다.

**Request Body:** `NodeCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Yes | 노드 이름 (max: 255) |
| node_type | NodeType | Yes | 노드 유형 |
| position_x | float | No | X 좌표 (default: 0.0) |
| position_y | float | No | Y 좌표 (default: 0.0) |
| config | dict | No | 노드 설정 |
| input_schema | dict | No | 입력 스키마 |
| output_schema | dict | No | 출력 스키마 |
| tool_id | UUID | No | 연결된 도구 ID |
| agent_id | UUID | No | 연결된 에이전트 ID |
| timeout_seconds | int | No | 타임아웃 (default: 300) |
| retry_config | dict | No | 재시도 설정 |

**Response:** `201 Created` with `NodeResponse`

#### REQ-010: Node 배치 생성

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows/{id}/nodes/batch`를 요청하면, **THEN** 여러 노드를 한 번에 생성해야 합니다.

**Request Body:** `NodeBatchCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| nodes | list[NodeCreate] | Yes | 생성할 노드 목록 (max: 100) |

**Response:** `201 Created` with `list[NodeResponse]`

**Validation Rules:**

| 검증 항목 | 조건 | 실패 시 응답 |
|----------|------|--------------|
| 최대 아이템 수 | nodes.length <= 100 | 400 Bad Request, error_code: BATCH_LIMIT_EXCEEDED |
| 중복 노드 이름 | 같은 workflow_id 내 유일 | 400 Bad Request, error_code: DUPLICATE_NODE_NAME |
| 유효하지 않은 node_type | NodeType enum 값 | 422 Unprocessable Entity, error_code: INVALID_NODE_TYPE |
| 누락된 필수 필드 | name, node_type 필수 | 422 Unprocessable Entity, error_code: MISSING_REQUIRED_FIELD |

**Partial Success Policy:**

전체 또는 전무 롤백: 배치 작업은 트랜잭션으로 처리하여, 하나의 항목이라도 실패하면 전체 배치가 롤백되어야 합니다.
**WHEN** 배치 내 어떤 노드 생성이라도 실패하면, **THEN** 시스템은 어떤 노드도 생성하지 않고 에러를 반환해야 합니다.

**Error Response Format:**
```json
{
  "detail": "Batch validation failed",
  "error_code": "BATCH_VALIDATION_FAILED",
  "validation_errors": [
    {
      "index": 5,
      "field": "name",
      "message": "Duplicate node name: 'data_processor'"
    },
    {
      "index": 12,
      "field": "node_type",
      "message": "Invalid node type: 'invalid_type'"
    }
  ]
}
```

#### REQ-011: Node 수정

**Event-Driven Requirement**

**WHEN** 클라이언트가 `PUT /api/v1/workflows/{id}/nodes/{node_id}`를 요청하면, **THEN** 노드를 업데이트해야 합니다.

**Request Body:** `NodeUpdate`

**Response:** `200 OK` with `NodeResponse`

#### REQ-012: Node 삭제

**Event-Driven Requirement**

**WHEN** 클라이언트가 `DELETE /api/v1/workflows/{id}/nodes/{node_id}`를 요청하면, **THEN** 노드와 연결된 엣지를 삭제해야 합니다.

**Response:** `204 No Content`

---

### Edge Endpoints

#### REQ-013: Edge 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}/edges`를 요청하면, **THEN** 해당 워크플로우의 모든 엣지를 반환해야 합니다.

**Response:** `200 OK` with `list[EdgeResponse]`

#### REQ-014: Edge 생성 (with DAG Validation)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows/{id}/edges`를 요청하면, **THEN** DAG 검증 후 새 엣지를 생성해야 합니다.

**Request Body:** `EdgeCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source_node_id | UUID | Yes | 출발 노드 ID |
| target_node_id | UUID | Yes | 도착 노드 ID |
| source_handle | str | No | 출발 핸들 |
| target_handle | str | No | 도착 핸들 |
| condition | dict | No | 조건 |
| priority | int | No | 우선순위 (default: 0) |
| label | str | No | 레이블 |

**Response:** `201 Created` with `EdgeResponse`

**DAG Validation Rules:**

| 검증 | 조건 | 에러 코드 |
|------|------|-----------|
| 자기 루프 방지 | source_node_id != target_node_id | SELF_LOOP_DETECTED |
| 사이클 감지 | 새 엣지 추가 후 그래프에 사이클 없음 | CYCLE_DETECTED |
| 노드 존재 | source, target 노드가 워크플로우에 존재 | NODE_NOT_FOUND |
| 중복 엣지 | 같은 source-target 엣지 미존재 | DUPLICATE_EDGE |

**Error Response Schemas:**

**1. 자기 루프 에러 (400 Bad Request):**
```json
{
  "detail": "Cannot create edge from node to itself",
  "error_code": "SELF_LOOP_DETECTED",
  "source_node_id": "uuid-123",
  "target_node_id": "uuid-123",
  "message": "Self-loops are not allowed in workflow graphs"
}
```

**2. 사이클 감지 에러 (400 Bad Request):**
```json
{
  "detail": "Adding this edge would create a cycle",
  "error_code": "CYCLE_DETECTED",
  "proposed_edge": {
    "source_node_id": "node-c",
    "target_node_id": "node-a"
  },
  "cycle_path": ["node-a", "node-b", "node-c", "node-a"],
  "message": "Edge would create cycle: node-c -> node-a completes cycle"
}
```

**3. 노드 미존재 에러 (404 Not Found):**
```json
{
  "detail": "Source or target node not found in workflow",
  "error_code": "NODE_NOT_FOUND",
  "workflow_id": "workflow-uuid",
  "source_node_id": "missing-node-uuid",
  "target_node_id": "valid-node-uuid",
  "message": "Source node 'missing-node-uuid' does not exist"
}
```

**4. 중복 엣지 에러 (409 Conflict):**
```json
{
  "detail": "Edge between these nodes already exists",
  "error_code": "DUPLICATE_EDGE",
  "existing_edge_id": "edge-uuid-456",
  "source_node_id": "node-a",
  "target_node_id": "node-b",
  "message": "Use PUT /edges/{id} to update existing edge"
}
```

**Cycle Detection Algorithm:**
- DFS(Depth-First Search) 사용하여 백트래킹 경로 추적
- 새 엣지 추가 후 source_node에서 시작하는 순환 경로 탐지
- 경로를 노드 ID 목록으로 반환하여 디버깅 지원

#### REQ-015: Edge 배치 생성

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/workflows/{id}/edges/batch`를 요청하면, **THEN** DAG 검증 후 여러 엣지를 한 번에 생성해야 합니다.

**Request Body:** `EdgeBatchCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| edges | list[EdgeCreate] | Yes | 생성할 엣지 목록 (max: 100) |

**Response:** `201 Created` with `list[EdgeResponse]`

**Validation Rules:**

| 검증 항목 | 조건 | 실패 시 응답 |
|----------|------|--------------|
| 최대 아이템 수 | edges.length <= 100 | 400 Bad Request |
| 존재하는 노드 ID | source/target 노드 존재 | 404 Not Found, error_code: NODE_NOT_FOUND |
| 중복 엣지 | 같은 source-target 쌍 | 400 Bad Request, error_code: DUPLICATE_EDGE |
| 자기 루프 | source != target | 400 Bad Request, error_code: SELF_LOOP_DETECTED |

**DAG Integrity Check:**

배치 엣지 생성 후 전체 워크플로우 그래프가 DAG인지 검증해야 합니다.
**WHEN** 사이클이 감지되면, **THEN** 모든 엣지 생성을 롤백하고 에러를 반환해야 합니다.

**Error Response Format (DAG Cycle):**
```json
{
  "detail": "Cycle detected in workflow graph",
  "error_code": "CYCLE_DETECTED",
  "cycle_path": ["node-a", "node-b", "node-c", "node-a"],
  "message": "Adding these edges would create a cycle"
}
```

#### REQ-016: Edge 삭제

**Event-Driven Requirement**

**WHEN** 클라이언트가 `DELETE /api/v1/workflows/{id}/edges/{edge_id}`를 요청하면, **THEN** 엣지를 삭제해야 합니다.

**Response:** `204 No Content`

---

### Graph Update

#### REQ-017: Graph 일괄 업데이트

**Event-Driven Requirement**

**WHEN** 클라이언트가 `PUT /api/v1/workflows/{id}/graph`를 요청하면, **THEN** 노드와 엣지를 일괄 업데이트하고 DAG 검증을 수행해야 합니다.

**Request Body:** `GraphUpdate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| nodes_to_create | list[NodeCreate] | No | 생성할 노드 |
| nodes_to_update | list[NodeUpdateWithId] | No | 수정할 노드 |
| nodes_to_delete | list[UUID] | No | 삭제할 노드 ID |
| edges_to_create | list[EdgeCreate] | No | 생성할 엣지 |
| edges_to_delete | list[UUID] | No | 삭제할 엣지 ID |

**Validation Sequence:**

1. 삭제할 노드가 연결된 엣지 존재 확인 (연결된 엣지 자동 삭제)
2. 생성할 노드/엣지 데이터 검증
3. 업데이트할 노드 존재 확인
4. 최종 그래프 DAG 무결성 검증

**Atomic Transaction Policy:**

**IF** 어떤 작업이라도 실패하면, **THEN** 시스템은 모든 변경 사항을 롤백해야 합니다.
**WHEN** DAG 검증이 실패하면, **THEN** 어떤 노드나 엣지도 생성/수정/삭제하지 않아야 합니다.

**Error Response Format:**
```json
{
  "detail": "Graph update failed: cycle detected",
  "error_code": "GRAPH_UPDATE_FAILED",
  "validation_stage": "dag_integrity_check",
  "cycle_path": ["node-1", "node-2", "node-3", "node-1"],
  "rollback_performed": true
}
```

**Response:** `200 OK` with `GraphUpdateResponse`

```json
{
  "workflow_id": "uuid",
  "version": 2,
  "nodes_created": 3,
  "nodes_updated": 1,
  "nodes_deleted": 0,
  "edges_created": 2,
  "edges_deleted": 0,
  "validation_passed": true,
  "warnings": ["Deleted 2 edges connected to removed nodes"]
}
```

#### REQ-DAG-001: DAG 검증 서비스 인터페이스

**Ubiquitous Requirement**

시스템은 워크플로우 그래프의 DAG 무결성을 검증하는 서비스를 제공해야 합니다.

**Service Methods:**

- `validate_cycle_detection(workflow_id: UUID, new_edges: list[EdgeCreate]) -> CycleDetectionResult`
  - 새 엣지 추가 후 그래프의 사이클 감지 수행
  - 사이클 경로 반환

- `find_cycle_path(workflow_id: UUID) -> list[str] | None`
  - 현재 워크플로우 그래프에서 사이클 경로 탐지
  - 사이클이 없으면 None 반환

- `validate_node_deletion(workflow_id: UUID, node_id: UUID) -> DeletionValidationResult`
  - 노드 삭제 시 그래프 무결성 검증
  - 연결된 엣지 자동 삭제 가능성 확인

**Result Schema:**

```python
class CycleDetectionResult(BaseModel):
    """DAG 사이클 감지 결과."""
    is_valid: bool
    has_cycle: bool
    cycle_path: list[str] | None = None
    error_message: str | None = None

class DeletionValidationResult(BaseModel):
    """노드 삭제 검증 결과."""
    can_delete: bool
    connected_edges_count: int
    connected_edge_ids: list[UUID]
    warning_message: str | None = None
```

**Usage Context:**

이 서비스는 다음 엔드포인트에서 사용됩니다:
- REQ-014: Edge 생성 (단일 엣지 DAG 검증)
- REQ-015: Edge 배치 생성 (배치 엣지 DAG 검증)
- REQ-017: Graph 일괄 업데이트 (전체 그래프 DAG 검증)

---

### Execution Endpoints

#### REQ-018: Execution 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions`를 요청하면, **THEN** 페이지네이션된 실행 목록을 반환해야 합니다.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | int | No | 1 | 페이지 번호 |
| size | int | No | 20 | 페이지 크기 |
| workflow_id | UUID | No | None | 워크플로우 필터 |
| status | ExecutionStatus | No | None | 상태 필터 |
| trigger_type | TriggerType | No | None | 트리거 유형 필터 |

**Response:** `200 OK` with `PaginatedResponse[ExecutionResponse]`

**Error Conditions:**

| 조건 | HTTP 상태 | 에러 코드 | 메시지 |
|------|-----------|-----------|--------|
| 유효하지 않은 workflow_id | 400 Bad Request | INVALID_WORKFLOW_ID | "UUID format invalid" |
| 존재하지 않는 workflow_id | 404 Not Found | WORKFLOW_NOT_FOUND | "Workflow {id} does not exist" |
| 유효하지 않은 status 값 | 400 Bad Request | INVALID_STATUS | "Status must be one of: pending, running, completed, failed, cancelled" |
| 페이지 번호 범위 초과 | 400 Bad Request | PAGE_OUT_OF_RANGE | "Page {page} exceeds total pages {total}" |

**Error Response Format:**
```json
{
  "detail": "Invalid parameter",
  "code": "INVALID_SIZE",
  "field": "size",
  "provided": 150,
  "valid_range": "1-100",
  "message": "Page size must be between 1 and 100"
}
```

#### REQ-019: Execution 생성 (시작)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/executions`를 요청하면, **THEN** 새 실행을 생성하고 시작해야 합니다.

**Request Body:** `ExecutionCreate`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| workflow_id | UUID | Yes | 실행할 워크플로우 ID |
| trigger_type | TriggerType | No | 트리거 유형 (default: manual) |
| input_data | dict | No | 입력 데이터 |
| context | dict | No | 실행 컨텍스트 |
| metadata | dict | No | 메타데이터 |

**Response:** `201 Created` with `ExecutionResponse`

**Error Conditions:**

| 조건 | HTTP 상태 | 에러 코드 |
|------|-----------|-----------|
| workflow_id 누락 | 422 Unprocessable Entity | MISSING_WORKFLOW_ID |
| 존재하지 않는 workflow_id | 404 Not Found | WORKFLOW_NOT_FOUND |
| 비활성 워크플로우 | 400 Bad Request | WORKFLOW_INACTIVE |
| 이미 실행 중인 실행 | 409 Conflict | EXECUTION_ALREADY_RUNNING |
| 워크플로우 검증 실패 | 400 Bad Request | WORKFLOW_VALIDATION_FAILED |

**Error Response Examples:**

1. 비활성 워크플로우:
```json
{
  "detail": "Cannot start execution for inactive workflow",
  "error_code": "WORKFLOW_INACTIVE",
  "workflow_id": "uuid",
  "workflow_status": "inactive",
  "message": "Activate the workflow before starting execution",
  "suggestion": "PUT /api/v1/workflows/{id} with is_active=true"
}
```

2. 워크플로우 검증 실패:
```json
{
  "detail": "Workflow validation failed",
  "error_code": "WORKFLOW_VALIDATION_FAILED",
  "workflow_id": "uuid",
  "validation_errors": [
    {
      "node_id": "node-1",
      "error": "Missing required tool configuration"
    },
    {
      "node_id": "node-2",
      "error": "Invalid input schema"
    }
  ]
}
```

#### REQ-020: Execution 단일 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}`를 요청하면, **THEN** 해당 실행 정보를 반환해야 합니다.

**Response:** `200 OK` with `ExecutionResponse`

#### REQ-021: Execution 상세 조회 (with Nodes and Logs)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/detail`을 요청하면, **THEN** 노드 실행과 로그를 포함한 상세 정보를 반환해야 합니다.

**Response:** `200 OK` with `ExecutionDetailResponse`

```json
{
  "id": "uuid",
  "workflow_id": "uuid",
  "status": "completed",
  "node_executions": [...],
  "recent_logs": [...]
}
```

#### REQ-022: Execution 취소

**Event-Driven Requirement**

**WHEN** 클라이언트가 `POST /api/v1/executions/{id}/cancel`을 요청하면, **THEN** 실행을 취소해야 합니다.

**Response:** `200 OK` with `ExecutionResponse`

**Valid State Transitions:**

| 현재 상태 | 취소 가능 | 에러 코드 |
|----------|-----------|-----------|
| pending | Yes | - |
| running | Yes | - |
| completed | No | INVALID_STATE_TRANSITION |
| failed | No | INVALID_STATE_TRANSITION |
| cancelled | No | ALREADY_CANCELLED |

**Error Response Format (Invalid State):**
```json
{
  "detail": "Cannot cancel execution in current state",
  "error_code": "INVALID_STATE_TRANSITION",
  "execution_id": "uuid",
  "current_status": "completed",
  "requested_action": "cancel",
  "allowed_transitions": ["pending -> cancelled", "running -> cancelled"],
  "message": "Execution is already completed and cannot be cancelled"
}
```

#### REQ-023: Execution 통계

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/statistics`를 요청하면, **THEN** 실행 통계를 반환해야 합니다.

**Response:** `200 OK` with `ExecutionStatistics`

```json
{
  "total_nodes": 10,
  "completed_nodes": 8,
  "failed_nodes": 1,
  "pending_nodes": 1,
  "duration_seconds": 45.2,
  "avg_node_duration": 5.02
}
```

---

### NodeExecution Endpoints

#### REQ-024: NodeExecution 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/nodes`를 요청하면, **THEN** 해당 실행의 모든 노드 실행을 반환해야 합니다.

**Response:** `200 OK` with `list[NodeExecutionResponse]`

#### REQ-025: NodeExecution 단일 조회 (with Logs)

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/nodes/{node_id}`를 요청하면, **THEN** 로그를 포함한 노드 실행 정보를 반환해야 합니다.

**Response:** `200 OK` with `NodeExecutionDetailResponse`

---

### ExecutionLog Endpoints

#### REQ-026: ExecutionLog 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/logs`를 요청하면, **THEN** 페이지네이션되고 필터링 가능한 로그 목록을 반환해야 합니다.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | int | No | 1 | 페이지 번호 |
| size | int | No | 50 | 페이지 크기 (max: 1000) |
| level | LogLevel | No | None | 로그 레벨 필터 |
| node_execution_id | UUID | No | None | 노드 실행 필터 |

**Response:** `200 OK` with `PaginatedResponse[ExecutionLogResponse]`

#### REQ-027: NodeExecution 로그 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/executions/{id}/nodes/{node_id}/logs`를 요청하면, **THEN** 해당 노드 실행의 로그를 반환해야 합니다.

**Response:** `200 OK` with `list[ExecutionLogResponse]`

---

### Workflow-specific Execution Endpoints

#### REQ-028: Workflow별 Execution 목록 조회

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}/executions`를 요청하면, **THEN** 해당 워크플로우의 실행 목록을 반환해야 합니다.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | int | No | 1 | 페이지 번호 |
| size | int | No | 20 | 페이지 크기 |
| status | ExecutionStatus | No | None | 상태 필터 |

**Response:** `200 OK` with `PaginatedResponse[ExecutionResponse]`

#### REQ-029: Workflow 통계

**Event-Driven Requirement**

**WHEN** 클라이언트가 `GET /api/v1/workflows/{id}/statistics`를 요청하면, **THEN** 워크플로우의 전체 실행 통계를 반환해야 합니다.

**Response:** `200 OK` with `WorkflowStatistics`

```json
{
  "total_executions": 100,
  "successful_executions": 85,
  "failed_executions": 10,
  "cancelled_executions": 5,
  "success_rate": 0.85,
  "avg_duration_seconds": 42.5,
  "last_execution_at": "2026-01-12T10:30:00Z"
}
```

---

## Specifications

### SPEC-007-A: 파일 구조

```
backend/
  app/
    api/
      deps.py                    # 의존성 (DBSession, Pagination, Sorting)
      v1/
        __init__.py              # 라우터 등록
        workflows.py             # Workflow, Node, Edge 엔드포인트
        executions.py            # Execution, Log 엔드포인트
    schemas/
      base.py                    # BaseResponse, PaginatedResponse
      workflow.py                # WorkflowCreate, NodeCreate, EdgeCreate, etc.
      execution.py               # ExecutionCreate, LogResponse, etc.
    services/
      workflow_service.py        # WorkflowService, NodeService, EdgeService
      execution_service.py       # ExecutionService, NodeExecutionService, LogService
```

### SPEC-007-B: 의존성 주입 스펙

```python
# api/deps.py
from typing import AsyncGenerator, Annotated
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]


class Pagination:
    """Pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Page size"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size


class Sorting:
    """Sorting parameters."""

    def __init__(
        self,
        sort_by: str = Query("created_at", description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order
```

### SPEC-007-C: Base Schema 스펙

```python
# schemas/base.py
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model with ORM support."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    code: str | None = None
```

### SPEC-007-D: Workflow Schema 스펙

```python
# schemas/workflow.py
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import NodeType


# Workflow Schemas
class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    is_active: bool | None = None


class WorkflowResponse(BaseModel):
    """Workflow response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    config: dict[str, Any]
    variables: dict[str, Any]
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class WorkflowDuplicate(BaseModel):
    """Schema for duplicating a workflow."""

    name: str | None = None


# Node Schemas
class NodeCreate(BaseModel):
    """Schema for creating a node."""

    name: str = Field(..., min_length=1, max_length=255)
    node_type: NodeType
    position_x: float = 0.0
    position_y: float = 0.0
    config: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    tool_id: UUID | None = None
    agent_id: UUID | None = None
    timeout_seconds: int = Field(300, ge=1, le=3600)
    retry_config: dict[str, Any] = Field(
        default_factory=lambda: {"max_retries": 3, "delay": 1}
    )


class NodeUpdate(BaseModel):
    """Schema for updating a node."""

    name: str | None = Field(None, min_length=1, max_length=255)
    position_x: float | None = None
    position_y: float | None = None
    config: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    tool_id: UUID | None = None
    agent_id: UUID | None = None
    timeout_seconds: int | None = Field(None, ge=1, le=3600)
    retry_config: dict[str, Any] | None = None


class NodeUpdateWithId(NodeUpdate):
    """Schema for updating a node with ID (for batch updates)."""

    id: UUID


class NodeResponse(BaseModel):
    """Node response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    name: str
    node_type: NodeType
    position_x: float
    position_y: float
    config: dict[str, Any]
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    tool_id: UUID | None
    agent_id: UUID | None
    timeout_seconds: int
    retry_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NodeBatchCreate(BaseModel):
    """Schema for batch creating nodes."""

    nodes: list[NodeCreate] = Field(..., max_length=100)


# Edge Schemas
class EdgeCreate(BaseModel):
    """Schema for creating an edge."""

    source_node_id: UUID
    target_node_id: UUID
    source_handle: str | None = None
    target_handle: str | None = None
    condition: dict[str, Any] | None = None
    priority: int = 0
    label: str | None = Field(None, max_length=100)


class EdgeResponse(BaseModel):
    """Edge response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    source_handle: str | None
    target_handle: str | None
    condition: dict[str, Any] | None
    priority: int
    label: str | None
    created_at: datetime


class EdgeBatchCreate(BaseModel):
    """Schema for batch creating edges."""

    edges: list[EdgeCreate] = Field(..., max_length=100)


# Graph Update Schemas
class GraphUpdate(BaseModel):
    """Schema for bulk graph updates."""

    nodes_to_create: list[NodeCreate] = Field(default_factory=list)
    nodes_to_update: list[NodeUpdateWithId] = Field(default_factory=list)
    nodes_to_delete: list[UUID] = Field(default_factory=list)
    edges_to_create: list[EdgeCreate] = Field(default_factory=list)
    edges_to_delete: list[UUID] = Field(default_factory=list)


class GraphUpdateResponse(BaseModel):
    """Response for bulk graph update."""

    workflow_id: UUID
    version: int
    nodes_created: int
    nodes_updated: int
    nodes_deleted: int
    edges_created: int
    edges_deleted: int


# Full Workflow Response
class WorkflowFullResponse(WorkflowResponse):
    """Full workflow response with nodes and edges."""

    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
```

### SPEC-007-E: Execution Schema 스펙

```python
# schemas/execution.py
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import ExecutionStatus, LogLevel, TriggerType


# Execution Schemas
class ExecutionCreate(BaseModel):
    """Schema for creating an execution."""

    workflow_id: UUID
    trigger_type: TriggerType = TriggerType.MANUAL
    input_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionResponse(BaseModel):
    """Execution response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    trigger_type: TriggerType
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class NodeExecutionResponse(BaseModel):
    """Node execution response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_execution_id: UUID
    node_id: UUID
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    error_message: str | None
    retry_count: int
    execution_order: int
    created_at: datetime
    updated_at: datetime


class ExecutionLogResponse(BaseModel):
    """Execution log response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_execution_id: UUID
    node_execution_id: UUID | None
    level: LogLevel
    message: str
    data: dict[str, Any] | None
    timestamp: datetime


class NodeExecutionDetailResponse(NodeExecutionResponse):
    """Node execution with logs."""

    logs: list[ExecutionLogResponse]


class ExecutionDetailResponse(ExecutionResponse):
    """Execution with node executions and recent logs."""

    node_executions: list[NodeExecutionResponse]
    recent_logs: list[ExecutionLogResponse]


# Statistics Schemas
class ExecutionStatistics(BaseModel):
    """Execution statistics."""

    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    pending_nodes: int
    skipped_nodes: int
    running_nodes: int
    duration_seconds: float | None
    avg_node_duration: float | None


class WorkflowStatistics(BaseModel):
    """Workflow execution statistics."""

    total_executions: int
    successful_executions: int
    failed_executions: int
    cancelled_executions: int
    success_rate: float
    avg_duration_seconds: float | None
    last_execution_at: datetime | None
```

### SPEC-007-F: API Router 스펙

```python
# api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1.workflows import router as workflows_router
from app.api.v1.executions import router as executions_router

router = APIRouter()

router.include_router(workflows_router, prefix="/workflows", tags=["workflows"])
router.include_router(executions_router, prefix="/executions", tags=["executions"])
```

### SPEC-007-G: HTTP 상태 코드

| Operation | Success | Client Error | Server Error |
|-----------|---------|--------------|--------------|
| GET (list) | 200 | 400, 401, 403 | 500 |
| GET (single) | 200 | 401, 403, 404 | 500 |
| POST (create) | 201 | 400, 401, 403, 409 | 500 |
| PUT (update) | 200 | 400, 401, 403, 404, 409 | 500 |
| DELETE | 204 | 401, 403, 404 | 500 |
| POST (action) | 200 | 400, 401, 403, 404 | 500 |

---

## Constraints

### Technical Constraints

- Pydantic v2 `model_config = ConfigDict(from_attributes=True)` 사용 필수
- 모든 엔드포인트는 비동기(`async def`) 함수로 구현
- SQLAlchemy 2.0 스타일 쿼리 사용
- UUID는 `uuid.UUID` 타입으로 처리

### Performance Constraints

- 목록 조회 API 응답 시간 500ms 이내
- 단일 조회 API 응답 시간 200ms 이내
- 배치 작업 최대 100개 아이템

### Security Constraints

- 모든 API는 인증 필요 (향후 구현)
- 워크플로우 소유자만 수정/삭제 가능
- CORS 설정 적용
- Rate limiting 적용 (향후 구현)

---

## Dependencies

### Internal Dependencies

- SPEC-001: Base 모델, Mixins, Enums
- SPEC-003: Workflow, Node, Edge 모델
- SPEC-005: WorkflowExecution, NodeExecution, ExecutionLog 모델

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | API framework |
| pydantic | >=2.10.0 | Schema validation |
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| uvicorn | >=0.34.0 | ASGI server |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API 응답 시간 초과 | Medium | High | 페이지네이션, 캐싱, 인덱스 최적화 |
| 동시성 충돌 (워크플로우 수정) | Medium | Medium | Optimistic locking (version 필드) |
| 대용량 그래프 업데이트 실패 | Low | High | 트랜잭션 관리, 부분 롤백 |
| DAG 검증 성능 저하 | Low | Medium | 알고리즘 최적화, 캐싱 |

---

## Related SPECs

- SPEC-001: Database Foundation Setup (기본 모델)
- SPEC-003: Workflow Domain Models (Workflow, Node, Edge 모델)
- SPEC-005: Execution Tracking Models (Execution, Log 모델)
- SPEC-008: Scheduler Implementation (스케줄링 API)
- SPEC-010: DAG Validation Service (그래프 검증)
- SPEC-011: Workflow Execution Engine (실행 엔진)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | 최초 SPEC 작성 |
| 1.1.0 | 2026-01-12 | workflow-spec | 구현 완료 및 테스트 통과 (87.47% coverage) |

---

## Naming Conventions

### NC-001: Schema 클래스명 통일

**문제:** 현재 ExecutionCreate, ExecutionResponse 등의 이름이 WorkflowExecutionCreate, WorkflowExecutionResponse와 혼용되어 사용됨

**해결 방안:**

1. **스키마 클래스명 통일**
   - `ExecutionCreate` → `WorkflowExecutionCreate` (Workflow 접두사 추가)
   - `ExecutionResponse` → `WorkflowExecutionResponse` (Workflow 접두사 추가)
   - `ExecutionCreate` 유지 (간결한 API용 별칭)

2. **API 필드명 통일**
   - URL 경로: `/executions/{id}` (간결하게 유지)
   - Response JSON: `workflow_execution_id` (명확하게)
   - Query 매개변수: `?workflow_id=xxx` (간결하게)

3. **Service 클래스명 통일**
   - `ExecutionService` → `WorkflowExecutionService`
   - `NodeExecutionService` 유지 (이미 명확함)

**이유:** NodeExecution과 명확히 구분하기 위해 WorkflowExecution 접두사 사용

**적용 범위:**
- `schemas/execution.py` - 모든 Execution 관련 스키마
- `services/execution_service.py` - 서비스 클래스명
- API 엔드포인트 - 필드명 일관성

**마이그레이션 가이드:**

```python
# 변경 전
class ExecutionCreate(BaseModel):
    workflow_id: UUID
    ...

# 변경 후
class WorkflowExecutionCreate(BaseModel):
    workflow_id: UUID
    ...
    ExecutionCreate = WorkflowExecutionCreate  # 별칭 유지
```

### NC-002: API 필드명 표준화

**표준:** 각 컨텍스트에 따라 적절한 명명 규칙 적용

**명명 규칙:**

| 컨텍스트 | 형식 | 예시 | 규칙 |
|----------|------|------|------|
| URL 경로 | 간결한 형태 | `/executions/{id}` | 리소스 중심, 단수형 |
| Response JSON 필드 | 명확한 전체 이름 | `workflow_execution_id` | 중복을 피하기 위한 접두사 |
| Query 매개변수 | 간결한 형식 | `?workflow_id=xxx` | 필터링 용도로 간결하게 |
| Request Body 필드 | 명확한 전체 이름 | `workflow_execution_id` | 일관성 유지 |

**예시:**

```json
// URL: GET /api/v1/executions/{id}
// Response JSON:
{
  "id": "uuid",
  "workflow_id": "uuid",
  "workflow_execution_id": "uuid",  // 명확한 필드명
  "status": "running",
  "started_at": "2026-01-12T10:00:00Z"
}

// URL: GET /api/v1/executions?workflow_id=xxx&page=1
// 간결한 query parameter 사용
```

**예외 사항:**

- `id` 필드: URL 경로의 `{id}`와 일치하게 단순히 `id`로 사용
- `owner_id`: 별도의 접두사 불필요 (컨텍스트에서 명확함)
- Enum 값: `status`, `trigger_type` 등은 접두사 불필요

**적용 범위:**

- 모든 API 엔드포인트의 URL 경로 설계
- 모든 Response 스키마의 필드명
- 모든 Request 스키마의 필드명
- Query 매개변수 정의

**RESTful 관행 준수:**

- URL 경로: 리소스의 계층 구조 reflect
- Collection: 복수형 (`/executions`, `/workflows`)
- Single Resource: 단수형 (`/executions/{id}`)
- Nested Resources: 경로로 표현 (`/executions/{id}/nodes`)
