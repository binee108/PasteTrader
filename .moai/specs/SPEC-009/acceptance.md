# SPEC-009: Tool/Agent API Endpoints - Acceptance Criteria

## 1. 개요

이 문서는 SPEC-009 Tool/Agent API Endpoints의 인수 기준을 Given/When/Then 형식으로 정의합니다.

---

## 2. Tool API 인수 기준

### AC-001: 도구 정상 생성

```gherkin
Scenario: 도구 정상 생성
  Given 유효한 도구 정보가 준비되어 있고
    | name | price_fetcher |
    | description | 주가 데이터 조회 도구 |
    | parameters | {"type": "object", "properties": {...}} |
  And 사용자가 인증된 상태일 때
  When POST /api/v1/tools 요청을 보내면
  Then 응답 상태 코드는 201 Created이고
  And 응답에 생성된 도구의 id가 포함되고
  And is_active는 true이다
```

### AC-002: 중복 이름 도구 생성 거부

```gherkin
Scenario: 중복 이름 도구 생성 거부
  Given 이름이 "price_fetcher"인 도구가 이미 존재할 때
  When 동일한 이름으로 POST /api/v1/tools 요청을 보내면
  Then 응답 상태 코드는 409 Conflict이고
  And 에러 메시지는 "Tool with name 'price_fetcher' already exists"이다
```

### AC-003: 도구 목록 조회

```gherkin
Scenario: 도구 목록 조회
  Given 5개의 도구가 존재할 때
  When GET /api/v1/tools 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 5개의 도구 정보가 포함된다
```

### AC-004: 활성 상태 필터링 조회

```gherkin
Scenario: 활성 도구만 조회
  Given 다음 도구가 존재할 때
    | name | is_active |
    | tool_1 | true |
    | tool_2 | false |
    | tool_3 | true |
  When GET /api/v1/tools?is_active=true 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 2개의 도구가 포함되고
  And 모든 도구의 is_active는 true이다
```

### AC-005: 도구 검색

```gherkin
Scenario: 이름/설명으로 도구 검색
  Given 다음 도구가 존재할 때
    | name | description |
    | price_fetcher | 주가 데이터 조회 |
    | indicator_calc | 기술적 지표 계산 |
    | market_screener | 종목 스크리닝 |
  When GET /api/v1/tools?search=price 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 1개의 도구(price_fetcher)가 포함된다
```

### AC-006: 도구 상세 조회

```gherkin
Scenario: 도구 상세 정보 조회
  Given tool_id "uuid-123"인 도구가 존재할 때
  When GET /api/v1/tools/uuid-123 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 다음 필드가 포함된다
    | field | present |
    | id | true |
    | name | true |
    | parameters | true |
    | used_by_agents | true |
    | used_in_workflows | true |
```

### AC-007: 존재하지 않는 도구 조회

```gherkin
Scenario: 존재하지 않는 도구 조회
  Given tool_id "invalid-uuid"가 존재하지 않을 때
  When GET /api/v1/tools/invalid-uuid 요청을 보내면
  Then 응답 상태 코드는 404 Not Found이다
```

### AC-008: 도구 수정

```gherkin
Scenario: 도구 정보 수정
  Given tool_id "uuid-123"인 도구가 존재할 때
  When PUT /api/v1/tools/uuid-123 요청을 보내면
    | description | 업데이트된 설명 |
    | is_active | false |
  Then 응답 상태 코드는 200 OK이고
  And description이 "업데이트된 설명"으로 변경되고
  And is_active가 false로 변경된다
```

### AC-009: 도구 삭제

```gherkin
Scenario: 도구 정상 삭제
  Given tool_id "uuid-123"인 도구가 존재하고
  And 해당 도구를 참조하는 에이전트나 워크플로우가 없을 때
  When DELETE /api/v1/tools/uuid-123 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 deleted: true가 포함된다
```

### AC-010: 사용 중인 도구 삭제 거부

```gherkin
Scenario: 사용 중인 도구 삭제 거부
  Given tool_id "uuid-123"인 도구가 존재하고
  And 에이전트 "agent-1"이 해당 도구를 참조할 때
  When DELETE /api/v1/tools/uuid-123 요청을 보내면
  Then 응답 상태 코드는 409 Conflict이고
  And 응답에 used_by_agents 목록이 포함된다
```

### AC-011: 도구 테스트 실행 성공

```gherkin
Scenario: 도구 테스트 실행 성공
  Given tool_id "uuid-123"인 도구가 존재하고
  And 해당 도구가 정상 동작 가능할 때
  When POST /api/v1/tools/uuid-123/test 요청을 보내면
    | params | {"symbol": "005930"} |
    | timeout | 30 |
  Then 응답 상태 코드는 200 OK이고
  And success는 true이고
  And result에 실행 결과가 포함되고
  And execution_time_ms가 양수이다
```

### AC-012: 도구 테스트 실행 실패

```gherkin
Scenario: 도구 테스트 실행 실패
  Given tool_id "uuid-123"인 도구가 존재하고
  And 잘못된 파라미터가 제공될 때
  When POST /api/v1/tools/uuid-123/test 요청을 보내면
    | params | {"invalid_param": "value"} |
  Then 응답 상태 코드는 200 OK이고
  And success는 false이고
  And error에 에러 메시지가 포함된다
```

---

## 3. Agent API 인수 기준

### AC-013: 에이전트 정상 생성

```gherkin
Scenario: 에이전트 정상 생성
  Given 유효한 에이전트 정보가 준비되어 있고
    | name | buy_signal_analyzer |
    | system_prompt | 당신은 매수 신호 분석가입니다... |
    | model_config | {"provider": "anthropic", "model": "claude-sonnet-4-20250514"} |
  And tool_ids에 유효한 도구 ID들이 포함되어 있을 때
  When POST /api/v1/agents 요청을 보내면
  Then 응답 상태 코드는 201 Created이고
  And 응답에 생성된 에이전트의 id가 포함되고
  And tool_ids가 정상적으로 저장된다
```

### AC-014: 유효하지 않은 도구 ID로 에이전트 생성 거부

```gherkin
Scenario: 유효하지 않은 도구 ID로 에이전트 생성 거부
  Given tool_ids에 존재하지 않는 도구 ID가 포함되어 있을 때
  When POST /api/v1/agents 요청을 보내면
  Then 응답 상태 코드는 400 Bad Request이고
  And 에러 메시지에 유효하지 않은 tool_id가 포함된다
```

### AC-015: 에이전트 상세 조회

```gherkin
Scenario: 에이전트 상세 정보 조회
  Given agent_id "uuid-456"인 에이전트가 존재할 때
  When GET /api/v1/agents/uuid-456 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 다음 필드가 포함된다
    | field | present |
    | id | true |
    | name | true |
    | system_prompt | true |
    | model_config | true |
    | tools | true |
    | used_in_workflows | true |
```

### AC-016: 에이전트-도구 연결 업데이트

```gherkin
Scenario: 에이전트의 도구 연결 업데이트
  Given agent_id "uuid-456"인 에이전트가 존재하고
  And 유효한 tool_ids ["tool-1", "tool-2"]가 있을 때
  When PUT /api/v1/agents/uuid-456/tools 요청을 보내면
    | tool_ids | ["tool-1", "tool-2"] |
  Then 응답 상태 코드는 200 OK이고
  And 에이전트의 tool_ids가 ["tool-1", "tool-2"]로 업데이트된다
```

### AC-017: 에이전트 삭제

```gherkin
Scenario: 에이전트 정상 삭제
  Given agent_id "uuid-456"인 에이전트가 존재하고
  And 해당 에이전트를 참조하는 워크플로우가 없을 때
  When DELETE /api/v1/agents/uuid-456 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 deleted: true가 포함된다
```

### AC-018: 사용 중인 에이전트 삭제 거부

```gherkin
Scenario: 사용 중인 에이전트 삭제 거부
  Given agent_id "uuid-456"인 에이전트가 존재하고
  And 워크플로우 "workflow-1"이 해당 에이전트를 참조할 때
  When DELETE /api/v1/agents/uuid-456 요청을 보내면
  Then 응답 상태 코드는 409 Conflict이고
  And 응답에 used_in_workflows 목록이 포함된다
```

### AC-019: 에이전트 테스트 실행

```gherkin
Scenario: 에이전트 테스트 실행
  Given agent_id "uuid-456"인 에이전트가 존재할 때
  When POST /api/v1/agents/uuid-456/test 요청을 보내면
    | test_prompt | 삼성전자의 RSI를 분석해주세요 |
    | timeout | 60 |
  Then 응답 상태 코드는 200 OK이고
  And success는 true이고
  And response에 분석 결과가 포함되고
  And tool_calls에 호출된 도구 목록이 포함되고
  And tokens_used에 토큰 사용량이 포함된다
```

---

## 4. 공통 인수 기준

### AC-020: 인증되지 않은 요청 거부

```gherkin
Scenario: 인증 없이 API 호출
  Given 사용자가 인증되지 않은 상태일 때
  When GET /api/v1/tools 요청을 보내면
  Then 응답 상태 코드는 401 Unauthorized이다
```

### AC-021: 잘못된 JSON 형식 거부

```gherkin
Scenario: 잘못된 JSON 형식으로 요청
  Given 잘못된 JSON 형식의 요청 본문으로
  When POST /api/v1/tools 요청을 보내면
  Then 응답 상태 코드는 422 Unprocessable Entity이고
  And 에러 상세 정보가 포함된다
```

### AC-022: 페이지네이션 동작

```gherkin
Scenario: 페이지네이션 적용
  Given 50개의 도구가 존재할 때
  When GET /api/v1/tools?limit=10&offset=20 요청을 보내면
  Then 응답 상태 코드는 200 OK이고
  And 응답에 10개의 도구가 포함되고
  And 21번째부터 30번째 도구가 반환된다
```

---

## 5. 성능 인수 기준

### AC-023: API 응답 시간

```gherkin
Scenario: CRUD API 응답 시간 충족
  Given 시스템이 정상 부하 상태일 때
  When GET /api/v1/tools 요청을 100회 보내면
  Then P95 응답 시간은 200ms 이하이다
```

### AC-024: 테스트 실행 타임아웃

```gherkin
Scenario: 도구 테스트 실행 타임아웃
  Given 실행에 오래 걸리는 도구가 있을 때
  When POST /api/v1/tools/{id}/test 요청을 timeout=5로 보내면
  And 실행이 5초 내에 완료되지 않으면
  Then 응답 상태 코드는 200 OK이고
  And success는 false이고
  And error는 "Execution timeout"이다
```

---

## 6. 검증 체크리스트

| ID | 항목 | 검증 방법 | 상태 |
|----|------|-----------|------|
| AC-001 | 도구 정상 생성 | 자동화 테스트 | ⬜ |
| AC-002 | 중복 이름 거부 | 자동화 테스트 | ⬜ |
| AC-003 | 도구 목록 조회 | 자동화 테스트 | ⬜ |
| AC-004 | 활성 상태 필터링 | 자동화 테스트 | ⬜ |
| AC-005 | 도구 검색 | 자동화 테스트 | ⬜ |
| AC-006 | 도구 상세 조회 | 자동화 테스트 | ⬜ |
| AC-007 | 존재하지 않는 도구 | 자동화 테스트 | ⬜ |
| AC-008 | 도구 수정 | 자동화 테스트 | ⬜ |
| AC-009 | 도구 삭제 | 자동화 테스트 | ⬜ |
| AC-010 | 사용 중 도구 삭제 거부 | 자동화 테스트 | ⬜ |
| AC-011 | 도구 테스트 성공 | 자동화 테스트 | ⬜ |
| AC-012 | 도구 테스트 실패 | 자동화 테스트 | ⬜ |
| AC-013 | 에이전트 정상 생성 | 자동화 테스트 | ⬜ |
| AC-014 | 유효하지 않은 tool_id | 자동화 테스트 | ⬜ |
| AC-015 | 에이전트 상세 조회 | 자동화 테스트 | ⬜ |
| AC-016 | 도구 연결 업데이트 | 자동화 테스트 | ⬜ |
| AC-017 | 에이전트 삭제 | 자동화 테스트 | ⬜ |
| AC-018 | 사용 중 에이전트 삭제 거부 | 자동화 테스트 | ⬜ |
| AC-019 | 에이전트 테스트 실행 | 자동화 테스트 | ⬜ |
| AC-020 | 인증 검증 | 자동화 테스트 | ⬜ |
| AC-021 | 요청 형식 검증 | 자동화 테스트 | ⬜ |
| AC-022 | 페이지네이션 | 자동화 테스트 | ⬜ |
| AC-023 | 응답 시간 | 성능 테스트 | ⬜ |
| AC-024 | 테스트 타임아웃 | 자동화 테스트 | ⬜ |
