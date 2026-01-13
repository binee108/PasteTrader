---
id: SPEC-008
version: "1.0.0"
status: "draft"
created: "2026-01-13"
updated: "2026-01-13"
author: "MoAI Agent"
priority: "high"
---

# SPEC-008: Execution API Endpoints

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-01-13 | MoAI Agent | 초기 SPEC 작성 |

---

## 1. 개요

### 1.1 목적

워크플로우 실행을 관리하기 위한 RESTful API 엔드포인트를 정의한다. 사용자는 이 API를 통해 워크플로우를 실행, 조회, 취소, 재시도할 수 있다.

### 1.2 범위

- 워크플로우 실행 시작 및 관리
- 실행 상태 조회 및 모니터링
- 노드별 실행 상세 정보 조회
- 실패한 실행의 재시도
- 실행 취소 및 삭제

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| Execution | 워크플로우의 단일 실행 인스턴스 |
| Node Execution | 워크플로우 내 개별 노드의 실행 인스턴스 |
| ExecutionStatus | 실행 상태 (pending, running, completed, failed, cancelled) |

---

## 2. EARS 요구사항

### 2.1 Ubiquitous Requirements (보편적 요구사항)

| ID | 요구사항 |
|----|----------|
| U-001 | 시스템은 모든 API 응답에 표준 JSON 형식을 사용해야 한다 |
| U-002 | 시스템은 모든 실행 상태 변경을 `workflow_executions` 테이블에 기록해야 한다 |
| U-003 | 시스템은 모든 API 요청에 대해 유효성 검증을 수행해야 한다 |
| U-004 | 시스템은 존재하지 않는 리소스 접근 시 404 Not Found를 반환해야 한다 |

### 2.2 Event-Driven Requirements (이벤트 기반 요구사항)

| ID | 트리거 | 요구사항 |
|----|--------|----------|
| E-001 | 사용자가 워크플로우 실행을 요청하면 | 시스템은 새로운 실행 인스턴스를 생성하고 202 Accepted를 반환해야 한다 |
| E-002 | 실행이 완료되면 | 시스템은 completed_at 타임스탬프와 최종 상태를 기록해야 한다 |
| E-003 | 노드 실행이 실패하면 | 시스템은 error_message와 함께 노드 상태를 failed로 업데이트해야 한다 |
| E-004 | 사용자가 재시도를 요청하면 | 시스템은 retry_count를 증가시키고 실패한 노드부터 실행을 재개해야 한다 |
| E-005 | 사용자가 취소를 요청하면 | 시스템은 실행 중인 노드를 중단하고 상태를 cancelled로 변경해야 한다 |

### 2.3 State-Driven Requirements (상태 기반 요구사항)

| ID | 상태 조건 | 요구사항 |
|----|-----------|----------|
| S-001 | 실행이 running 상태인 동안 | 시스템은 노드 진행률을 실시간으로 업데이트해야 한다 |
| S-002 | 실행이 pending 상태인 동안 | 시스템은 취소 요청을 즉시 처리할 수 있어야 한다 |
| S-003 | 실행이 completed 또는 cancelled 상태인 동안 | 시스템은 재시도 요청을 거부해야 한다 (failed만 재시도 가능) |

### 2.4 Optional Requirements (선택적 요구사항)

| ID | 조건 | 요구사항 |
|----|------|----------|
| O-001 | 로그 스트리밍이 활성화된 경우 | 시스템은 WebSocket을 통해 실시간 로그를 제공해야 한다 |
| O-002 | 통계 기능이 활성화된 경우 | 시스템은 실행 통계 엔드포인트를 제공해야 한다 |

### 2.5 Unwanted Behavior Requirements (금지 요구사항)

| ID | 조건 | 금지 행위 |
|----|------|-----------|
| X-001 | 실행이 running 상태일 때 | 시스템은 동일 워크플로우의 중복 실행을 허용하지 않아야 한다 |
| X-002 | 인증되지 않은 요청인 경우 | 시스템은 실행 데이터에 접근을 허용하지 않아야 한다 |
| X-003 | 실행이 completed 상태일 때 | 시스템은 상태를 running으로 변경하지 않아야 한다 |

---

## 3. API 엔드포인트 명세

### 3.1 워크플로우 실행 시작

```
POST /api/v1/executions
```

**Request Body:**
```json
{
  "workflow_id": "uuid",
  "variables": {},
  "trigger_type": "manual" | "schedule"
}
```

**Response (202 Accepted):**
```json
{
  "id": "uuid",
  "workflow_id": "uuid",
  "status": "pending",
  "started_at": "2026-01-13T09:30:00+09:00"
}
```

### 3.2 실행 목록 조회

```
GET /api/v1/executions?status=running&workflow_id=uuid&limit=20&offset=0
```

**Query Parameters:**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| status | string | N | 상태 필터 |
| workflow_id | uuid | N | 워크플로우 ID 필터 |
| limit | int | N | 페이지 크기 (기본: 20) |
| offset | int | N | 시작 오프셋 |

### 3.3 실행 상세 조회

```
GET /api/v1/executions/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "workflow_id": "uuid",
  "status": "running",
  "started_at": "2026-01-13T09:30:00+09:00",
  "completed_at": null,
  "context": {},
  "error_message": null,
  "retry_count": 0,
  "progress": {
    "total_nodes": 8,
    "completed_nodes": 3,
    "current_node": "n4"
  }
}
```

### 3.4 실행 취소/삭제

```
DELETE /api/v1/executions/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "cancelled",
  "message": "Execution cancelled successfully"
}
```

### 3.5 노드 실행 상세 조회

```
GET /api/v1/executions/{id}/nodes
```

**Response (200 OK):**
```json
{
  "execution_id": "uuid",
  "nodes": [
    {
      "node_id": "n1",
      "status": "completed",
      "started_at": "2026-01-13T09:30:00+09:00",
      "completed_at": "2026-01-13T09:30:05+09:00",
      "inputs": {},
      "outputs": {}
    }
  ]
}
```

### 3.6 실행 재시도

```
POST /api/v1/executions/{id}/retry
```

**Request Body:**
```json
{
  "from_node": "n3",
  "reset_context": false
}
```

**Response (202 Accepted):**
```json
{
  "id": "uuid",
  "status": "pending",
  "retry_count": 1,
  "message": "Retry initiated from node n3"
}
```

---

## 4. 데이터 모델

### 4.1 ExecutionStatus Enum

```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 4.2 WorkflowExecution 스키마

```python
class WorkflowExecution(BaseModel):
    id: UUID
    workflow_id: UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    context: dict
    error_message: str | None
    retry_count: int = 0
```

---

## 5. 의존성

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| ExecutionService | `backend/app/services/execution_service.py` | 비즈니스 로직 |
| DAGExecutor | `workflow_engine/core/executor.py` | DAG 실행 엔진 |
| WorkflowScheduler | `workflow_engine/scheduler/apscheduler.py` | 스케줄 트리거 |

---

## 6. 비기능적 요구사항

### 6.1 성능
- API 응답 시간: 200ms 이내 (조회), 500ms 이내 (실행 시작)
- 동시 실행 가능 워크플로우: 최대 10개

### 6.2 확장성
- 페이지네이션 지원 (Offset 기반, 향후 Cursor 기반 확장)
- 필터링 및 정렬 지원

### 6.3 보안
- JWT 기반 인증 필수
- 사용자별 실행 데이터 격리

---

## 7. 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [APScheduler 문서](https://apscheduler.readthedocs.io/)
- paste-trader 아키텍처 문서: `.moai/project/structure.md`
