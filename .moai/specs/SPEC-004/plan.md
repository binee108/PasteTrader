# SPEC-004 Implementation Plan: Tool & Agent Registry

## Tags

`[SPEC-004]` `[IMPLEMENTATION]` `[PLAN]`

---

## Overview

Tool 및 Agent 레지스트리 모델 구현을 위한 상세 계획입니다.

---

## Milestones

### Primary Goal: Core Model Implementation

모델 파일 생성 및 기본 구조 구현

**Tasks:**

1. **ToolType Enum 업데이트**
   - `backend/app/models/enums.py` 수정
   - 기존: DATA_FETCHER, TECHNICAL_INDICATOR, MARKET_SCREENER, CODE_ANALYZER, NOTIFICATION
   - 변경: HTTP, MCP, PYTHON, SHELL, BUILTIN
   - 마이그레이션 호환성 고려

2. **Tool 모델 구현**
   - `backend/app/models/tool.py` 생성
   - UUIDMixin, TimestampMixin, SoftDeleteMixin 적용
   - JSONB 필드: config, input_schema, output_schema, auth_config, rate_limit
   - User 관계 설정 (owner_id FK)

3. **Agent 모델 구현**
   - `backend/app/models/agent.py` 생성
   - UUIDMixin, TimestampMixin, SoftDeleteMixin 적용
   - JSONB 필드: config, tools, memory_config
   - User 관계 설정 (owner_id FK)

4. **모델 Export 업데이트**
   - `backend/app/models/__init__.py` 수정
   - Tool, Agent 모델 export 추가

### Secondary Goal: Database Migration

Alembic 마이그레이션 스크립트 생성

**Tasks:**

1. **마이그레이션 파일 생성**
   - `alembic revision --autogenerate -m "add_tool_agent_models"`
   - tools 테이블 생성
   - agents 테이블 생성

2. **인덱스 정의**
   - tools: owner_id, tool_type, is_active, is_public
   - agents: owner_id, model_provider, is_active, is_public
   - JSONB GIN 인덱스: config 필드

3. **마이그레이션 테스트**
   - upgrade/downgrade 테스트
   - 데이터 무결성 검증

### Final Goal: Validation & Testing

모델 검증 및 테스트 코드 작성

**Tasks:**

1. **단위 테스트 작성**
   - Tool 모델 CRUD 테스트
   - Agent 모델 CRUD 테스트
   - Soft delete 동작 테스트
   - 관계 테스트 (User-Tool, User-Agent)

2. **JSONB 스키마 검증**
   - config 구조 검증 로직
   - input_schema/output_schema JSON Schema 검증
   - tools 배열 UUID 유효성 검증

---

## Technical Approach

### 1. Model Architecture

```python
# backend/app/models/tool.py
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import ToolType


class Tool(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tools"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    auth_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rate_limit: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    owner = relationship("User", back_populates="tools")
```

### 2. Enum Update Strategy

```python
# backend/app/models/enums.py - Updated ToolType

class ToolType(str, Enum):
    """Tool execution type classification."""

    HTTP = "http"           # HTTP API 호출
    MCP = "mcp"             # MCP 서버 도구
    PYTHON = "python"       # Python 함수 실행
    SHELL = "shell"         # Shell 명령 실행
    BUILTIN = "builtin"     # 내장 도구
```

### 3. Index Strategy

```sql
-- tools 테이블 인덱스
CREATE INDEX idx_tools_owner ON tools(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tools_type ON tools(tool_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_tools_public ON tools(is_public) WHERE deleted_at IS NULL AND is_active = TRUE;
CREATE INDEX idx_tools_config ON tools USING GIN (config jsonb_path_ops);

-- agents 테이블 인덱스
CREATE INDEX idx_agents_owner ON agents(owner_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_provider ON agents(model_provider) WHERE deleted_at IS NULL;
CREATE INDEX idx_agents_public ON agents(is_public) WHERE deleted_at IS NULL AND is_active = TRUE;
CREATE INDEX idx_agents_config ON agents USING GIN (config jsonb_path_ops);
```

---

## Architecture Design

### Entity Relationships

```
+------------------+         +------------------+
|      users       |         |      users       |
+------------------+         +------------------+
         |                            |
         | 1:N                        | 1:N
         v                            v
+------------------+         +------------------+
|      tools       |<--------|      agents      |
+------------------+  N:M    +------------------+
| id (UUID)        | (via    | id (UUID)        |
| owner_id (FK)    | tools   | owner_id (FK)    |
| name             | JSONB)  | name             |
| tool_type        |         | model_provider   |
| config (JSONB)   |         | model_name       |
| input_schema     |         | system_prompt    |
| output_schema    |         | config (JSONB)   |
| auth_config      |         | tools (JSONB[])  |
| rate_limit       |         | memory_config    |
| is_active        |         | is_active        |
| is_public        |         | is_public        |
+------------------+         +------------------+
```

### Data Flow

```
1. Tool 생성
   User -> API -> Tool Model -> Database
                      |
                      v
              Encrypt auth_config
              Validate input_schema

2. Agent 생성
   User -> API -> Agent Model -> Database
                      |
                      v
              Validate tools[] UUIDs
              Store config parameters

3. Agent-Tool 연결
   Agent.tools = ["uuid1", "uuid2"]
   Runtime: Load Tools by UUIDs
```

---

## Risk Mitigation

### ToolType Enum 변경 전략

1. **하위 호환성 유지**
   - 기존 ToolType 값 유지 (deprecated 표시)
   - 새로운 ToolType 값 추가
   - 마이그레이션에서 기존 데이터 변환

2. **점진적 마이그레이션**
   ```python
   class ToolType(str, Enum):
       # New types (preferred)
       HTTP = "http"
       MCP = "mcp"
       PYTHON = "python"
       SHELL = "shell"
       BUILTIN = "builtin"

       # Deprecated (to be removed)
       DATA_FETCHER = "data_fetcher"  # -> HTTP
       TECHNICAL_INDICATOR = "technical_indicator"  # -> PYTHON
       MARKET_SCREENER = "market_screener"  # -> HTTP
       CODE_ANALYZER = "code_analyzer"  # -> PYTHON
       NOTIFICATION = "notification"  # -> HTTP
   ```

### 인증 정보 암호화

1. **암호화 유틸리티 모듈**
   ```python
   # backend/app/utils/crypto.py
   from cryptography.fernet import Fernet

   def encrypt_auth_config(config: dict) -> dict:
       ...

   def decrypt_auth_config(encrypted: dict) -> dict:
       ...
   ```

2. **환경 변수 관리**
   - `ENCRYPTION_KEY` 환경 변수 사용
   - Key rotation 전략 수립

---

## Quality Gates

### Test Coverage Requirements

- Tool 모델: 90% 이상
- Agent 모델: 90% 이상
- Enum 변경: 100%

### Code Quality

- ruff lint 통과
- mypy type check 통과
- 모든 public 메서드 docstring 작성

### Security Review

- auth_config 암호화 검증
- SQL injection 방지 확인
- 접근 제어 로직 검증

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [acceptance.md](acceptance.md) - 인수 조건
- [SPEC-001](../SPEC-001/spec.md) - Database Foundation
- [database-schema.md](/docs/architecture/database-schema.md) - DB 스키마

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-11 | workflow-spec | Initial plan creation |
