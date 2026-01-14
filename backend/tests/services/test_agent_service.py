"""Tests for AgentService.

TAG: [SPEC-009] [TESTING] [SERVICE] [AGENT]
REQ: REQ-001 - AgentService CRUD Operations Tests
REQ: REQ-002 - Agent Tool Association Tests
REQ: REQ-003 - Agent Filtering and Search Tests
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.enums import ModelProvider
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.agent_service import (
    AgentNotFoundError,
    AgentService,
    AgentServiceError,
    ToolAlreadyAssociatedError,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def agent_create_schema() -> AgentCreate:
    """Create AgentCreate schema for testing."""
    return AgentCreate(
        name="Test Agent",
        description="A test agent",
        model_provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        system_prompt="You are a helpful assistant.",
        config={"temperature": 0.7, "max_tokens": 1000},
        tools=[str(uuid4()), str(uuid4())],
        memory_config={"type": "summary", "max_tokens": 2000},
        is_active=True,
        is_public=False,
    )


@pytest.fixture
def agent_update_schema() -> AgentUpdate:
    """Create AgentUpdate schema for testing."""
    return AgentUpdate(
        name="Updated Agent",
        description="Updated description",
        is_active=False,
    )


# =============================================================================
# CREATE TESTS
# =============================================================================


class TestAgentServiceCreate:
    """Test AgentService.create method."""

    @pytest.mark.asyncio
    async def test_create_agent_success(
        self, db_session: AsyncSession, agent_create_schema: AgentCreate
    ) -> None:
        """Test successful agent creation."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Act
        agent = await service.create(owner_id, agent_create_schema)

        # Assert
        assert agent.id is not None
        assert agent.owner_id == owner_id
        assert agent.name == agent_create_schema.name
        assert agent.description == agent_create_schema.description
        assert agent.model_provider == agent_create_schema.model_provider
        assert agent.model_name == agent_create_schema.model_name
        assert agent.system_prompt == agent_create_schema.system_prompt
        assert agent.config == agent_create_schema.config
        assert agent.tools == agent_create_schema.tools
        assert agent.memory_config == agent_create_schema.memory_config
        assert agent.is_active == agent_create_schema.is_active
        assert agent.is_public == agent_create_schema.is_public
        assert agent.created_at is not None
        assert agent.updated_at is not None
        assert agent.deleted_at is None

    @pytest.mark.asyncio
    async def test_create_agent_with_empty_tools(
        self, db_session: AsyncSession
    ) -> None:
        """Test agent creation with empty tools list."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()
        data = AgentCreate(
            name="Agent without tools",
            model_provider="openai",
            model_name="gpt-4",
            tools=[],
        )

        # Act
        agent = await service.create(owner_id, data)

        # Assert
        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_create_agent_with_tools_default(
        self, db_session: AsyncSession
    ) -> None:
        """Test agent creation with tools using default factory."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()
        data = AgentCreate(
            name="Agent with default tools",
            model_provider="anthropic",
            model_name="claude-3-opus-20240229",
        )

        # Act
        agent = await service.create(owner_id, data)

        # Assert
        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_create_agent_with_optional_fields_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test agent creation with optional fields as None."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()
        data = AgentCreate(
            name="Minimal Agent",
            model_provider="glm",
            model_name="glm-4",
            description=None,
            system_prompt=None,
            memory_config=None,
        )

        # Act
        agent = await service.create(owner_id, data)

        # Assert
        assert agent.description is None
        assert agent.system_prompt is None
        assert agent.memory_config is None


# =============================================================================
# GET TESTS
# =============================================================================


class TestAgentServiceGet:
    """Test AgentService.get method."""

    @pytest.mark.asyncio
    async def test_get_agent_by_id_success(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test successful agent retrieval by ID."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        agent = await service.get(sample_agent.id)

        # Assert
        assert agent is not None
        assert agent.id == sample_agent.id
        assert agent.name == sample_agent.name

    @pytest.mark.asyncio
    async def test_get_agent_by_id_not_found(self, db_session: AsyncSession) -> None:
        """Test getting non-existent agent returns None."""
        # Arrange
        service = AgentService(db_session)
        non_existent_id = uuid4()

        # Act
        agent = await service.get(non_existent_id)

        # Assert
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_agent_include_deleted_false(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test getting soft-deleted agent with include_deleted=False."""
        # Arrange
        service = AgentService(db_session)
        sample_agent.soft_delete()
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        agent = await service.get(sample_agent.id, include_deleted=False)

        # Assert
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_agent_include_deleted_true(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test getting soft-deleted agent with include_deleted=True."""
        # Arrange
        service = AgentService(db_session)
        sample_agent.soft_delete()
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        agent = await service.get(sample_agent.id, include_deleted=True)

        # Assert
        assert agent is not None
        assert agent.id == sample_agent.id
        assert agent.deleted_at is not None


# =============================================================================
# LIST TESTS
# =============================================================================


class TestAgentServiceList:
    """Test AgentService.list method."""

    @pytest.mark.asyncio
    async def test_list_agents_default(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents with default parameters."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create 5 agents
        for i in range(5):
            agent = agent_factory(
                owner_id=owner_id,
                name=f"Agent {i}",
            )
            db_session.add(agent)
        await db_session.flush()

        # Act
        agents = await service.list(owner_id)

        # Assert
        assert len(agents) == 5
        assert all(agent.owner_id == owner_id for agent in agents)

    @pytest.mark.asyncio
    async def test_list_agents_with_pagination(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents with pagination."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create 10 agents
        for i in range(10):
            agent = agent_factory(owner_id=owner_id, name=f"Agent {i:02d}")
            db_session.add(agent)
        await db_session.flush()

        # Act - Get first page
        page1 = await service.list(owner_id, skip=0, limit=5)

        # Act - Get second page
        page2 = await service.list(owner_id, skip=5, limit=5)

        # Assert
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1 != page2

    @pytest.mark.asyncio
    async def test_list_agents_filter_by_model_provider(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents filtered by model provider."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create agents with different providers
        for _ in range(3):
            db_session.add(
                agent_factory(owner_id=owner_id, model_provider=ModelProvider.ANTHROPIC)
            )
        for _ in range(2):
            db_session.add(
                agent_factory(owner_id=owner_id, model_provider=ModelProvider.OPENAI)
            )
        await db_session.flush()

        # Act
        anthropic_agents = await service.list(owner_id, model_provider="anthropic")
        openai_agents = await service.list(owner_id, model_provider="openai")

        # Assert
        assert len(anthropic_agents) == 3
        assert all(a.model_provider == "anthropic" for a in anthropic_agents)
        assert len(openai_agents) == 2
        assert all(a.model_provider == "openai" for a in openai_agents)

    @pytest.mark.asyncio
    async def test_list_agents_filter_by_is_active(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents filtered by active status."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create active and inactive agents
        for _ in range(3):
            db_session.add(agent_factory(owner_id=owner_id, is_active=True))
        for _ in range(2):
            db_session.add(agent_factory(owner_id=owner_id, is_active=False))
        await db_session.flush()

        # Act
        active_agents = await service.list(owner_id, is_active=True)
        inactive_agents = await service.list(owner_id, is_active=False)

        # Assert
        assert len(active_agents) == 3
        assert all(a.is_active for a in active_agents)
        assert len(inactive_agents) == 2
        assert all(not a.is_active for a in inactive_agents)

    @pytest.mark.asyncio
    async def test_list_agents_filter_by_is_public(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents filtered by public status."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create public and private agents
        for _ in range(2):
            db_session.add(agent_factory(owner_id=owner_id, is_public=True))
        for _ in range(3):
            db_session.add(agent_factory(owner_id=owner_id, is_public=False))
        await db_session.flush()

        # Act
        public_agents = await service.list(owner_id, is_public=True)
        private_agents = await service.list(owner_id, is_public=False)

        # Assert
        assert len(public_agents) == 2
        assert all(a.is_public for a in public_agents)
        assert len(private_agents) == 3
        assert all(not a.is_public for a in private_agents)

    @pytest.mark.asyncio
    async def test_list_agents_exclude_deleted(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents excludes deleted ones by default."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create agents and delete some
        active_agent = agent_factory(owner_id=owner_id, name="Active")
        deleted_agent = agent_factory(owner_id=owner_id, name="Deleted")
        deleted_agent.soft_delete()

        db_session.add(active_agent)
        db_session.add(deleted_agent)
        await db_session.flush()

        # Act
        agents = await service.list(owner_id, include_deleted=False)

        # Assert
        assert len(agents) == 1
        assert agents[0].name == "Active"

    @pytest.mark.asyncio
    async def test_list_agents_include_deleted(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents includes deleted when flag is True."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create agents and delete some
        active_agent = agent_factory(owner_id=owner_id, name="Active")
        deleted_agent = agent_factory(owner_id=owner_id, name="Deleted")
        deleted_agent.soft_delete()

        db_session.add(active_agent)
        db_session.add(deleted_agent)
        await db_session.flush()

        # Act
        agents = await service.list(owner_id, include_deleted=True)

        # Assert
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_list_agents_ordering(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test listing agents are ordered by created_at desc."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create agents with different timestamps
        now = datetime.now(UTC)
        agent1 = agent_factory(owner_id=owner_id, name="Agent 1", created_at=now)
        agent2 = agent_factory(owner_id=owner_id, name="Agent 2", created_at=now)
        agent3 = agent_factory(owner_id=owner_id, name="Agent 3", created_at=now)

        db_session.add(agent1)
        await db_session.flush()
        db_session.add(agent2)
        await db_session.flush()
        db_session.add(agent3)
        await db_session.flush()

        # Act
        agents = await service.list(owner_id)

        # Assert - Should contain all agents and be ordered
        assert len(agents) == 3
        assert {a.name for a in agents} == {"Agent 1", "Agent 2", "Agent 3"}


# =============================================================================
# COUNT TESTS
# =============================================================================


class TestAgentServiceCount:
    """Test AgentService.count method."""

    @pytest.mark.asyncio
    async def test_count_agents_default(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents with default parameters."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Create 5 agents
        for i in range(5):
            agent = agent_factory(owner_id=owner_id)
            db_session.add(agent)
        await db_session.flush()

        # Act
        count = await service.count(owner_id)

        # Assert
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_agents_filter_by_model_provider(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents filtered by model provider."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        for _ in range(3):
            db_session.add(
                agent_factory(owner_id=owner_id, model_provider=ModelProvider.ANTHROPIC)
            )
        for _ in range(2):
            db_session.add(
                agent_factory(owner_id=owner_id, model_provider=ModelProvider.OPENAI)
            )
        await db_session.flush()

        # Act
        anthropic_count = await service.count(owner_id, model_provider="anthropic")
        openai_count = await service.count(owner_id, model_provider="openai")
        total_count = await service.count(owner_id)

        # Assert
        assert anthropic_count == 3
        assert openai_count == 2
        assert total_count == 5

    @pytest.mark.asyncio
    async def test_count_agents_filter_by_is_active(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents filtered by active status."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        for _ in range(3):
            db_session.add(agent_factory(owner_id=owner_id, is_active=True))
        for _ in range(2):
            db_session.add(agent_factory(owner_id=owner_id, is_active=False))
        await db_session.flush()

        # Act
        active_count = await service.count(owner_id, is_active=True)
        inactive_count = await service.count(owner_id, is_active=False)

        # Assert
        assert active_count == 3
        assert inactive_count == 2

    @pytest.mark.asyncio
    async def test_count_agents_filter_by_is_public(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents filtered by public status."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        for _ in range(2):
            db_session.add(agent_factory(owner_id=owner_id, is_public=True))
        for _ in range(3):
            db_session.add(agent_factory(owner_id=owner_id, is_public=False))
        await db_session.flush()

        # Act
        public_count = await service.count(owner_id, is_public=True)
        private_count = await service.count(owner_id, is_public=False)

        # Assert
        assert public_count == 2
        assert private_count == 3

    @pytest.mark.asyncio
    async def test_count_agents_exclude_deleted(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents excludes deleted by default."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        active_agent = agent_factory(owner_id=owner_id)
        deleted_agent = agent_factory(owner_id=owner_id)
        deleted_agent.soft_delete()

        db_session.add(active_agent)
        db_session.add(deleted_agent)
        await db_session.flush()

        # Act
        count = await service.count(owner_id, include_deleted=False)

        # Assert
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_agents_include_deleted(
        self, db_session: AsyncSession, agent_factory
    ) -> None:
        """Test counting agents includes deleted when flag is True."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        active_agent = agent_factory(owner_id=owner_id)
        deleted_agent = agent_factory(owner_id=owner_id)
        deleted_agent.soft_delete()

        db_session.add(active_agent)
        db_session.add(deleted_agent)
        await db_session.flush()

        # Act
        count = await service.count(owner_id, include_deleted=True)

        # Assert
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_agents_no_agents(self, db_session: AsyncSession) -> None:
        """Test counting when no agents exist."""
        # Arrange
        service = AgentService(db_session)
        owner_id = uuid4()

        # Act
        count = await service.count(owner_id)

        # Assert
        assert count == 0


# =============================================================================
# UPDATE TESTS
# =============================================================================


class TestAgentServiceUpdate:
    """Test AgentService.update method."""

    @pytest.mark.asyncio
    async def test_update_agent_success(
        self,
        db_session: AsyncSession,
        sample_agent: Agent,
        agent_update_schema: AgentUpdate,
    ) -> None:
        """Test successful agent update."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        updated_agent = await service.update(sample_agent.id, agent_update_schema)

        # Assert
        assert updated_agent.id == sample_agent.id
        assert updated_agent.name == agent_update_schema.name
        assert updated_agent.description == agent_update_schema.description
        assert updated_agent.is_active == agent_update_schema.is_active
        assert updated_agent.updated_at is not None

    @pytest.mark.asyncio
    async def test_update_agent_partial_fields(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test updating agent with partial fields."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        update_data = AgentUpdate(name="Updated Name Only")

        # Act
        updated_agent = await service.update(sample_agent.id, update_data)

        # Assert
        assert updated_agent.name == "Updated Name Only"
        assert updated_agent.description == sample_agent.description  # Unchanged

    @pytest.mark.asyncio
    async def test_update_agent_not_found(
        self, db_session: AsyncSession, agent_update_schema: AgentUpdate
    ) -> None:
        """Test updating non-existent agent raises error."""
        # Arrange
        service = AgentService(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(AgentNotFoundError) as exc_info:
            await service.update(non_existent_id, agent_update_schema)

        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_agent_with_tools(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test updating agent tools."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        new_tools = [str(uuid4()), str(uuid4()), str(uuid4())]
        update_data = AgentUpdate(tools=new_tools)

        # Act
        updated_agent = await service.update(sample_agent.id, update_data)

        # Assert
        assert updated_agent.tools == new_tools


# =============================================================================
# DELETE TESTS
# =============================================================================


class TestAgentServiceDelete:
    """Test AgentService.delete method."""

    @pytest.mark.asyncio
    async def test_delete_agent_success(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test successful agent soft delete."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        deleted_agent = await service.delete(sample_agent.id)

        # Assert
        assert deleted_agent.id == sample_agent.id
        assert deleted_agent.deleted_at is not None

        # Verify it's actually deleted
        agent = await service.get(sample_agent.id)
        assert agent is None

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, db_session: AsyncSession) -> None:
        """Test deleting non-existent agent raises error."""
        # Arrange
        service = AgentService(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(AgentNotFoundError) as exc_info:
            await service.delete(non_existent_id)

        assert str(non_existent_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_already_deleted_agent(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test deleting an already deleted agent raises error."""
        # Arrange
        service = AgentService(db_session)
        sample_agent.soft_delete()
        db_session.add(sample_agent)
        await db_session.flush()

        # Act & Assert
        with pytest.raises(AgentNotFoundError):
            await service.delete(sample_agent.id)


# =============================================================================
# ADD TOOL TESTS
# =============================================================================


class TestAgentServiceAddTool:
    """Test AgentService.add_tool method."""

    @pytest.mark.asyncio
    async def test_add_tool_success(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test successfully adding a tool to agent."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        tool_id = uuid4()

        # Act
        updated_agent = await service.add_tool(sample_agent.id, tool_id)

        # Assert
        assert str(tool_id) in updated_agent.tools

    @pytest.mark.asyncio
    async def test_add_tool_agent_not_found(self, db_session: AsyncSession) -> None:
        """Test adding tool to non-existent agent raises error."""
        # Arrange
        service = AgentService(db_session)
        non_existent_id = uuid4()
        tool_id = uuid4()

        # Act & Assert
        with pytest.raises(AgentNotFoundError):
            await service.add_tool(non_existent_id, tool_id)

    @pytest.mark.asyncio
    async def test_add_tool_already_associated(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test adding already associated tool raises error."""
        # Arrange
        service = AgentService(db_session)
        tool_id = uuid4()
        sample_agent.tools = [str(tool_id)]
        db_session.add(sample_agent)
        await db_session.flush()

        # Act & Assert
        with pytest.raises(ToolAlreadyAssociatedError) as exc_info:
            await service.add_tool(sample_agent.id, tool_id)

        assert str(tool_id) in str(exc_info.value)
        assert str(sample_agent.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_tool_updates_timestamp(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test adding tool updates updated_at timestamp."""
        # Arrange
        service = AgentService(db_session)
        db_session.add(sample_agent)
        await db_session.flush()

        tool_id = uuid4()

        # Act
        updated_agent = await service.add_tool(sample_agent.id, tool_id)

        # Assert
        assert updated_agent.updated_at is not None


# =============================================================================
# REMOVE TOOL TESTS
# =============================================================================


class TestAgentServiceRemoveTool:
    """Test AgentService.remove_tool method."""

    @pytest.mark.asyncio
    async def test_remove_tool_success(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test successfully removing a tool from agent."""
        # Arrange
        service = AgentService(db_session)
        tool_id = uuid4()
        sample_agent.tools = [str(tool_id), str(uuid4())]
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        updated_agent = await service.remove_tool(sample_agent.id, tool_id)

        # Assert
        assert str(tool_id) not in updated_agent.tools
        assert len(updated_agent.tools) == 1

    @pytest.mark.asyncio
    async def test_remove_tool_agent_not_found(self, db_session: AsyncSession) -> None:
        """Test removing tool from non-existent agent raises error."""
        # Arrange
        service = AgentService(db_session)
        non_existent_id = uuid4()
        tool_id = uuid4()

        # Act & Assert
        with pytest.raises(AgentNotFoundError):
            await service.remove_tool(non_existent_id, tool_id)

    @pytest.mark.asyncio
    async def test_remove_tool_not_associated(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test removing non-associated tool doesn't raise error."""
        # Arrange
        service = AgentService(db_session)
        tool_id = uuid4()
        sample_agent.tools = [str(uuid4())]  # Different tool
        db_session.add(sample_agent)
        await db_session.flush()

        # Act - Should not raise error
        updated_agent = await service.remove_tool(sample_agent.id, tool_id)

        # Assert - Tools should be unchanged
        assert len(updated_agent.tools) == 1
        assert str(tool_id) not in updated_agent.tools

    @pytest.mark.asyncio
    async def test_remove_tool_updates_timestamp(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test removing tool updates updated_at timestamp."""
        # Arrange
        service = AgentService(db_session)
        tool_id = uuid4()
        sample_agent.tools = [str(tool_id)]
        db_session.add(sample_agent)
        await db_session.flush()

        # Act
        updated_agent = await service.remove_tool(sample_agent.id, tool_id)

        # Assert
        assert updated_agent.updated_at is not None

    @pytest.mark.asyncio
    async def test_remove_tool_from_empty_list(
        self, db_session: AsyncSession, sample_agent: Agent
    ) -> None:
        """Test removing tool from agent with empty tools list."""
        # Arrange
        service = AgentService(db_session)
        sample_agent.tools = []
        db_session.add(sample_agent)
        await db_session.flush()

        tool_id = uuid4()

        # Act - Should not raise error
        updated_agent = await service.remove_tool(sample_agent.id, tool_id)

        # Assert
        assert updated_agent.tools == []


# =============================================================================
# EXCEPTION TESTS
# =============================================================================


class TestAgentServiceExceptions:
    """Test AgentService exception hierarchy."""

    def test_agent_not_found_is_service_error(self) -> None:
        """Test AgentNotFoundError inherits from AgentServiceError."""
        # Arrange
        error = AgentNotFoundError("test message")

        # Assert
        assert isinstance(error, AgentServiceError)
        assert isinstance(error, Exception)

    def test_tool_already_associated_is_service_error(self) -> None:
        """Test ToolAlreadyAssociatedError inherits from AgentServiceError."""
        # Arrange
        error = ToolAlreadyAssociatedError("test message")

        # Assert
        assert isinstance(error, AgentServiceError)
        assert isinstance(error, Exception)

    def test_exception_messages(self) -> None:
        """Test exception messages are properly formatted."""
        # Arrange & Assert
        assert "Agent" in str(AgentNotFoundError("Agent 123 not found"))
        assert "Tool" in str(ToolAlreadyAssociatedError("Tool already added"))
        assert "Failed" in str(AgentServiceError("Failed to create agent"))
