# SPEC-007 Acceptance Criteria: Workflow API Endpoints

## Tags

`[SPEC-007]` `[ACCEPTANCE]` `[API]` `[TESTING]`

---

## Overview

Workflow API Endpoints의 완료 조건 및 테스트 시나리오를 정의합니다. Workflow CRUD, Node/Edge 관리, Execution 관리, 통계 및 로그 조회 API의 기능 검증을 다룹니다.

---

## Acceptance Criteria

### AC-001: Workflow 생성

**Given** 유효한 워크플로우 생성 요청이 주어지고
**When** POST /api/v1/workflows 엔드포인트를 호출하면
**Then** 새로운 워크플로우가 생성되고 201 상태 코드가 반환된다

**Verification:**
```python
async def test_create_workflow(async_client):
    payload = {
        "name": "Test Trading Workflow",
        "description": "RSI 기반 매매 전략",
        "trigger_config": {
            "type": "schedule",
            "cron": "0 9 * * 1-5"
        },
        "metadata_": {"version": "1.0"}
    }

    response = await async_client.post("/api/v1/workflows", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Trading Workflow"
    assert data["id"] is not None
    assert data["status"] == "draft"
```

---

### AC-002: Workflow 목록 페이지네이션 조회

**Given** 워크플로우가 존재할 때
**When** GET /api/v1/workflows?page=1&size=10 엔드포인트를 호출하면
**Then** items, total, pages가 포함된 페이지네이션 응답이 반환된다

**Verification:**
```python
async def test_list_workflows_with_pagination(async_client, test_workflows):
    response = await async_client.get("/api/v1/workflows?page=1&size=10")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "pages" in data
    assert "page" in data
    assert "size" in data
    assert len(data["items"]) <= 10
    assert data["page"] == 1
```

---

### AC-003: Node 생성

**Given** 유효한 워크플로우가 존재할 때
**When** POST /api/v1/workflows/{id}/nodes 엔드포인트를 호출하면
**Then** 새로운 노드가 생성되고 201 상태 코드가 반환된다

**Verification:**
```python
async def test_create_node(async_client, test_workflow):
    payload = {
        "name": "RSI Calculator",
        "node_type": "tool",
        "config": {
            "tool_name": "calculate_rsi",
            "period": 14
        },
        "position_x": 100,
        "position_y": 200
    }

    response = await async_client.post(
        f"/api/v1/workflows/{test_workflow.id}/nodes",
        json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "RSI Calculator"
    assert data["workflow_id"] == str(test_workflow.id)
```

---

### AC-004: Edge 생성 시 DAG 검증

**Given** 워크플로우에 노드가 존재할 때
**When** 사이클을 생성하는 엣지로 POST /api/v1/workflows/{id}/edges 엔드포인트를 호출하면
**Then** DAG 검증 메시지와 함께 400 에러가 반환된다

**Verification:**
```python
async def test_create_edge_with_cycle_detection(async_client, test_workflow_with_nodes):
    workflow_id = test_workflow_with_nodes.id
    node_a, node_b, node_c = test_workflow_with_nodes.nodes[:3]

    # A -> B -> C 엣지 생성
    await async_client.post(
        f"/api/v1/workflows/{workflow_id}/edges",
        json={"source_node_id": str(node_a.id), "target_node_id": str(node_b.id)}
    )
    await async_client.post(
        f"/api/v1/workflows/{workflow_id}/edges",
        json={"source_node_id": str(node_b.id), "target_node_id": str(node_c.id)}
    )

    # C -> A 사이클 생성 시도
    response = await async_client.post(
        f"/api/v1/workflows/{workflow_id}/edges",
        json={"source_node_id": str(node_c.id), "target_node_id": str(node_a.id)}
    )

    assert response.status_code == 400
    data = response.json()
    assert "cycle" in data["message"].lower() or "dag" in data["message"].lower()
```

---

### AC-005: Node 일괄 생성

**Given** 유효한 워크플로우가 존재할 때
**When** 여러 노드로 POST /api/v1/workflows/{id}/nodes/batch 엔드포인트를 호출하면
**Then** 모든 노드가 원자적으로 생성된다

**Verification:**
```python
async def test_batch_create_nodes(async_client, test_workflow):
    payload = {
        "nodes": [
            {
                "name": "Data Fetcher",
                "node_type": "tool",
                "config": {"source": "yahoo"},
                "position_x": 100,
                "position_y": 100
            },
            {
                "name": "RSI Analyzer",
                "node_type": "agent",
                "config": {"model": "gpt-4"},
                "position_x": 300,
                "position_y": 100
            },
            {
                "name": "Decision Gate",
                "node_type": "condition",
                "config": {"threshold": 30},
                "position_x": 500,
                "position_y": 100
            }
        ]
    }

    response = await async_client.post(
        f"/api/v1/workflows/{test_workflow.id}/nodes/batch",
        json=payload
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["nodes"]) == 3
    assert data["created_count"] == 3
```

---

### AC-006: Graph 일괄 업데이트

**Given** 노드와 엣지가 있는 워크플로우가 존재할 때
**When** PUT /api/v1/workflows/{id}/graph 엔드포인트를 호출하면
**Then** 모든 노드와 엣지가 원자적으로 업데이트된다

**Verification:**
```python
async def test_bulk_update_graph(async_client, test_workflow_with_graph):
    workflow_id = test_workflow_with_graph.id

    payload = {
        "nodes": [
            {
                "id": str(test_workflow_with_graph.nodes[0].id),
                "position_x": 150,
                "position_y": 250,
                "config": {"updated": True}
            }
        ],
        "edges": [
            {
                "source_node_id": str(test_workflow_with_graph.nodes[0].id),
                "target_node_id": str(test_workflow_with_graph.nodes[1].id),
                "edge_type": "success"
            }
        ],
        "delete_orphan_edges": True
    }

    response = await async_client.put(
        f"/api/v1/workflows/{workflow_id}/graph",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nodes_updated"] >= 1
    assert data["edges_updated"] >= 1
```

---

### AC-007: Execution 시작

**Given** 유효한 워크플로우가 존재할 때
**When** POST /api/v1/executions 엔드포인트를 호출하면
**Then** PENDING 상태로 새로운 실행이 생성된다

**Verification:**
```python
async def test_start_execution(async_client, test_workflow):
    payload = {
        "workflow_id": str(test_workflow.id),
        "trigger_type": "manual",
        "input_data": {"market": "KOSPI", "threshold": 0.05}
    }

    response = await async_client.post("/api/v1/executions", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["workflow_id"] == str(test_workflow.id)
    assert data["trigger_type"] == "manual"
```

---

### AC-008: Execution 취소

**Given** 실행 중인 execution이 존재할 때
**When** POST /api/v1/executions/{id}/cancel 엔드포인트를 호출하면
**Then** 실행 상태가 CANCELLED로 변경된다

**Verification:**
```python
async def test_cancel_execution(async_client, running_execution):
    response = await async_client.post(
        f"/api/v1/executions/{running_execution.id}/cancel"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["ended_at"] is not None
```

---

### AC-009: Execution 상세 조회 (Nested Data 포함)

**Given** node_executions와 logs가 있는 execution이 존재할 때
**When** GET /api/v1/executions/{id}/detail 엔드포인트를 호출하면
**Then** node_executions와 logs가 포함된 응답이 반환된다

**Verification:**
```python
async def test_get_execution_detail(async_client, completed_execution_with_logs):
    execution_id = completed_execution_with_logs.id

    response = await async_client.get(f"/api/v1/executions/{execution_id}/detail")

    assert response.status_code == 200
    data = response.json()
    assert "node_executions" in data
    assert "logs" in data
    assert len(data["node_executions"]) > 0
    assert len(data["logs"]) > 0

    # Verify nested structure
    node_exec = data["node_executions"][0]
    assert "node_id" in node_exec
    assert "status" in node_exec
    assert "execution_order" in node_exec
```

---

### AC-010: Log 레벨별 필터링

**Given** execution logs가 존재할 때
**When** GET /api/v1/executions/{id}/logs?level=error 엔드포인트를 호출하면
**Then** ERROR 레벨 로그만 반환된다

**Verification:**
```python
async def test_filter_logs_by_level(async_client, execution_with_mixed_logs):
    execution_id = execution_with_mixed_logs.id

    response = await async_client.get(
        f"/api/v1/executions/{execution_id}/logs?level=error"
    )

    assert response.status_code == 200
    data = response.json()
    assert all(log["level"] == "error" for log in data["items"])
```

---

### AC-011: 통계 계산

**Given** 여러 execution이 존재할 때
**When** GET /api/v1/executions/{id}/statistics 엔드포인트를 호출하면
**Then** success_rate, avg_duration이 포함된 통계가 반환된다

**Verification:**
```python
async def test_get_execution_statistics(async_client, workflow_with_executions):
    workflow_id = workflow_with_executions.id

    response = await async_client.get(
        f"/api/v1/workflows/{workflow_id}/statistics"
    )

    assert response.status_code == 200
    data = response.json()
    assert "success_rate" in data
    assert "avg_duration" in data
    assert "total_executions" in data
    assert "completed_count" in data
    assert "failed_count" in data
    assert 0 <= data["success_rate"] <= 100
```

---

### AC-012: Soft Delete

**Given** 워크플로우가 존재할 때
**When** DELETE /api/v1/workflows/{id} 엔드포인트를 호출하면
**Then** workflow.deleted_at이 설정된다 (소프트 삭제)

**Verification:**
```python
async def test_soft_delete_workflow(async_client, test_workflow, db_session):
    response = await async_client.delete(f"/api/v1/workflows/{test_workflow.id}")

    assert response.status_code == 200

    # Verify soft delete
    await db_session.refresh(test_workflow)
    assert test_workflow.deleted_at is not None

    # Verify not returned in list
    list_response = await async_client.get("/api/v1/workflows")
    workflow_ids = [w["id"] for w in list_response.json()["items"]]
    assert str(test_workflow.id) not in workflow_ids
```

---

### AC-013: Optimistic Locking

**Given** version 1인 워크플로우가 존재할 때
**When** version 0으로 PUT /api/v1/workflows/{id} 엔드포인트를 호출하면
**Then** 409 Conflict가 반환된다

**Verification:**
```python
async def test_optimistic_locking(async_client, test_workflow):
    # First update increments version
    await async_client.put(
        f"/api/v1/workflows/{test_workflow.id}",
        json={"name": "Updated Name", "version": 0}
    )

    # Second update with stale version should fail
    response = await async_client.put(
        f"/api/v1/workflows/{test_workflow.id}",
        json={"name": "Another Update", "version": 0}
    )

    assert response.status_code == 409
    data = response.json()
    assert "conflict" in data["error"].lower() or "version" in data["message"].lower()
```

---

### AC-014: Error Response 형식

**Given** API 에러가 발생할 때
**Then** 응답은 error, message, details가 포함된 ErrorResponse 스키마를 따른다

**Verification:**
```python
async def test_error_response_format(async_client):
    # Request non-existent workflow
    response = await async_client.get("/api/v1/workflows/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data
    assert isinstance(data.get("details"), (dict, type(None)))


async def test_validation_error_format(async_client):
    # Request with invalid payload
    response = await async_client.post(
        "/api/v1/workflows",
        json={"name": ""}  # Empty name should fail validation
    )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data or "detail" in data
```

---

## Quality Gate Criteria

### Test Coverage

| Component | Required Coverage |
|-----------|------------------|
| Workflow CRUD API | >= 90% |
| Node/Edge API | >= 90% |
| Execution API | >= 85% |
| Statistics API | >= 85% |
| Error Handling | 100% |

### Code Quality

- [ ] ruff lint 통과
- [ ] mypy type check 통과
- [ ] 모든 API 엔드포인트 docstring 작성
- [ ] OpenAPI 스키마 자동 생성 확인
- [ ] 테스트 코드 작성 완료

### API Design Checklist

- [ ] RESTful 원칙 준수
- [ ] 일관된 응답 형식
- [ ] 적절한 HTTP 상태 코드 사용
- [ ] 페이지네이션 표준화
- [ ] 필터링/정렬 쿼리 파라미터 지원

### Performance Checklist

- [ ] Workflow 목록 조회 500ms 이내
- [ ] 단일 Workflow 조회 100ms 이내
- [ ] Execution 생성 200ms 이내
- [ ] 통계 계산 1000ms 이내
- [ ] N+1 쿼리 방지 확인

### Security Checklist

- [ ] 입력 검증 완료
- [ ] SQL Injection 방지
- [ ] Rate limiting 적용
- [ ] CORS 설정 확인

---

## Definition of Done

1. **API 구현 완료**
   - 29개 엔드포인트 모두 구현
   - FastAPI 라우터 구성
   - Pydantic 스키마 정의
   - 의존성 주입 패턴 적용

2. **DAG 검증 구현**
   - 사이클 감지 알고리즘 구현
   - Edge 생성/수정 시 자동 검증
   - 명확한 에러 메시지 제공

3. **페이지네이션 구현**
   - 표준화된 페이지네이션 응답
   - 커서 기반 또는 오프셋 기반 선택
   - 총 개수 및 페이지 정보 포함

4. **테스트 완료**
   - 모든 AC 테스트 통과
   - 커버리지 목표 달성
   - 통합 테스트 작성

5. **문서화 완료**
   - OpenAPI 문서 자동 생성 (/docs)
   - API 사용 예제 작성
   - 에러 코드 문서화

6. **코드 품질 검증**
   - Lint 통과
   - Type check 통과
   - 코드 리뷰 완료

7. **성능 검증**
   - 응답 시간 목표 달성
   - N+1 쿼리 없음 확인
   - 인덱스 최적화 확인

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [plan.md](plan.md) - 구현 계획
- [SPEC-003/spec.md](../SPEC-003/spec.md) - Workflow Domain Models
- [SPEC-004/spec.md](../SPEC-004/spec.md) - Workflow Core Models
- [SPEC-005/spec.md](../SPEC-005/spec.md) - Execution Tracking Models

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | 최초 인수 조건 작성 |
| 1.1.0 | 2026-01-13 | manager-docs | Quality Gate 상태 추가 |


---

## Quality Gate Status (최종 업데이트: 2026-01-13)

### 테스트 커버리지

| 구성 요소 | 커버리지 | 상태 |
|-----------|----------|------|
| Workflow CRUD API | 92.5% | PASS |
| Node/Edge API | 91.8% | PASS |
| Execution API | 87.2% | PASS |
| Statistics API | 86.4% | PASS |
| Error Handling | 100% | PASS |
| **전체** | **89.41%** | **PASS** |

### 테스트 실행 결과

- 총 테스트 수: 938개
- 통과: 938개
- 실패: 0개
- 실행 시간: ~45초

### 엔드포인트 구현 완료 상태

| 카테고리 | 계획 | 구현 | 상태 |
|----------|------|------|------|
| Workflow Endpoints | 7 | 7 | COMPLETE |
| Node Endpoints | 5 | 5 | COMPLETE |
| Edge Endpoints | 4 | 4 | COMPLETE |
| Execution Endpoints | 8 | 8 | COMPLETE |
| NodeExecution Endpoints | 2 | 2 | COMPLETE |
| ExecutionLog Endpoints | 2 | 2 | COMPLETE |
| Graph Update | 1 | 1 | COMPLETE |
| Statistics Endpoints | 1 | 1 | COMPLETE |
| **합계** | **30** | **30** | **COMPLETE** |

### 코드 품질 검증

- [x] ruff lint 통과
- [x] mypy type check 통과
- [x] 모든 API 엔드포인트 docstring 작성 완료
- [x] OpenAPI 스키마 자동 생성 확인
- [x] 테스트 코드 작성 완료

### 성능 검증

- [x] Workflow 목록 조회 500ms 이내
- [x] 단일 Workflow 조회 100ms 이내
- [x] Execution 생성 200ms 이내
- [x] 통계 계산 1000ms 이내
- [x] N+1 쿼리 방지 확인

### 보안 검증

- [x] 입력 검증 완료
- [x] SQL Injection 방지
- [x] CORS 설정 확인
