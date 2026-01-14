---
id: SPEC-009
version: "1.1.0"
status: "completed"
created: "2026-01-13"
updated: "2026-01-14"
author: "MoAI Agent"
priority: "high"
---

# SPEC-009: Tool/Agent API Endpoints

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
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
| Tool | 코드로 정의된 실행 가능한 도구 (예: 가격 조회, 지표 계산) |
| Agent | LLM 기반 추론 에이전트 (시스템 프롬프트 + 도구 조합) |
| ToolRegistry | 도구 등록 및 조회를 담당하는 레지스트리 |
| Parameters | 도구 실행에 필요한 입력 파라미터 (JSON Schema) |

---

## 2. EARS 요구사항

### 2.1 Ubiquitous Requirements (보편적 요구사항)

| ID | 요구사항 |
|----|----------|
| U-001 | 시스템은 모든 API 응답에 표준 JSON 형식을 사용해야 한다 |
| U-002 | 시스템은 도구/에이전트 이름의 고유성을 보장해야 한다 |
| U-003 | 시스템은 모든 생성/수정 시 created_at/updated_at 타임스탬프를 기록해야 한다 |
| U-004 | 시스템은 parameters 필드에 유효한 JSON Schema만 허용해야 한다 |

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
  "parameters": {
    "type": "object",
    "properties": {
      "symbol": {"type": "string", "description": "종목 코드"},
      "period": {"type": "string", "enum": ["1d", "1w", "1m", "3m"]}
    },
    "required": ["symbol"]
  },
  "implementation_path": "meta_llm.tools.data_fetcher.PriceFetcher"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "price_fetcher",
  "description": "주가 데이터를 조회하는 도구",
  "parameters": {...},
  "implementation_path": "meta_llm.tools.data_fetcher.PriceFetcher",
  "is_active": true,
  "created_at": "2026-01-13T09:00:00+09:00"
}
```

### 3.2 도구 목록 조회

```
GET /api/v1/tools?is_active=true&search=price&limit=20&offset=0
```

**Query Parameters:**
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| is_active | bool | N | 활성화 상태 필터 |
| search | string | N | 이름/설명 검색 |
| limit | int | N | 페이지 크기 (기본: 20) |
| offset | int | N | 시작 오프셋 |

### 3.3 도구 상세 조회

```
GET /api/v1/tools/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "price_fetcher",
  "description": "주가 데이터를 조회하는 도구",
  "parameters": {...},
  "implementation_path": "meta_llm.tools.data_fetcher.PriceFetcher",
  "is_active": true,
  "created_at": "2026-01-13T09:00:00+09:00",
  "used_by_agents": ["agent-uuid-1", "agent-uuid-2"],
  "used_in_workflows": ["workflow-uuid-1"]
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
  "parameters": {...},
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
  "params": {
    "symbol": "005930",
    "period": "1d"
  },
  "timeout": 30
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "result": {...},
  "execution_time_ms": 150,
  "logs": ["Fetching data...", "Data retrieved successfully"]
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
  "model_config": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "tool_ids": ["tool-uuid-1", "tool-uuid-2"]
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "buy_signal_analyzer",
  "description": "매수 신호 분석 에이전트",
  "system_prompt": "...",
  "model_config": {...},
  "tool_ids": ["tool-uuid-1", "tool-uuid-2"],
  "is_active": true,
  "created_at": "2026-01-13T09:00:00+09:00"
}
```

### 4.2 에이전트 목록 조회

```
GET /api/v1/agents?is_active=true&search=analyzer&limit=20&offset=0
```

### 4.3 에이전트 상세 조회

```
GET /api/v1/agents/{id}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "buy_signal_analyzer",
  "description": "매수 신호 분석 에이전트",
  "system_prompt": "...",
  "model_config": {...},
  "tools": [
    {"id": "tool-uuid-1", "name": "price_fetcher"},
    {"id": "tool-uuid-2", "name": "indicator_calculator"}
  ],
  "is_active": true,
  "created_at": "2026-01-13T09:00:00+09:00",
  "used_in_workflows": ["workflow-uuid-1"]
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

```
PUT /api/v1/agents/{id}/tools
```

**Request Body:**
```json
{
  "tool_ids": ["tool-uuid-1", "tool-uuid-2", "tool-uuid-3"]
}
```

### 4.7 에이전트 테스트 실행

```
POST /api/v1/agents/{id}/test
```

**Request Body:**
```json
{
  "test_prompt": "삼성전자의 현재 RSI 지표를 분석해주세요",
  "timeout": 60
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "response": "삼성전자(005930)의 현재 RSI는 45.2로...",
  "tool_calls": [
    {"tool": "price_fetcher", "params": {...}, "result": {...}},
    {"tool": "indicator_calculator", "params": {...}, "result": {...}}
  ],
  "execution_time_ms": 2500,
  "tokens_used": {"input": 150, "output": 320}
}
```

---

## 5. 데이터 모델

### 5.1 Tool 스키마

```python
class Tool(BaseModel):
    id: UUID
    name: str  # unique
    description: str | None
    parameters: dict  # JSON Schema
    implementation_path: str | None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None
```

### 5.2 Agent 스키마

```python
class Agent(BaseModel):
    id: UUID
    name: str  # unique
    description: str | None
    system_prompt: str
    model_config: ModelConfig
    tool_ids: list[UUID] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None

class ModelConfig(BaseModel):
    provider: str  # anthropic, openai, glm
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
```

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
- Agent API: 6개 엔드포인트 (생성, 목록, 상세, 수정, 삭제, 도구 연결, 테스트)
- 총 13개 RESTful API 엔드포인트 구현
- ToolService 및 AgentService 비즈니스 로직 계층 구현
- 통합 테스트: 28개 보안 관련 테스트 통과

### 9.2 품질 검증

- **테스트 커버리지**: pytest 기반 테스트 러너, 28/28 테스트 통과
- **린터**: ruff로 포맷팅 및 린팅 구성 완료
- **타입 체커**: mypy로 타입 검증, 0개 타입 에러

### 9.3 주요 변경사항

- **보안 모듈**: passlib 대신 직접 bcrypt 사용으로 마이그레이션
- **타입 어노테이션**: AsyncGenerator 타입 수정
- **모델 통합**: is_active 필드를 SoftDeleteMixin으로 이동
- **의존성 제거**: pyproject.toml에서 passlib 제거
