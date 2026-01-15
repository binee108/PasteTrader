---
id: SPEC-009
version: "1.2.0"
status: "completed"
created: "2026-01-13"
updated: "2026-01-15"
author: "MoAI Agent"
priority: "high"
---

# SPEC-009: Tool/Agent API Endpoints

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.2.0 | 2026-01-15 | MoAI Agent | 문서와 코드 동기화: 필드명 통일 (parameters→input_schema, tool_ids→tools), model_config 평탄화, 필드 추가 (tool_type, output_schema, auth_config, rate_limit, owner_id, memory_config, is_public) |
| 1.1.0 | 2026-01-14 | MoAI Agent | 구현 완료, 보안 모듈 개선 (passlib → bcrypt), 타입 annotations 수정 |
| 1.0.0 | 2026-01-13 | MoAI Agent | 초기 SPEC 작성 |

---

## 1. 개요

### 1.1 목적

워크플로우에서 사용되는 도구(Tool)와 에이전트(Agent)를 관리하기 위한 RESTful API 엔드포인트를 정의한다. 사용자는 이 API를 통해 도구와 에이전트를 등록, 조회, 수정, 삭제하고 테스트할 수 있다.

### 1.2 범위

- **Tool API**: 도구 CRUD 및 테스트 실행
- **Agent API**: 에이전트 CRUD 및 도구 연결 관리
- **Registry 통합**: meta_llm 엔진의 ToolRegistry/AgentManager와 연동

### 1.3 용어 정의

| 용어 | 정의 |
|------|------|
| Tool | 다양한 유형의 실행 가능한 도구 (HTTP, MCP, Python, Shell, Builtin) |
| Agent | LLM 기반 추론 에이전트 (시스템 프롬프트 + 도구 조합) |
| input_schema | 도구 실행에 필요한 입력 파라미터의 JSON Schema |
| output_schema | 도구 실행 결과의 JSON Schema (선택사항) |
| config | 도구 유형별 설정 (URL, 메서드, 인증 등) |
| tool_type | 도구의 유형 (http, mcp, python, shell, builtin) |

---

## 2. EARS 요구사항

### 2.1 Ubiquitous Requirements (보편적 요구사항)

| ID | 요구사항 |
|----|----------|
| U-001 | 시스템은 모든 API 응답에 표준 JSON 형식을 사용해야 한다 |
| U-002 | 시스템은 도구/에이전트 이름의 고유성을 보장해야 한다 |
| U-003 | 시스템은 모든 생성/수정 시 created_at/updated_at 타임스탬프를 기록해야 한다 |
| U-004 | 시스템은 input_schema 필드에 유효한 JSON Schema만 허용해야 한다 |

### 2.2 Event-Driven Requirements (이벤트 기반 요구사항)

| ID | 트리거 | 요구사항 |
|----|--------|----------|
| E-001 | 도구가 생성되면 | 시스템은 ToolRegistry에 도구를 등록해야 한다 |
| E-002 | 에이전트가 생성되면 | 시스템은 연결된 도구들의 유효성을 검증해야 한다 |
| E-003 | 도구가 삭제되면 | 시스템은 해당 도구를 참조하는 에이전트 목록을 반환해야 한다 |
| E-004 | 도구 테스트가 요청되면 | 시스템은 샌드박스 환경에서 도구를 실행해야 한다 |
| E-005 | 에이전트 테스트가 요청되면 | 시스템은 테스트 프롬프트로 에이전트를 실행해야 한다 |

### 2.3 State-Driven Requirements (상태 기반 요구사항)

| ID | 상태 조건 | 요구사항 |
|----|-----------|----------|
| S-001 | 도구가 is_active=false 상태인 동안 | 시스템은 워크플로우 실행에서 해당 도구를 제외해야 한다 |
| S-002 | 에이전트가 is_active=false 상태인 동안 | 시스템은 워크플로우 노드에서 해당 에이전트 선택을 비활성화해야 한다 |

### 2.4 Optional Requirements (선택적 요구사항)

| ID | 조건 | 요구사항 |
|----|------|----------|
| O-001 | 버전 관리가 활성화된 경우 | 시스템은 도구/에이전트의 버전 히스토리를 유지해야 한다 |
| O-002 | 카테고리 기능이 활성화된 경우 | 시스템은 도구/에이전트를 카테고리별로 그룹화해야 한다 |

### 2.5 Unwanted Behavior Requirements (금지 요구사항)

| ID | 조건 | 금지 행위 |
|----|------|-----------|
| X-001 | 도구가 워크플로우에서 사용 중일 때 | 시스템은 해당 도구의 삭제를 허용하지 않아야 한다 |
| X-002 | 에이전트가 워크플로우에서 사용 중일 때 | 시스템은 해당 에이전트의 삭제를 허용하지 않아야 한다 |
| X-003 | 중복된 이름으로 도구/에이전트 생성 시 | 시스템은 생성을 거부해야 한다 |

---

## 3. Tool API 엔드포인트 명세

### 3.1 도구 생성

```
POST /api/v1/tools
```

**Request Body:**
```json
{
  "name": "price_fetcher",
  "description": "주가 데이터를 조회하는 도구",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET"
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "symbol": {"type": "string", "description": "종목 코드"},
      "period": {"type": "string", "enum": ["1d", "1w", "1m", "3m"]}
    },
    "required": ["symbol"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "price": {"type": "number"},
      "timestamp": {"type": "string"}
    }
  },
  "auth_config": {
    "type": "bearer",
    "token": "${API_TOKEN}"
  },
  "is_active": true,
  "is_public": false
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "owner_id": "owner-uuid",
  "name": "price_fetcher",
  "description": "주가 데이터를 조회하는 도구",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET"
  },
  "input_schema": {...},
  "output_schema": {...},
  "auth_config": {
    "type": "bearer",
    "token": "***"
  },
  "rate_limit": null,
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

### 3.2 도구 목록 조회

```
GET /api/v1/tools?skip=0&limit=20&is_active=true&is_public=false
```

**Query Parameters:**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| skip | int | N | 건너뛸 레코드 수 (기본: 0) |
| limit | int | N | 페이지 크기 (기본: 20) |
| is_active | bool | N | 활성화 상태 필터 |
| is_public | bool | N | 공개 여부 필터 |

### 3.3 도구 상세 조회

```
GET /api/v1/tools/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "owner_id": "owner-uuid",
  "name": "price_fetcher",
  "description": "주가 데이터를 조회하는 도구",
  "tool_type": "http",
  "config": {
    "url": "https://api.example.com/price",
    "method": "GET"
  },
  "input_schema": {...},
  "output_schema": {...},
  "auth_config": {...},
  "rate_limit": null,
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

### 3.4 도구 수정

```
PUT /api/v1/tools/{id}
```

**Request Body:**
```json
{
  "description": "업데이트된 설명",
  "config": {
    "url": "https://api.example.com/v2/price",
    "method": "GET"
  },
  "input_schema": {...},
  "is_active": false
}
```

### 3.5 도구 삭제

```
DELETE /api/v1/tools/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "deleted": true,
  "message": "Tool deleted successfully"
}
```

**Response (409 Conflict - 사용 중인 경우):**
```json
{
  "error": "Tool is in use",
  "used_by_agents": ["agent-uuid-1"],
  "used_in_workflows": ["workflow-uuid-1"]
}
```

### 3.6 도구 테스트 실행

```
POST /api/v1/tools/{id}/test
```

**Request Body:**
```json
{
  "input_data": {
    "symbol": "005930",
    "period": "1d"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "output": {
    "price": 82500,
    "timestamp": "2026-01-15T09:00:00+09:00"
  },
  "error": null,
  "execution_time_ms": 150.5
}
```

---

## 4. Agent API 엔드포인트 명세

### 4.1 에이전트 생성

```
POST /api/v1/agents
```

**Request Body:**
```json
{
  "name": "buy_signal_analyzer",
  "description": "매수 신호 분석 에이전트",
  "system_prompt": "당신은 주식 매수 신호를 분석하는 전문 트레이딩 분석가입니다...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "tools": ["tool-uuid-1", "tool-uuid-2"],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
  },
  "is_active": true,
  "is_public": false
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "owner_id": "owner-uuid",
  "name": "buy_signal_analyzer",
  "description": "매수 신호 분석 에이전트",
  "system_prompt": "...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "tools": ["tool-uuid-1", "tool-uuid-2"],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
  },
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

### 4.2 에이전트 목록 조회

```
GET /api/v1/agents?skip=0&limit=20&model_provider=anthropic&is_active=true&is_public=false
```

**Query Parameters:**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| skip | int | N | 건너뛸 레코드 수 (기본: 0) |
| limit | int | N | 페이지 크기 (기본: 20) |
| model_provider | str | N | 모델 제공자 필터 (anthropic, openai, glm) |
| is_active | bool | N | 활성화 상태 필터 |
| is_public | bool | N | 공개 여부 필터 |

### 4.3 에이전트 상세 조회

```
GET /api/v1/agents/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "owner_id": "owner-uuid",
  "name": "buy_signal_analyzer",
  "description": "매수 신호 분석 에이전트",
  "system_prompt": "...",
  "model_provider": "anthropic",
  "model_name": "claude-3-5-sonnet-20241022",
  "config": {
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "tools": ["tool-uuid-1", "tool-uuid-2"],
  "memory_config": {
    "max_turns": 10,
    "context_window": 200000
  },
  "is_active": true,
  "is_public": false,
  "created_at": "2026-01-13T09:00:00+09:00",
  "updated_at": "2026-01-13T09:00:00+09:00"
}
```

### 4.4 에이전트 수정

```
PUT /api/v1/agents/{id}
```

### 4.5 에이전트 삭제

```
DELETE /api/v1/agents/{id}
```

### 4.6 에이전트-도구 연결 관리

#### 4.6.1 도구 추가

```
POST /api/v1/agents/{agent_id}/tools
```

**Request Body:**
```json
{
  "tool_id": "tool-uuid-3"
}
```

**Response (200 OK):**
```json
{
  "id": "agent-uuid",
  "name": "buy_signal_analyzer",
  "tools": ["tool-uuid-1", "tool-uuid-2", "tool-uuid-3"],
  ...
}
```

#### 4.6.2 도구 제거

```
DELETE /api/v1/agents/{agent_id}/tools/{tool_id}
```

**Response (200 OK):**
```json
{
  "id": "agent-uuid",
  "name": "buy_signal_analyzer",
  "tools": ["tool-uuid-1", "tool-uuid-2"],
  ...
}
```

### 4.7 에이전트 테스트 실행

```
POST /api/v1/agents/{agent_id}/test
```

**Request Body:**
```json
{
  "input_data": {
    "message": "삼성전자의 현재 RSI 지표를 분석해주세요"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "output": {
    "response": "삼성전자(005930)의 현재 RSI는 45.2로 중립 구간에 위치합니다...",
    "tool_calls": [
      {"tool": "price_fetcher", "params": {...}, "result": {...}},
      {"tool": "indicator_calculator", "params": {...}, "result": {...}}
    ]
  },
  "error": null,
  "execution_time_ms": 2500.5
}
```

---

## 5. 데이터 모델

### 5.1 Tool 스키마

```python
class Tool(BaseModel):
    id: UUID                           # 고유 ID
    owner_id: UUID                     # 소유자 ID
    name: str                          # 도구 이름 (unique)
    description: str | None            # 설명
    tool_type: ToolType                # 도구 유형 (http, mcp, python, shell, builtin)
    config: dict[str, Any]             # 도구별 설정 (JSONB)
    input_schema: dict[str, Any]       # 입력 JSON Schema (JSONB)
    output_schema: dict[str, Any] | None  # 출력 JSON Schema (JSONB)
    auth_config: dict[str, Any] | None    # 인증 설정 (JSONB)
    rate_limit: dict[str, Any] | None     # 속도 제한 설정 (JSONB)
    is_active: bool                    # 활성화 상태
    is_public: bool                    # 공개 여부
    created_at: datetime               # 생성 시간
    updated_at: datetime | None        # 수정 시간
    deleted_at: datetime | None        # 삭제 시간 (soft delete)
```

### 5.2 Agent 스키마

```python
class Agent(BaseModel):
    id: UUID                           # 고유 ID
    owner_id: UUID                     # 소유자 ID
    name: str                          # 에이전트 이름 (unique)
    description: str | None            # 설명
    system_prompt: str | None          # 시스템 프롬프트
    model_provider: str                # LLM 제공자 (anthropic, openai, glm)
    model_name: str                    # 모델 이름
    config: dict[str, Any]             # 모델 설정 (temperature, max_tokens 등)
    tools: list[str]                   # 도구 UUID 목록 (JSONB)
    memory_config: dict[str, Any] | None  # 메모리 설정 (JSONB)
    is_active: bool                    # 활성화 상태
    is_public: bool                    # 공개 여부
    created_at: datetime               # 생성 시간
    updated_at: datetime | None        # 수정 시간
    deleted_at: datetime | None        # 삭제 시간 (soft delete)
```

### 5.3 필드 변경사항 요약

**Tool 모델:**
- `parameters` → `input_schema`: 필드명 변경
- `implementation_path` → `config` + `tool_type`: 구현 방식 변경
- `tool_type` 추가: 도구 유형 구분 (http, mcp, python, shell, builtin)
- `output_schema` 추가: 출력 JSON Schema 지원
- `auth_config` 추가: 인증 설정 지원
- `rate_limit` 추가: 속도 제한 설정 지원
- `owner_id` 추가: 소유자 관계
- `is_public` 추가: 공개 여부

**Agent 모델:**
- `model_config` (객체) → `model_provider`, `model_name`, `config` (평탄화)
- `tool_ids` → `tools`: 필드명 변경 (UUID 문자열 리스트)
- `owner_id` 추가: 소유자 관계
- `memory_config` 추가: 메모리 설정 지원
- `is_public` 추가: 공개 여부

---

## 6. 의존성

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| ToolRegistry | `meta_llm/tools/registry.py` | 도구 등록 및 조회 |
| BaseTool | `meta_llm/tools/base_tool.py` | 도구 베이스 클래스 |
| BaseAgent | `meta_llm/agents/base_agent.py` | 에이전트 베이스 클래스 |
| ProviderRouter | `meta_llm/providers/router.py` | LLM 제공자 라우팅 |

---

## 7. 비기능적 요구사항

### 7.1 성능
- API 응답 시간: 200ms 이내 (CRUD), 60초 이내 (테스트 실행)
- 동시 테스트 실행: 최대 5개

### 7.2 보안
- JWT 기반 인증 필수
- 도구 implementation_path는 화이트리스트 검증

### 7.3 확장성
- 도구/에이전트 수: 무제한 (페이지네이션 필수)
- 카테고리 및 태그 지원 (향후 확장)

---

## 8. 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- paste-trader 아키텍처 문서: `.moai/project/structure.md`
- paste-trader 기술 스택: `.moai/project/tech.md`

## 9. 구현 노트

### 9.1 완료된 기능

- Tool API: 7개 엔드포인트 (생성, 목록, 상세, 수정, 삭제, 테스트)
- Agent API: 8개 엔드포인트 (생성, 목록, 상세, 수정, 삭제, 도구 추가, 도구 제거, 테스트)
- 총 15개 RESTful API 엔드포인트 구현
- ToolService 및 AgentService 비즈니스 로직 계층 구현
- 통합 테스트: 28개 보안 관련 테스트 통과

### 9.2 품질 검증

- **테스트 커버리지**: pytest 기반 테스트 러너, 28/28 테스트 통과
- **린터**: ruff로 포맷팅 및 린팅 구성 완료
- **타입 체커**: mypy로 타입 검증, 0개 타입 에러

### 9.3 주요 변경사항

**버전 1.2.0 (2026-01-15) - 문서 동기화:**
- 필드명 통일: `parameters` → `input_schema`, `tool_ids` → `tools`
- Agent 모델 평탄화: `model_config` (객체) → `model_provider`, `model_name`, `config` (평탄화)
- Tool 필드 추가: `tool_type`, `output_schema`, `auth_config`, `rate_limit`, `owner_id`, `is_public`
- Agent 필드 추가: `owner_id`, `memory_config`, `is_public`
- 테스트 API 변경: `params/timeout` → `input_data`, `test_prompt/timeout` → `input_data`
- 페이지네이션 변경: `offset` → `skip`
- 에이전트-도구 연결 API 변경: `PUT` → `POST/DELETE`

**버전 1.1.0 (2026-01-14) - 초기 구현:**
- 보안 모듈: passlib 대신 직접 bcrypt 사용으로 마이그레이션
- 타입 어노테이션: AsyncGenerator 타입 수정
- 모델 통합: is_active 필드를 SoftDeleteMixin으로 이동
- 의존성 제거: pyproject.toml에서 passlib 제거

### 9.4 향후 개선사항

- 도구/에이전트 버전 관리 (O-001)
- 카테고리 및 태그 기능 (O-002)
- 워크플로우 연동 검증 강화
- 테스트 실행 샌드박스 격리 강화
