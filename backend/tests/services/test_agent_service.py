"""Service layer tests for AgentService.

TAG: [SPEC-007] [TESTS] [SERVICE] [AGENT]
REQ: REQ-001 - AgentService CRUD Operations
REQ: REQ-002 - Agent Tool Association
REQ: REQ-003 - Agent Filtering and Search
REQ: REQ-004 - Soft Delete Behavior
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.agent import Agent
from app.models.enums import ModelProvider
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.agent_service import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentService,
    AgentServiceError,
    ToolAlreadyAssociatedError,
)


# =============================================================================
# AgentService CRUD Tests
# =============================================================================


class TestAgentServiceCreate:
    """Test AgentService.create() method."""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, db_session):
        """Test successful agent creation."""
        owner_id = uuid4()
        data = AgentCreate(
            name="Test Agent",
            description="A test agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            system_prompt="You are helpful.",
            config={"temperature": 0.7},
            tools=[],
            memory_config=None,
            is_active=True,
            is_public=False,
        )

        service = AgentService(db_session)
        agent = await service.create(owner_id, data)

        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.model_provider == ModelProvider.ANTHROPIC
        assert agent.is_active is True
        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_create_agent_database_failure(self, db_session, monkeypatch):
        """Test agent creation with database failure."""
        owner_id = uuid4()
        data = AgentCreate(
            name="Test Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
        )

        service = AgentService(db_session)

        # Mock flush to raise database error
        async def mock_flush():
            raise SQLAlchemyError("Database connection lost")

        monkeypatch.setattr(db_session, "flush", mock_flush)

        with pytest.raises(AgentServiceError, match="Failed to create agent"):
            await service.create(owner_id, data)


class TestAgentServiceGet:
    """Test AgentService.get() method."""

    @pytest.mark.asyncio
    async def test_get_agent_found(self, db_session, agent_factory):
        """Test getting an existing agent."""
        agent = agent_factory(name="Test Agent")
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        result = await service.get(agent.id)

        assert result is not None
        assert result.id == agent.id
        assert result.name == "Test Agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, db_session):
        """Test getting a non-existent agent."""
        service = AgentService(db_session)
        result = await service.get(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_agent_include_deleted_true(self, db_session, agent_factory):
        """Test getting a deleted agent with include_deleted=True."""
        agent = agent_factory(name="Deleted Agent")
        agent.soft_delete()
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)

        # Without include_deleted, should return None
        result = await service.get(agent.id, include_deleted=False)
        assert result is None

        # With include_deleted=True, should return the agent
        result = await service.get(agent.id, include_deleted=True)
        assert result is not None
        assert result.id == agent.id

    @pytest.mark.asyncio
    async def test_get_agent_include_deleted_false(self, db_session, agent_factory):
        """Test that deleted agents are excluded by default."""
        agent = agent_factory(name="Active Agent")
        db_session.add(agent)
        await db_session.flush()

        # Create deleted agent
        deleted_agent = agent_factory(name="Deleted Agent")
        deleted_agent.soft_delete()
        db_session.add(deleted_agent)
        await db_session.flush()

        service = AgentService(db_session)

        # Should only return active agent
        result = await service.get(agent.id, include_deleted=False)
        assert result is not None
        assert result.id == agent.id

        # Deleted agent should return None
        result = await service.get(deleted_agent.id, include_deleted=False)
        assert result is None


class TestAgentServiceList:
    """Test AgentService.list() method."""

    @pytest.mark.asyncio
    async def test_list_agents_no_filters(self, db_session, agent_factory):
        """Test listing agents without filters."""
        owner_id = uuid4()
        for i in range(3):
            agent = agent_factory(owner_id=owner_id, name=f"Agent {i}")
            db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        results = await service.list(owner_id)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_agents_with_model_provider_filter(
        self, db_session, agent_factory
    ):
        """Test listing agents filtered by model provider."""
        owner_id = uuid4()
        anthropic_agent = agent_factory(
            owner_id=owner_id, model_provider=ModelProvider.ANTHROPIC
        )
        openai_agent = agent_factory(
            owner_id=owner_id, model_provider=ModelProvider.OPENAI
        )
        db_session.add_all([anthropic_agent, openai_agent])
        await db_session.flush()

        service = AgentService(db_session)
        results = await service.list(owner_id, model_provider="anthropic")

        assert len(results) == 1
        assert results[0].model_provider == ModelProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_list_agents_with_is_active_filter(self, db_session, agent_factory):
        """Test listing agents filtered by active status."""
        owner_id = uuid4()
        active_agent = agent_factory(owner_id=owner_id, is_active=True)
        inactive_agent = agent_factory(owner_id=owner_id, is_active=False)
        db_session.add_all([active_agent, inactive_agent])
        await db_session.flush()

        service = AgentService(db_session)

        # Filter for active agents
        results = await service.list(owner_id, is_active=True)
        assert len(results) == 1
        assert results[0].is_active is True

        # Filter for inactive agents
        results = await service.list(owner_id, is_active=False)
        assert len(results) == 1
        assert results[0].is_active is False

    @pytest.mark.asyncio
    async def test_list_agents_with_is_public_filter(self, db_session, agent_factory):
        """Test listing agents filtered by public status."""
        owner_id = uuid4()
        public_agent = agent_factory(owner_id=owner_id, is_public=True)
        private_agent = agent_factory(owner_id=owner_id, is_public=False)
        db_session.add_all([public_agent, private_agent])
        await db_session.flush()

        service = AgentService(db_session)
        results = await service.list(owner_id, is_public=True)

        assert len(results) == 1
        assert results[0].is_public is True

    @pytest.mark.asyncio
    async def test_list_agents_combined_filters(self, db_session, agent_factory):
        """Test listing agents with multiple filters."""
        owner_id = uuid4()
        agent1 = agent_factory(
            owner_id=owner_id,
            model_provider=ModelProvider.ANTHROPIC,
            is_active=True,
            is_public=True,
        )
        agent2 = agent_factory(
            owner_id=owner_id,
            model_provider=ModelProvider.OPENAI,
            is_active=True,
            is_public=True,
        )
        agent3 = agent_factory(
            owner_id=owner_id,
            model_provider=ModelProvider.ANTHROPIC,
            is_active=False,
            is_public=True,
        )
        db_session.add_all([agent1, agent2, agent3])
        await db_session.flush()

        service = AgentService(db_session)
        results = await service.list(
            owner_id, model_provider="anthropic", is_active=True, is_public=True
        )

        assert len(results) == 1
        assert results[0].model_provider == ModelProvider.ANTHROPIC
        assert results[0].is_active is True

    @pytest.mark.asyncio
    async def test_list_agents_include_deleted(self, db_session, agent_factory):
        """Test listing agents with include_deleted flag."""
        owner_id = uuid4()
        active_agent = agent_factory(owner_id=owner_id, name="Active Agent")
        deleted_agent = agent_factory(owner_id=owner_id, name="Deleted Agent")
        deleted_agent.soft_delete()
        db_session.add_all([active_agent, deleted_agent])
        await db_session.flush()

        service = AgentService(db_session)

        # Without include_deleted, should only return active
        results = await service.list(owner_id, include_deleted=False)
        assert len(results) == 1
        assert results[0].name == "Active Agent"

        # With include_deleted=True, should return both
        results = await service.list(owner_id, include_deleted=True, is_active=None)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_agents_pagination(self, db_session, agent_factory):
        """Test agent listing with pagination."""
        owner_id = uuid4()
        for i in range(5):
            agent = agent_factory(owner_id=owner_id, name=f"Agent {i}")
            db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        results = await service.list(owner_id, skip=2, limit=2)

        assert len(results) == 2


class TestAgentServiceCount:
    """Test AgentService.count() method."""

    @pytest.mark.asyncio
    async def test_count_agents_all(self, db_session, agent_factory):
        """Test counting all agents."""
        owner_id = uuid4()
        for i in range(3):
            agent = agent_factory(owner_id=owner_id)
            db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        count = await service.count(owner_id)

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_agents_with_filters(self, db_session, agent_factory):
        """Test counting agents with filters."""
        owner_id = uuid4()
        anthropic_agent = agent_factory(
            owner_id=owner_id, model_provider=ModelProvider.ANTHROPIC
        )
        openai_agent = agent_factory(
            owner_id=owner_id, model_provider=ModelProvider.OPENAI
        )
        db_session.add_all([anthropic_agent, openai_agent])
        await db_session.flush()

        service = AgentService(db_session)
        count = await service.count(owner_id, model_provider="anthropic")

        assert count == 1

    @pytest.mark.asyncio
    async def test_count_agents_returns_zero(self, db_session):
        """Test count returns zero when no agents match."""
        owner_id = uuid4()
        service = AgentService(db_session)
        count = await service.count(owner_id)

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_agents_include_deleted(self, db_session, agent_factory):
        """Test counting with include_deleted flag."""
        owner_id = uuid4()
        active_agent = agent_factory(owner_id=owner_id)
        deleted_agent = agent_factory(owner_id=owner_id)
        deleted_agent.soft_delete()
        db_session.add_all([active_agent, deleted_agent])
        await db_session.flush()

        service = AgentService(db_session)

        # Without include_deleted
        count = await service.count(owner_id, include_deleted=False)
        assert count == 1

        # With include_deleted
        count = await service.count(owner_id, include_deleted=True, is_active=None)
        assert count == 2


class TestAgentServiceUpdate:
    """Test AgentService.update() method."""

    @pytest.mark.asyncio
    async def test_update_agent_success(self, db_session, agent_factory):
        """Test successful agent update."""
        agent = agent_factory(name="Original Name")
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        update_data = AgentUpdate(name="Updated Name", is_active=False)

        updated = await service.update(agent.id, update_data)

        assert updated.name == "Updated Name"
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_update_agent_partial_fields(self, db_session, agent_factory):
        """Test updating agent with partial fields."""
        agent = agent_factory(
            name="Test",
            description="Original",
            is_active=True,
            is_public=False,
        )
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        update_data = AgentUpdate(description="Updated Description")

        updated = await service.update(agent.id, update_data)

        assert updated.description == "Updated Description"
        assert updated.name == "Test"  # Unchanged
        assert updated.is_active is True  # Unchanged

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, db_session):
        """Test updating non-existent agent raises error."""
        service = AgentService(db_session)
        update_data = AgentUpdate(name="Updated")

        with pytest.raises(AgentNotFoundError):
            await service.update(uuid4(), update_data)

    @pytest.mark.asyncio
    async def test_update_agent_database_failure(
        self, db_session, agent_factory, monkeypatch
    ):
        """Test update with database failure."""
        agent = agent_factory()
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        update_data = AgentUpdate(name="Updated")

        # Mock flush to raise database error
        async def mock_flush():
            raise SQLAlchemyError("Database connection lost")

        monkeypatch.setattr(db_session, "flush", mock_flush)

        with pytest.raises(AgentServiceError, match="Failed to update agent"):
            await service.update(agent.id, update_data)


class TestAgentServiceDelete:
    """Test AgentService.delete() method."""

    @pytest.mark.asyncio
    async def test_delete_agent_success(self, db_session, agent_factory):
        """Test successful agent soft delete."""
        agent = agent_factory(name="To Delete")
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        deleted = await service.delete(agent.id)

        assert deleted.deleted_at is not None
        assert deleted.is_active is False

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, db_session):
        """Test deleting non-existent agent raises error."""
        service = AgentService(db_session)

        with pytest.raises(AgentNotFoundError):
            await service.delete(uuid4())

    @pytest.mark.asyncio
    async def test_delete_agent_sets_deleted_at(self, db_session, agent_factory):
        """Test that delete sets deleted_at timestamp."""
        agent = agent_factory()
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        deleted = await service.delete(agent.id)

        assert deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_agent_sets_is_active_false(self, db_session, agent_factory):
        """Test that delete sets is_active to False."""
        agent = agent_factory(is_active=True)
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        deleted = await service.delete(agent.id)

        assert deleted.is_active is False


class TestAgentServiceAddTool:
    """Test AgentService.add_tool() method."""

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_success(self, db_session, agent_factory):
        """Test successfully adding a tool to an agent."""
        agent = agent_factory(tools=[])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        tool_id = uuid4()

        updated = await service.add_tool(agent.id, tool_id)

        assert str(tool_id) in updated.tools
        assert len(updated.tools) == 1

    @pytest.mark.asyncio
    async def test_add_tool_to_agent_not_found(self, db_session):
        """Test adding tool to non-existent agent."""
        service = AgentService(db_session)

        with pytest.raises(AgentNotFoundError):
            await service.add_tool(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_add_tool_already_associated(self, db_session, agent_factory):
        """Test adding duplicate tool raises error."""
        tool_id = uuid4()
        agent = agent_factory(tools=[str(tool_id)])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)

        with pytest.raises(ToolAlreadyAssociatedError):
            await service.add_tool(agent.id, tool_id)

    @pytest.mark.asyncio
    async def test_add_tool_updates_modified_flag(self, db_session, agent_factory):
        """Test that add_tool flags the tools field as modified."""
        agent = agent_factory(tools=[])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        tool_id = uuid4()

        updated = await service.add_tool(agent.id, tool_id)

        # Verify the tool was added and field was flagged
        assert str(tool_id) in updated.tools
        assert updated.updated_at is not None


class TestAgentServiceRemoveTool:
    """Test AgentService.remove_tool() method."""

    @pytest.mark.asyncio
    async def test_remove_tool_from_agent_success(self, db_session, agent_factory):
        """Test successfully removing a tool from an agent."""
        tool_id = uuid4()
        agent = agent_factory(tools=[str(tool_id)])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        updated = await service.remove_tool(agent.id, tool_id)

        assert str(tool_id) not in updated.tools
        assert len(updated.tools) == 0

    @pytest.mark.asyncio
    async def test_remove_tool_from_agent_not_found(self, db_session):
        """Test removing tool from non-existent agent."""
        service = AgentService(db_session)

        with pytest.raises(AgentNotFoundError):
            await service.remove_tool(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_remove_tool_not_in_agent_tools_list(self, db_session, agent_factory):
        """Test removing tool that isn't in agent's tools list."""
        agent = agent_factory(tools=[])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)

        # Should not raise error, just no-op
        updated = await service.remove_tool(agent.id, uuid4())
        assert len(updated.tools) == 0

    @pytest.mark.asyncio
    async def test_remove_tool_updates_modified_flag(self, db_session, agent_factory):
        """Test that remove_tool flags the tools field as modified."""
        tool_id = uuid4()
        agent = agent_factory(tools=[str(tool_id)])
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        updated = await service.remove_tool(agent.id, tool_id)

        # Verify the tool was removed and field was flagged
        assert str(tool_id) not in updated.tools
        assert updated.updated_at is not None

from app.models.tool import Tool


class TestAgentServiceTestExecute:
    """Test AgentService.test_execute() method."""

    @pytest.mark.asyncio
    async def test_agent_execute_success(self, db_session, agent_factory):
        """Test successful agent execution."""
        agent = agent_factory(is_active=True)
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        input_data = {"task": "test task"}

        result = await service.test_execute(agent.id, input_data)

        assert result["success"] is True
        assert "execution_time_ms" in result
        assert result["output"]["input"] == input_data

    @pytest.mark.asyncio
    async def test_agent_execute_not_found(self, db_session):
        """Test agent execution with non-existent agent."""
        service = AgentService(db_session)

        with pytest.raises(AgentNotFoundError):
            await service.test_execute(uuid4(), {})

    @pytest.mark.asyncio
    async def test_agent_execute_inactive_agent(self, db_session, agent_factory):
        """Test agent execution on inactive agent raises error."""
        agent = agent_factory(is_active=False)
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)

        with pytest.raises(AgentExecutionError, match="not active"):
            await service.test_execute(agent.id, {})

    @pytest.mark.asyncio
    async def test_agent_execute_returns_execution_time(self, db_session, agent_factory):
        """Test that agent execution returns execution time."""
        agent = agent_factory(is_active=True)
        db_session.add(agent)
        await db_session.flush()

        service = AgentService(db_session)
        result = await service.test_execute(agent.id, {})

        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], float)
        assert result["execution_time_ms"] >= 0


class TestAgentServiceListDefaultActiveFilter:
    """Test AgentService.list() default is_active=True behavior."""

    @pytest.mark.asyncio
    async def test_list_returns_only_active_by_default(
        self, db_session, agent_factory
    ):
        """Test that list() returns only active agents by default."""
        owner_id = uuid4()
        active_agent = agent_factory(owner_id=owner_id, is_active=True)
        inactive_agent = agent_factory(owner_id=owner_id, is_active=False)
        db_session.add_all([active_agent, inactive_agent])
        await db_session.flush()

        service = AgentService(db_session)

        # Default behavior should return only active agents
        results = await service.list(owner_id)
        assert len(results) == 1
        assert results[0].is_active is True

        # Explicitly request inactive agents
        results = await service.list(owner_id, is_active=False)
        assert len(results) == 1
        assert results[0].is_active is False

        # Request all agents (active and inactive)
        results = await service.list(owner_id, is_active=None)
        assert len(results) == 2
