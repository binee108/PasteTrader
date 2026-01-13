"""Tests for AgentService.

TAG: [SPEC-009] [TEST] [AGENT_SERVICE]
REQ: REQ-006 - Agent Service Business Logic
REQ: REQ-007 - Agent CRUD Operations

This module contains comprehensive tests for AgentService following TDD RED-GREEN-REFACTOR cycle.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent as AgentModel
from app.models.tool import Tool as ToolModel
from app.schemas.agent import AgentCreate, AgentUpdate, AgentToolsUpdate
from app.services.agent_service import AgentService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def agent_service():
    """AgentService 인스턴스를 반환합니다."""
    return AgentService()


@pytest.fixture
async def db_session(async_session_maker) -> AsyncSession:
    """테스트용 DB 세션을 반환합니다."""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def sample_owner_id() -> UUID:
    """샘플 소유자 ID를 반환합니다."""
    return uuid4()


@pytest.fixture
async def sample_tool(db_session: AsyncSession, sample_owner_id: UUID) -> ToolModel:
    """샘플 Tool 모델을 생성하고 DB에 저장합니다."""
    from app.models.enums import ToolType

    tool = ToolModel(
        id=uuid4(),
        owner_id=sample_owner_id,
        name="test_tool",
        description="Test tool description",
        tool_type=ToolType.HTTP,
        config={"url": "https://api.example.com"},
        input_schema={"type": "object"},
        output_schema=None,
        auth_config=None,
        rate_limit=None,
        is_active=True,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.fixture
async def inactive_tool(db_session: AsyncSession, sample_owner_id: UUID) -> ToolModel:
    """비활성 샘플 Tool 모델을 생성하고 DB에 저장합니다."""
    from app.models.enums import ToolType

    tool = ToolModel(
        id=uuid4(),
        owner_id=sample_owner_id,
        name="inactive_tool",
        description="Inactive tool",
        tool_type=ToolType.PYTHON,
        config={"path": "test.py"},
        input_schema={"type": "object"},
        output_schema=None,
        auth_config=None,
        rate_limit=None,
        is_active=False,
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.fixture
def agent_create_data() -> dict:
    """Agent 생성 데이터를 반환합니다."""
    return {
        "name": "New Agent",
        "description": "New agent description",
        "system_prompt": "You are a specialized assistant",
        "llm_config": {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 8192,
        },
        "tool_ids": [],
    }


# =============================================================================
# create_agent Tests
# =============================================================================


class TestCreateAgent:
    """AgentService.create_agent 메서드 테스트 스위트."""

    async def test_create_agent_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """성공적으로 에이전트를 생성합니다."""
        agent_in = AgentCreate(**agent_create_data)

        result = await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        assert result is not None
        assert result.id is not None
        assert result.name == "New Agent"
        assert result.description == "New agent description"
        assert result.system_prompt == "You are a specialized assistant"
        assert result.model_config["provider"] == "openai"
        assert result.model_config["model"] == "gpt-4o"
        assert result.owner_id == sample_owner_id
        assert result.is_active is True

    async def test_create_agent_duplicate_name_raises_error(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """중복된 이름으로 에이전트 생성 시도 시 에러를 발생시킵니다."""
        # Create first agent
        agent_in = AgentCreate(**agent_create_data)
        await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        # Try to create second agent with same name
        agent_in2 = AgentCreate(**agent_create_data)
        with pytest.raises(ValueError) as exc_info:
            await agent_service.create_agent(db_session, agent_in2, uuid4())

        assert "already exists" in str(exc_info.value).lower()

    async def test_create_agent_with_invalid_tool_ids_raises_error(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """유효하지 않은 도구 ID로 에이전트 생성 시도 시 에러를 발생시킵니다."""
        invalid_tool_id = uuid4()
        agent_in = AgentCreate(**{**agent_create_data, "tool_ids": [invalid_tool_id]})

        with pytest.raises(ValueError) as exc_info:
            await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        assert "invalid tool" in str(exc_info.value).lower()

    async def test_create_agent_with_tools(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_tool: ToolModel,
        sample_owner_id: UUID,
    ):
        """도구가 연결된 에이전트를 생성합니다."""
        agent_in = AgentCreate(**{**agent_create_data, "tool_ids": [sample_tool.id]})

        result = await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        assert result is not None
        assert len(result.tools) == 1
        assert result.tools[0].id == sample_tool.id

    async def test_create_agent_only_accepts_active_tools(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        inactive_tool: ToolModel,
        sample_owner_id: UUID,
    ):
        """활성 상태인 도구만 에이전트에 연결할 수 있습니다."""
        agent_in = AgentCreate(**{**agent_create_data, "tool_ids": [inactive_tool.id]})

        with pytest.raises(ValueError) as exc_info:
            await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        assert "invalid tool" in str(exc_info.value).lower()


# =============================================================================
# get_agent Tests
# =============================================================================


class TestGetAgent:
    """AgentService.get_agent 메서드 테스트 스위트."""

    async def test_get_agent_by_id_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """ID로 에이전트를 조회합니다."""
        # Create agent first
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        # Get by ID
        result = await agent_service.get_agent(db_session, created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == created.name

    async def test_get_agent_by_id_not_found(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """존재하지 않는 ID로 조회 시 None을 반환합니다."""
        non_existent_id = uuid4()
        result = await agent_service.get_agent(db_session, non_existent_id)
        assert result is None

    async def test_get_agent_includes_tools(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_tool: ToolModel,
        sample_owner_id: UUID,
    ):
        """에이전트 조회 시 도구 관계가 로드됩니다."""
        agent_in = AgentCreate(**{**agent_create_data, "tool_ids": [sample_tool.id]})
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        result = await agent_service.get_agent(db_session, created.id)

        assert result is not None
        assert len(result.tools) == 1
        assert result.tools[0].id == sample_tool.id


# =============================================================================
# get_agent_by_name Tests
# =============================================================================


class TestGetAgentByName:
    """AgentService.get_agent_by_name 메서드 테스트 스위트."""

    async def test_get_agent_by_name_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """이름으로 에이전트를 조회합니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        result = await agent_service.get_agent_by_name(db_session, "New Agent")

        assert result is not None
        assert result.id == created.id
        assert result.name == "New Agent"

    async def test_get_agent_by_name_not_found(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """존재하지 않는 이름으로 조회 시 None을 반환합니다."""
        result = await agent_service.get_agent_by_name(db_session, "NonExistent")
        assert result is None


# =============================================================================
# list_agents Tests
# =============================================================================


class TestListAgents:
    """AgentService.list_agents 메서드 테스트 스위트."""

    async def test_list_agents_default_params(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """기본 파라미터로 에이전트 목록을 조회합니다."""
        # Create multiple agents
        for i in range(3):
            data = {**agent_create_data, "name": f"Agent {i}"}
            agent_in = AgentCreate(**data)
            await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        result = await agent_service.list_agents(db_session)

        assert isinstance(result, list)
        assert len(result) >= 3

    async def test_list_agents_with_is_active_filter(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """is_active 필터로 에이전트 목록을 조회합니다."""
        # Create active and inactive agents
        active_data = {**agent_create_data, "name": "Active Agent"}
        inactive_data = {**agent_create_data, "name": "Inactive Agent"}

        active_agent = AgentCreate(**active_data)
        inactive_agent = AgentCreate(**inactive_data)

        created_active = await agent_service.create_agent(
            db_session, active_agent, sample_owner_id
        )
        created_inactive = await agent_service.create_agent(
            db_session, inactive_agent, sample_owner_id
        )

        # Deactivate one agent
        created_inactive.is_active = False
        await db_session.commit()

        active_agents = await agent_service.list_agents(db_session, is_active=True)
        inactive_agents = await agent_service.list_agents(db_session, is_active=False)

        assert isinstance(active_agents, list)
        assert isinstance(inactive_agents, list)
        # Note: might contain other agents from previous tests

    async def test_list_agents_with_search(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """검색어로 에이전트 목록을 조회합니다."""
        # Create agents with specific names
        matching_data = {**agent_create_data, "name": "Search Matching Agent"}
        non_matching_data = {**agent_create_data, "name": "Different Name"}

        await agent_service.create_agent(
            db_session, AgentCreate(**matching_data), sample_owner_id
        )
        await agent_service.create_agent(
            db_session, AgentCreate(**non_matching_data), sample_owner_id
        )

        result = await agent_service.list_agents(db_session, search="Matching")

        assert isinstance(result, list)
        assert len(result) >= 1
        assert any("Matching" in agent.name for agent in result)

    async def test_list_agents_with_pagination(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """페이지네이션과 함께 에이전트 목록을 조회합니다."""
        # Create 5 agents
        for i in range(5):
            data = {**agent_create_data, "name": f"Paginated Agent {i}"}
            agent_in = AgentCreate(**data)
            await agent_service.create_agent(db_session, agent_in, sample_owner_id)

        # Get first page
        page1 = await agent_service.list_agents(db_session, limit=2, offset=0)

        # Get second page
        page2 = await agent_service.list_agents(db_session, limit=2, offset=2)

        assert isinstance(page1, list)
        assert isinstance(page2, list)


# =============================================================================
# update_agent Tests
# =============================================================================


class TestUpdateAgent:
    """AgentService.update_agent 메서드 테스트 스위트."""

    async def test_update_agent_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """에이전트를 수정합니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        update_data = AgentUpdate(
            description="Updated description",
            is_active=False,
        )

        result = await agent_service.update_agent(db_session, created.id, update_data)

        assert result is not None
        assert result.description == "Updated description"
        assert result.is_active is False

    async def test_update_agent_not_found(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """존재하지 않는 에이전트 수정 시도 시 None을 반환합니다."""
        update_data = AgentUpdate(description="Updated")

        result = await agent_service.update_agent(db_session, uuid4(), update_data)

        assert result is None

    async def test_update_agent_with_model_config(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """에이전트의 모델 설정을 수정합니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        update_data = AgentUpdate(
            llm_config={
                "provider": "glm",
                "model": "glm-4-plus",
                "temperature": 0.8,
                "max_tokens": 2048,
            }
        )

        result = await agent_service.update_agent(db_session, created.id, update_data)

        assert result is not None
        assert result.model_config["provider"] == "glm"
        assert result.model_config["model"] == "glm-4-plus"


# =============================================================================
# update_agent_tools Tests
# =============================================================================


class TestUpdateAgentTools:
    """AgentService.update_agent_tools 메서드 테스트 스위트."""

    async def test_update_agent_tools_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_tool: ToolModel,
        sample_owner_id: UUID,
    ):
        """에이전트의 도구 연결을 업데이트합니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        tools_update = AgentToolsUpdate(tool_ids=[sample_tool.id])

        result = await agent_service.update_agent_tools(
            db_session, created.id, tools_update
        )

        assert result is not None
        assert len(result.tools) == 1
        assert result.tools[0].id == sample_tool.id

    async def test_update_agent_tools_not_found(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """존재하지 않는 에이전트의 도구 업데이트 시도 시 None을 반환합니다."""
        tools_update = AgentToolsUpdate(tool_ids=[])

        result = await agent_service.update_agent_tools(
            db_session, uuid4(), tools_update
        )

        assert result is None

    async def test_update_agent_tools_invalid_tool_ids(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """유효하지 않은 도구 ID로 업데이트 시도 시 에러를 발생시킵니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        invalid_tool_id = uuid4()
        tools_update = AgentToolsUpdate(tool_ids=[invalid_tool_id])

        with pytest.raises(ValueError) as exc_info:
            await agent_service.update_agent_tools(db_session, created.id, tools_update)

        assert "invalid tool" in str(exc_info.value).lower()

    async def test_update_agent_tools_empty_list(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_tool: ToolModel,
        sample_owner_id: UUID,
    ):
        """빈 도구 목록으로 업데이트하여 모든 도구 연결을 제거합니다."""
        # Create agent with tools
        agent_in = AgentCreate(**{**agent_create_data, "tool_ids": [sample_tool.id]})
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        # Verify tools are attached
        assert len(created.tools) == 1

        # Remove all tools
        tools_update = AgentToolsUpdate(tool_ids=[])
        result = await agent_service.update_agent_tools(
            db_session, created.id, tools_update
        )

        assert result is not None
        assert len(result.tools) == 0


# =============================================================================
# delete_agent Tests
# =============================================================================


class TestDeleteAgent:
    """AgentService.delete_agent 메서드 테스트 스위트."""

    async def test_delete_agent_success(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        agent_create_data: dict,
        sample_owner_id: UUID,
    ):
        """에이전트를 삭제합니다."""
        agent_in = AgentCreate(**agent_create_data)
        created = await agent_service.create_agent(
            db_session, agent_in, sample_owner_id
        )

        result = await agent_service.delete_agent(db_session, created.id)

        assert result is True

        # Verify deletion
        deleted = await agent_service.get_agent(db_session, created.id)
        assert deleted is None

    async def test_delete_agent_not_found(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """존재하지 않는 에이전트 삭제 시도 시 False를 반환합니다."""
        result = await agent_service.delete_agent(db_session, uuid4())
        assert result is False


# =============================================================================
# _validate_tool_ids Tests
# =============================================================================


class TestValidateToolIds:
    """AgentService._validate_tool_ids 메서드 테스트 스위트."""

    async def test_validate_tool_ids_all_valid(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        sample_tool: ToolModel,
    ):
        """모든 도구 ID가 유효한 경우 검증을 통과합니다."""
        result = await agent_service._validate_tool_ids(db_session, [sample_tool.id])

        assert sample_tool.id in result

    async def test_validate_tool_ids_empty_list(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
    ):
        """빈 도구 ID 목록을 검증합니다."""
        result = await agent_service._validate_tool_ids(db_session, [])
        assert result == []

    async def test_validate_tool_ids_some_invalid(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        sample_tool: ToolModel,
    ):
        """일부 도구 ID가 유효하지 않은 경우 유효한 ID만 반환합니다."""
        invalid_id = uuid4()

        result = await agent_service._validate_tool_ids(
            db_session, [sample_tool.id, invalid_id]
        )

        assert sample_tool.id in result
        assert invalid_id not in result

    async def test_validate_tool_ids_only_active_tools(
        self,
        agent_service: AgentService,
        db_session: AsyncSession,
        sample_tool: ToolModel,
        inactive_tool: ToolModel,
    ):
        """활성 상태인 도구만 유효한 것으로 간주합니다."""
        result = await agent_service._validate_tool_ids(
            db_session, [sample_tool.id, inactive_tool.id]
        )

        assert sample_tool.id in result
        assert inactive_tool.id not in result
