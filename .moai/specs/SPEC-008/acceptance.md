# SPEC-008: Execution API Endpoints - Acceptance Criteria

## 1. 개요

이 문서는 SPEC-008 Execution API Endpoints의 인수 기준을 Given/When/Then 형식으로 정의합니다.

---

## 2. 워크플로우 실행 시작

### AC-001: 정상 실행 시작

```gherkin
Scenario: 워크플로우 정상 실행 시작
  Given 유효한 workflow_id "wf-001"이 존재하고
  And 사용자가 인증된 상태일 때
  When POST /api/v1/executions 요청을 보내면
    | workflow_id | wf-001 |
    | trigger_type | manual |
  Then 응답 상태 코드는 202 Accepted이고
  And 응답 본문에 execution_id가 포함되고
  And 실행 상태는 "pending"이다
```

### AC-002: 존재하지 않는 워크플로우 실행 시도

```gherkin
Scenario: 존재하지 않는 워크플로우 실행 시도
  Given 존재하지 않는 workflow_id "invalid-wf"로
  When POST /api/v1/executions 요청을 보내면
  Then 응답 상태 코드는 404 Not Found이고
  And 에러 메시지는 "Workflow not found"이다
```

### AC-003: 중복 실행 방지

```gherkin
Scenario: 이미 실행 중인 워크플로우 중복 실행 방지
  Given workflow_id "wf-001"이 이미 running 상태로 실행 중일 때
  When POST /api/v1/executions 요청을 보내면
    | workflow_id | wf-001 |
  Then 응답 상태 코드는 409 Conflict이고
  And 에러 메시지는 "Workflow is already running"이다
```

---

## 3. 실행 목록 조회

### AC-004: 전체 실행 목록 조회

```gherkin
Scenario: 전체 실행 목록 조회
  Given 5개의 실행 레코드가 존재할 때
  When GET /api/v1/executions 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 5개의 실행 레코드가 포함된다
```

### AC-005: 상태별 필터링 조회

```gherkin
Scenario: running 상태 실행만 조회
  Given 다음 실행 레코드가 존재할 때
    | id | status |
    | exec-1 | running |
    | exec-2 | completed |
    | exec-3 | running |
  When GET /api/v1/executions?status=running 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 2개의 실행 레코드가 포함되고
  And 모든 레코드의 status는 "running"이다
```

### AC-006: 페이지네이션

```gherkin
Scenario: 페이지네이션 적용
  Given 50개의 실행 레코드가 존재할 때
  When GET /api/v1/executions?limit=10&offset=20 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 10개의 실행 레코드가 포함되고
  And 21번째부터 30번째 레코드가 반환된다
```

---

## 4. 실행 상세 조회

### AC-007: 정상 상세 조회

```gherkin
Scenario: 실행 상세 정보 조회
  Given execution_id "exec-001"이 존재할 때
  When GET /api/v1/executions/exec-001 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 다음 필드가 포함된다
    | field | present |
    | id | true |
    | workflow_id | true |
    | status | true |
    | started_at | true |
    | progress | true |
```

### AC-008: 존재하지 않는 실행 조회

```gherkin
Scenario: 존재하지 않는 실행 조회
  Given execution_id "invalid-exec"가 존재하지 않을 때
  When GET /api/v1/executions/invalid-exec 요청을 보내면
  Then 응답 상태 코드는 404 Not Found이다
```

---

## 5. 실행 취소/삭제

### AC-009: running 상태 실행 취소

```gherkin
Scenario: 실행 중인 워크플로우 취소
  Given execution_id "exec-001"이 running 상태일 때
  When DELETE /api/v1/executions/exec-001 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답의 status는 "cancelled"이고
  And 실행의 completed_at이 설정된다
```

### AC-010: pending 상태 실행 삭제

```gherkin
Scenario: 대기 중인 실행 삭제
  Given execution_id "exec-002"가 pending 상태일 때
  When DELETE /api/v1/executions/exec-002 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답의 status는 "deleted"이고
  And 실행 레코드가 데이터베이스에서 삭제된다
```

### AC-011: completed 상태 실행 삭제

```gherkin
Scenario: 완료된 실행 삭제
  Given execution_id "exec-003"이 completed 상태일 때
  When DELETE /api/v1/executions/exec-003 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 실행 레코드와 관련 노드 실행 레코드가 삭제된다
```

---

## 6. 노드 실행 상세 조회

### AC-012: 노드 실행 목록 조회

```gherkin
Scenario: 노드 실행 상세 조회
  Given execution_id "exec-001"에 3개의 노드 실행이 존재할 때
  When GET /api/v1/executions/exec-001/nodes 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 3개의 노드 실행 정보가 포함되고
  And 각 노드에 다음 필드가 포함된다
    | field | present |
    | node_id | true |
    | status | true |
    | started_at | true |
    | inputs | true |
    | outputs | true |
```

### AC-013: 실행 순서대로 노드 조회

```gherkin
Scenario: 노드가 실행 순서대로 정렬
  Given execution_id "exec-001"에 노드 n1, n2, n3이 순서대로 실행되었을 때
  When GET /api/v1/executions/exec-001/nodes 요청을 보내면
  Then 응답의 노드 순서는 [n1, n2, n3]이다
```

---

## 7. 실행 재시도

### AC-014: failed 상태 실행 재시도

```gherkin
Scenario: 실패한 실행 재시도
  Given execution_id "exec-001"이 failed 상태이고
  And 노드 n3에서 실패했을 때
  When POST /api/v1/executions/exec-001/retry 요청을 보내면
    | from_node | n3 |
    | reset_context | false |
  Then 응답 상태 코드는 202 Accepted이고
  And 실행 상태가 "pending"으로 변경되고
  And retry_count가 1 증가한다
```

### AC-015: completed 상태 재시도 거부

```gherkin
Scenario: 완료된 실행 재시도 거부
  Given execution_id "exec-002"가 completed 상태일 때
  When POST /api/v1/executions/exec-002/retry 요청을 보내면
  Then 응답 상태 코드는 400 Bad Request이고
  And 에러 메시지는 "Cannot retry execution with status: completed"이다
```

### AC-016: 컨텍스트 리셋 재시도

```gherkin
Scenario: 컨텍스트를 리셋하고 처음부터 재시도
  Given execution_id "exec-001"이 failed 상태일 때
  When POST /api/v1/executions/exec-001/retry 요청을 보내면
    | reset_context | true |
  Then 응답 상태 코드는 202 Accepted이고
  And 실행 컨텍스트가 빈 객체로 초기화되고
  And 모든 노드가 처음부터 재실행된다
```

---

## 8. 에러 처리

### AC-017: 인증되지 않은 요청 거부

```gherkin
Scenario: 인증 없이 API 호출
  Given 사용자가 인증되지 않은 상태일 때
  When GET /api/v1/executions 요청을 보내면
  Then 응답 상태 코드는 401 Unauthorized이다
```

### AC-018: 잘못된 요청 형식 거부

```gherkin
Scenario: 잘못된 JSON 형식으로 실행 요청
  Given 잘못된 JSON 형식의 요청 본문으로
  When POST /api/v1/executions 요청을 보내면
  Then 응답 상태 코드는 422 Unprocessable Entity이고
  And 에러 상세 정보가 포함된다
```

---

## 9. 성능 요구사항

### AC-019: 응답 시간 요구사항

```gherkin
Scenario: API 응답 시간 충족
  Given 시스템이 정상 부하 상태일 때
  When GET /api/v1/executions 요청을 100회 보내면
  Then P95 응답 시간은 200ms 이하이다
```

### AC-020: 동시 실행 제한

```gherkin
Scenario: 최대 동시 실행 수 제한
  Given 10개의 워크플로우가 이미 running 상태일 때
  When 새로운 실행 요청을 보내면
  Then 응답 상태 코드는 429 Too Many Requests이고
  And 에러 메시지는 "Maximum concurrent executions reached"이다
```

---

## 10. 검증 체크리스트

| ID | 항목 | 검증 방법 | 상태 |
|----|------|-----------|------|
| AC-001 | 정상 실행 시작 | 자동화 테스트 | ⬜ |
| AC-002 | 존재하지 않는 워크플로우 | 자동화 테스트 | ⬜ |
| AC-003 | 중복 실행 방지 | 자동화 테스트 | ⬜ |
| AC-004 | 전체 목록 조회 | 자동화 테스트 | ⬜ |
| AC-005 | 상태별 필터링 | 자동화 테스트 | ⬜ |
| AC-006 | 페이지네이션 | 자동화 테스트 | ⬜ |
| AC-007 | 상세 조회 | 자동화 테스트 | ⬜ |
| AC-008 | 존재하지 않는 실행 조회 | 자동화 테스트 | ⬜ |
| AC-009 | running 취소 | 자동화 테스트 | ⬜ |
| AC-010 | pending 삭제 | 자동화 테스트 | ⬜ |
| AC-011 | completed 삭제 | 자동화 테스트 | ⬜ |
| AC-012 | 노드 실행 조회 | 자동화 테스트 | ⬜ |
| AC-013 | 노드 순서 정렬 | 자동화 테스트 | ⬜ |
| AC-014 | failed 재시도 | 자동화 테스트 | ⬜ |
| AC-015 | completed 재시도 거부 | 자동화 테스트 | ⬜ |
| AC-016 | 컨텍스트 리셋 재시도 | 자동화 테스트 | ⬜ |
| AC-017 | 인증 검증 | 자동화 테스트 | ⬜ |
| AC-018 | 요청 형식 검증 | 자동화 테스트 | ⬜ |
| AC-019 | 응답 시간 | 성능 테스트 | ⬜ |
| AC-020 | 동시 실행 제한 | 부하 테스트 | ⬜ |
