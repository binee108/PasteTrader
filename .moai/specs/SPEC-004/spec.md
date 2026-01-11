# SPEC-004: Tool & Agent Registry

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-004 |
| Title | Tool & Agent Registry |
| Created | 2026-01-11 |
| Status | Planned |
| Priority | High |
| Lifecycle | spec-anchored |
| Author | workflow-spec |
| Phase | 1 - Workflow Core Models |

## Tags

`[SPEC-004]` `[DATABASE]` `[TOOL]` `[AGENT]` `[REGISTRY]` `[BACKEND]`

---

## Overview

본 SPEC은 PasteTrader 워크플로우 엔진에서 노드 실행을 위한 Tool(도구)과 Agent(에이전트) 레지스트리 모델을 정의합니다. Tool은 외부 API 호출, MCP 서버, Python 함수 등의 실행 단위를 나타내며, Agent는 LLM 기반 AI 에이전트의 설정을 관리합니다.

### Scope

- Tool 모델 정의 (HTTP, MCP, Python, Shell, Builtin 타입)
- Agent 모델 정의 (Anthropic, OpenAI, GLM 제공자)
- 소유권 및 공유 기능
- 입출력 스키마 정의
- 인증 및 Rate Limit 설정

### Out of Scope

- Tool/Agent 실행 로직 (Phase 4에서 구현)
- LLM Provider 통합 (Phase 5에서 구현)
- API 엔드포인트 (Phase 3에서 구현)

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16.x | Primary database |
| SQLAlchemy | 2.0.x | Async ORM |
| asyncpg | 0.30.x | PostgreSQL async driver |
| Pydantic | 2.10.x | Schema validation |

### Configuration Dependencies

- SPEC-001의 Base 모델, Mixins 사용
- `ToolType` enum 업데이트 필요 (현재 정의와 다름)
- `ModelProvider` enum 활용

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| JSONB로 유연한 설정 저장이 가능함 | High | PostgreSQL 16 공식 지원 | 스키마 분리 필요 |
| 인증 정보 암호화가 애플리케이션 레벨에서 수행됨 | Medium | 보안 요구사항 | DB 레벨 암호화 필요 |
| Tool과 Agent는 여러 워크플로우에서 재사용됨 | High | 설계 의도 | 워크플로우별 복사 필요 |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| 사용자별 Tool/Agent 소유권이 필요함 | High | 권한 관리 복잡도 증가 |
| 공개 Tool/Agent 공유 기능이 필요함 | Medium | 보안 검토 필요 |
| Agent가 여러 Tool을 사용할 수 있음 | High | Tool 참조 방식 재설계 필요 |

---

## Requirements

### REQ-001: Tool 모델 정의

**Ubiquitous Requirement**

시스템은 외부 도구 실행을 위한 Tool 모델을 제공해야 한다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| owner_id | UUID | FK -> users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 도구 이름 |
| description | TEXT | NULL | 설명 |
| tool_type | VARCHAR(50) | NOT NULL, ENUM | 도구 타입 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 도구 설정 |
| input_schema | JSONB | NOT NULL, DEFAULT '{}' | 입력 JSON Schema |
| output_schema | JSONB | NULL | 출력 JSON Schema |
| auth_config | JSONB | NULL | 인증 설정 (암호화) |
| rate_limit | JSONB | NULL | 요청 제한 설정 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성 상태 |
| is_public | BOOLEAN | NOT NULL, DEFAULT FALSE | 공유 여부 |

### REQ-002: Tool 타입 Enum 업데이트

**Ubiquitous Requirement**

시스템은 database-schema.md에 정의된 Tool 타입을 지원해야 한다.

**Required Tool Types:**

| Type | Value | Description |
|------|-------|-------------|
| HTTP | http | HTTP API 호출 |
| MCP | mcp | MCP 서버 도구 |
| PYTHON | python | Python 함수 실행 |
| SHELL | shell | Shell 명령 실행 |
| BUILTIN | builtin | 내장 도구 |

**Note:** 현재 enums.py의 ToolType은 다른 값을 가지고 있으므로 업데이트가 필요합니다.

### REQ-003: Agent 모델 정의

**Ubiquitous Requirement**

시스템은 LLM 에이전트 설정을 위한 Agent 모델을 제공해야 한다.

**Details:**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| owner_id | UUID | FK -> users(id), NOT NULL | 소유자 |
| name | VARCHAR(255) | NOT NULL | 에이전트 이름 |
| description | TEXT | NULL | 설명 |
| model_provider | VARCHAR(50) | NOT NULL, ENUM | LLM 제공자 |
| model_name | VARCHAR(100) | NOT NULL | 모델 식별자 |
| system_prompt | TEXT | NULL | 시스템 프롬프트 |
| config | JSONB | NOT NULL, DEFAULT '{}' | 모델 파라미터 |
| tools | JSONB | NOT NULL, DEFAULT '[]' | 사용 가능한 도구 ID 목록 |
| memory_config | JSONB | NULL | 메모리/컨텍스트 설정 |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 활성 상태 |
| is_public | BOOLEAN | NOT NULL, DEFAULT FALSE | 공유 여부 |

### REQ-004: Model Provider Enum

**Ubiquitous Requirement**

시스템은 지원하는 LLM 제공자를 정의해야 한다.

**Supported Providers:**

| Provider | Value | Description |
|----------|-------|-------------|
| Anthropic | anthropic | Claude 모델 |
| OpenAI | openai | GPT 모델 |
| ZhipuAI | zhipuai | GLM 모델 |

**Note:** 현재 enums.py의 ModelProvider.GLM을 zhipuai로 변경 검토 필요.

### REQ-005: User 관계 설정

**Event-Driven Requirement**

WHEN Tool 또는 Agent가 생성될 때 THEN 시스템은 owner_id를 통해 User와의 관계를 설정해야 한다.

**Details:**
- User 삭제 시 해당 User의 Tool/Agent 처리 정책 정의 필요
- Soft delete 적용으로 데이터 보존

### REQ-006: Tool-Agent 연결

**State-Driven Requirement**

IF Agent가 tools 목록에 Tool ID를 포함하면 THEN 해당 Agent는 해당 Tool을 사용할 수 있다.

**Details:**
- tools 필드는 UUID 배열을 JSONB로 저장
- 런타임에 Tool 존재 여부 검증 필요
- 순환 참조 방지 불필요 (Tool은 Agent를 참조하지 않음)

### REQ-007: 공개 레지스트리 접근

**State-Driven Requirement**

IF Tool 또는 Agent의 is_public이 TRUE이면 THEN 다른 사용자도 해당 항목을 조회하고 사용할 수 있다.

**Details:**
- 공개 항목은 읽기 전용으로 다른 사용자에게 노출
- 수정/삭제는 소유자만 가능

### REQ-008: 인증 정보 보안

**Unwanted Requirement**

시스템은 auth_config 필드의 민감한 정보를 평문으로 저장하지 않아야 한다.

**Details:**
- API 키, 비밀번호 등은 암호화하여 저장
- 암호화 키는 환경 변수로 관리
- 조회 시 마스킹 처리

### REQ-009: Rate Limit 설정

**Optional Requirement**

가능하면 시스템은 Tool별 Rate Limit 설정을 제공한다.

**rate_limit JSONB 구조:**
```json
{
  "requests_per_minute": 60,
  "requests_per_hour": 1000,
  "concurrent_requests": 5
}
```

---

## Specifications

### SPEC-004-A: File Structure

```
backend/
  app/
    models/
      __init__.py          # Model exports (update)
      base.py              # Base model, mixins (existing)
      enums.py             # Domain enums (update ToolType)
      tool.py              # Tool model (new)
      agent.py             # Agent model (new)
```

### SPEC-004-B: Tool Config Structure

**HTTP Tool Config:**
```json
{
  "base_url": "https://api.example.com",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "timeout_seconds": 30
}
```

**MCP Tool Config:**
```json
{
  "server_name": "mcp-server",
  "tool_name": "search",
  "transport": "stdio"
}
```

**Python Tool Config:**
```json
{
  "module": "app.tools.custom",
  "function": "execute_analysis",
  "async": true
}
```

### SPEC-004-C: Agent Config Structure

**Model Config:**
```json
{
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 0.9,
  "stop_sequences": ["Human:", "Assistant:"]
}
```

**Memory Config:**
```json
{
  "type": "sliding_window",
  "max_messages": 20,
  "max_tokens": 8000
}
```

### SPEC-004-D: Relationship Diagram

```
users (1) ----< (N) tools
users (1) ----< (N) agents
agents (1) ----< (N) tools (via tools JSONB array)
```

---

## Constraints

### Technical Constraints

- UUIDMixin, TimestampMixin, SoftDeleteMixin 사용 필수
- JSONB 필드에 대한 GIN 인덱스 적용
- Soft delete 패턴 준수

### Performance Constraints

- Tool/Agent 조회 시 100ms 이내 응답
- JSONB 쿼리 최적화를 위한 인덱스 전략 수립

### Security Constraints

- auth_config 필드 암호화 필수
- 공개 Tool/Agent 조회 시 인증 정보 제외
- 소유자 검증을 통한 접근 제어

---

## Dependencies

### Internal Dependencies

| Dependency | Source | Purpose |
|------------|--------|---------|
| Base, UUIDMixin, TimestampMixin, SoftDeleteMixin | SPEC-001 | 기본 모델 패턴 |
| User 모델 | SPEC-002 | 소유자 관계 |
| ToolType, ModelProvider | SPEC-001 | Enum 정의 (업데이트 필요) |

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| cryptography | >=41.0.0 | 인증 정보 암호화 |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ToolType enum 변경으로 인한 기존 코드 영향 | High | Medium | 마이그레이션 스크립트 작성 |
| 인증 정보 암호화 복잡성 | Medium | High | 암호화 유틸리티 모듈 분리 |
| tools JSONB 배열의 무결성 검증 | Medium | Medium | 애플리케이션 레벨 검증 |

---

## Related SPECs

- SPEC-001: Database Foundation Setup (depends on)
- SPEC-002: User Authentication Model (depends on)
- SPEC-003: Workflow Domain Models (related - uses Tool/Agent)
- SPEC-009: Tool/Agent API Endpoints (dependent)
- SPEC-012: Node Processor Framework (dependent - uses Tool/Agent)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-11 | workflow-spec | Initial SPEC creation |
