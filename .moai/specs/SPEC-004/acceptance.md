# SPEC-004 Acceptance Criteria: Tool & Agent Registry

## Tags

`[SPEC-004]` `[ACCEPTANCE]` `[TESTING]`

---

## Overview

Tool 및 Agent 레지스트리 모델의 완료 조건 및 테스트 시나리오를 정의합니다.

---

## Acceptance Criteria

### AC-001: Tool 모델 생성

**Given** 데이터베이스에 users 테이블이 존재하고
**When** Tool 모델을 사용하여 새로운 도구를 생성하면
**Then** tools 테이블에 레코드가 저장되고 UUID id가 자동 생성된다

**Verification:**
```python
async def test_create_tool(db_session, test_user):
    tool = Tool(
        owner_id=test_user.id,
        name="Test HTTP Tool",
        tool_type=ToolType.HTTP,
        config={"base_url": "https://api.example.com"},
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    db_session.add(tool)
    await db_session.commit()

    assert tool.id is not None
    assert tool.created_at is not None
    assert tool.is_active is True
    assert tool.is_public is False
```

---

### AC-002: Agent 모델 생성

**Given** 데이터베이스에 users 테이블이 존재하고
**When** Agent 모델을 사용하여 새로운 에이전트를 생성하면
**Then** agents 테이블에 레코드가 저장되고 UUID id가 자동 생성된다

**Verification:**
```python
async def test_create_agent(db_session, test_user):
    agent = Agent(
        owner_id=test_user.id,
        name="Test Claude Agent",
        model_provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-5-sonnet",
        system_prompt="You are a helpful assistant.",
        config={"temperature": 0.7, "max_tokens": 4096},
        tools=[],
    )
    db_session.add(agent)
    await db_session.commit()

    assert agent.id is not None
    assert agent.created_at is not None
    assert agent.is_active is True
```

---

### AC-003: ToolType Enum 업데이트

**Given** ToolType enum이 정의되어 있을 때
**When** 새로운 Tool 타입 값을 사용하면
**Then** HTTP, MCP, PYTHON, SHELL, BUILTIN 타입이 지원된다

**Verification:**
```python
def test_tool_type_enum():
    assert ToolType.HTTP.value == "http"
    assert ToolType.MCP.value == "mcp"
    assert ToolType.PYTHON.value == "python"
    assert ToolType.SHELL.value == "shell"
    assert ToolType.BUILTIN.value == "builtin"
```

---

### AC-004: User-Tool 관계

**Given** User와 Tool이 존재할 때
**When** Tool의 owner_id로 User를 조회하면
**Then** 해당 User의 모든 Tool 목록을 가져올 수 있다

**Verification:**
```python
async def test_user_tool_relationship(db_session, test_user):
    # Create multiple tools
    for i in range(3):
        tool = Tool(
            owner_id=test_user.id,
            name=f"Tool {i}",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
    await db_session.commit()

    # Query user's tools
    result = await db_session.execute(
        select(Tool).where(Tool.owner_id == test_user.id)
    )
    tools = result.scalars().all()

    assert len(tools) == 3
```

---

### AC-005: User-Agent 관계

**Given** User와 Agent가 존재할 때
**When** Agent의 owner_id로 User를 조회하면
**Then** 해당 User의 모든 Agent 목록을 가져올 수 있다

**Verification:**
```python
async def test_user_agent_relationship(db_session, test_user):
    agent = Agent(
        owner_id=test_user.id,
        name="Test Agent",
        model_provider=ModelProvider.OPENAI,
        model_name="gpt-4",
    )
    db_session.add(agent)
    await db_session.commit()

    result = await db_session.execute(
        select(Agent).where(Agent.owner_id == test_user.id)
    )
    agents = result.scalars().all()

    assert len(agents) == 1
    assert agents[0].name == "Test Agent"
```

---

### AC-006: Agent-Tool 연결

**Given** Agent와 Tool이 존재할 때
**When** Agent의 tools 배열에 Tool UUID를 추가하면
**Then** Agent가 해당 Tool을 참조할 수 있다

**Verification:**
```python
async def test_agent_tool_connection(db_session, test_user):
    # Create tool
    tool = Tool(
        owner_id=test_user.id,
        name="Search Tool",
        tool_type=ToolType.HTTP,
    )
    db_session.add(tool)
    await db_session.commit()

    # Create agent with tool reference
    agent = Agent(
        owner_id=test_user.id,
        name="Research Agent",
        model_provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-5-sonnet",
        tools=[str(tool.id)],
    )
    db_session.add(agent)
    await db_session.commit()

    assert str(tool.id) in agent.tools
```

---

### AC-007: Soft Delete 동작

**Given** Tool 또는 Agent가 존재할 때
**When** soft_delete() 메서드를 호출하면
**Then** deleted_at 타임스탬프가 설정되고 is_deleted가 True가 된다

**Verification:**
```python
async def test_soft_delete_tool(db_session, test_user):
    tool = Tool(
        owner_id=test_user.id,
        name="To Delete",
        tool_type=ToolType.HTTP,
    )
    db_session.add(tool)
    await db_session.commit()

    tool.soft_delete()
    await db_session.commit()

    assert tool.is_deleted is True
    assert tool.deleted_at is not None
```

---

### AC-008: 공개 Tool/Agent 조회

**Given** is_public=True인 Tool/Agent가 존재할 때
**When** 공개 항목을 조회하면
**Then** 다른 사용자도 해당 항목을 볼 수 있다

**Verification:**
```python
async def test_public_tool_access(db_session, user_a, user_b):
    # User A creates public tool
    public_tool = Tool(
        owner_id=user_a.id,
        name="Public Tool",
        tool_type=ToolType.BUILTIN,
        is_public=True,
    )
    db_session.add(public_tool)
    await db_session.commit()

    # User B can see public tools
    result = await db_session.execute(
        select(Tool).where(
            or_(
                Tool.owner_id == user_b.id,
                Tool.is_public == True
            )
        ).where(Tool.deleted_at.is_(None))
    )
    visible_tools = result.scalars().all()

    assert any(t.id == public_tool.id for t in visible_tools)
```

---

### AC-009: JSONB config 저장 및 조회

**Given** Tool에 config JSONB 필드가 존재할 때
**When** 복잡한 설정 객체를 저장하면
**Then** 설정이 올바르게 저장되고 조회된다

**Verification:**
```python
async def test_jsonb_config_storage(db_session, test_user):
    config = {
        "base_url": "https://api.example.com",
        "method": "POST",
        "headers": {"Authorization": "Bearer token"},
        "timeout_seconds": 30,
        "retry": {"max_attempts": 3, "backoff": 2.0}
    }

    tool = Tool(
        owner_id=test_user.id,
        name="Complex Config Tool",
        tool_type=ToolType.HTTP,
        config=config,
    )
    db_session.add(tool)
    await db_session.commit()

    # Reload from database
    await db_session.refresh(tool)

    assert tool.config["base_url"] == "https://api.example.com"
    assert tool.config["retry"]["max_attempts"] == 3
```

---

### AC-010: Rate Limit 설정

**Given** Tool에 rate_limit JSONB 필드가 존재할 때
**When** Rate limit 설정을 저장하면
**Then** 설정이 올바르게 저장된다

**Verification:**
```python
async def test_rate_limit_config(db_session, test_user):
    rate_limit = {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "concurrent_requests": 5
    }

    tool = Tool(
        owner_id=test_user.id,
        name="Rate Limited Tool",
        tool_type=ToolType.HTTP,
        rate_limit=rate_limit,
    )
    db_session.add(tool)
    await db_session.commit()

    assert tool.rate_limit["requests_per_minute"] == 60
```

---

### AC-011: Model Provider 검증

**Given** Agent에 model_provider 필드가 존재할 때
**When** 지원되는 provider 값을 사용하면
**Then** anthropic, openai, zhipuai 값이 저장된다

**Verification:**
```python
@pytest.mark.parametrize("provider,model", [
    (ModelProvider.ANTHROPIC, "claude-3-5-sonnet"),
    (ModelProvider.OPENAI, "gpt-4"),
    (ModelProvider.GLM, "glm-4"),
])
async def test_model_providers(db_session, test_user, provider, model):
    agent = Agent(
        owner_id=test_user.id,
        name=f"{provider.value} Agent",
        model_provider=provider,
        model_name=model,
    )
    db_session.add(agent)
    await db_session.commit()

    assert agent.model_provider == provider
```

---

### AC-012: Timestamp 자동 관리

**Given** Tool 또는 Agent가 생성/수정될 때
**When** 레코드가 저장되면
**Then** created_at과 updated_at이 자동으로 설정된다

**Verification:**
```python
async def test_timestamp_management(db_session, test_user):
    tool = Tool(
        owner_id=test_user.id,
        name="Timestamp Test",
        tool_type=ToolType.HTTP,
    )
    db_session.add(tool)
    await db_session.commit()

    created = tool.created_at
    updated = tool.updated_at

    # Update the tool
    await asyncio.sleep(0.1)
    tool.name = "Updated Name"
    await db_session.commit()
    await db_session.refresh(tool)

    assert tool.created_at == created
    assert tool.updated_at > updated
```

---

## Quality Gate Criteria

### Test Coverage

| Component | Required Coverage |
|-----------|------------------|
| Tool Model | >= 90% |
| Agent Model | >= 90% |
| Enum Updates | 100% |

### Code Quality

- [ ] ruff lint 통과
- [ ] mypy type check 통과
- [ ] 모든 public 메서드 docstring 작성
- [ ] 테스트 코드 작성 완료

### Security Checklist

- [ ] auth_config 필드 암호화 구현
- [ ] 공개 Tool/Agent 조회 시 인증 정보 마스킹
- [ ] SQL injection 방지 확인

### Migration Verification

- [ ] Alembic upgrade 성공
- [ ] Alembic downgrade 성공
- [ ] 기존 데이터 무결성 유지

---

## Definition of Done

1. **모델 구현 완료**
   - Tool 모델 파일 생성
   - Agent 모델 파일 생성
   - ToolType enum 업데이트

2. **마이그레이션 완료**
   - Alembic 마이그레이션 스크립트 생성
   - 테스트 환경에서 마이그레이션 검증

3. **테스트 완료**
   - 모든 AC 테스트 통과
   - 커버리지 목표 달성

4. **코드 품질 검증**
   - Lint 통과
   - Type check 통과
   - 문서화 완료

5. **리뷰 완료**
   - PR 생성 및 코드 리뷰
   - 보안 검토 완료

---

## Related Documents

- [spec.md](spec.md) - 상세 요구사항
- [plan.md](plan.md) - 구현 계획
- [SPEC-001/acceptance.md](../SPEC-001/acceptance.md) - Database Foundation 인수 조건

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-11 | workflow-spec | Initial acceptance criteria creation |
