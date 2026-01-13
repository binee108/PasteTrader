"""Tests for Agent model with many-to-many Tool relationship.

TAG: [SPEC-009] [DATABASE] [AGENT] [TDD]
REQ: REQ-003 - Agent Model Definition
REQ: REQ-004 - Model Provider Enum

TDD Cycle:
- RED: Write failing tests first
- GREEN: Implement model to pass tests
- REFACTOR: Improve code quality
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ModelProvider, ToolType

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# =============================================================================
# MOCK USER MODEL FOR FK REFERENCE
# =============================================================================

_test_user_defined = False


def get_mock_user_class():
    """Get or create the mock User model class for testing."""
    global _test_user_defined

    if not _test_user_defined:
        from app.models.base import Base, UUIDMixin

        class TestUserAgent(UUIDMixin, Base):
            """Mock User model for testing FK references."""

            __tablename__ = "test_users_agent"
            __table_args__: dict[str, bool] = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        _test_user_defined = True
        return TestUserAgent

    return None


# =============================================================================
# DB SESSION FIXTURE
# =============================================================================


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create async session for testing with tables created."""

    # Import models to register them with Base.metadata
    from app.models.agent import Agent
    from app.models.tool import Tool

    # Get mock User class to satisfy FK constraints
    get_mock_user_class()

    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# =============================================================================
# RED PHASE: FAILING TESTS
# =============================================================================


class TestAgentModelStructure:
    """Test Agent model class structure - RED PHASE."""

    def test_agent_has_model_config_attribute(self) -> None:
        """Agent should have model_config attribute (replaces model_provider/model_name)."""
        from app.models.agent import Agent

        assert hasattr(
            Agent, "model_config"
        ), "Agent should have model_config attribute"

    def test_agent_does_not_have_model_provider(self) -> None:
        """Agent should NOT have deprecated model_provider attribute."""
        from app.models.agent import Agent

        assert not hasattr(
            Agent, "model_provider"
        ), "Agent should not have model_provider (use model_config instead)"

    def test_agent_does_not_have_model_name(self) -> None:
        """Agent should NOT have deprecated model_name attribute."""
        from app.models.agent import Agent

        assert not hasattr(
            Agent, "model_name"
        ), "Agent should not have model_name (use model_config instead)"

    def test_agent_system_prompt_not_nullable(self) -> None:
        """Agent system_prompt should be NOT nullable."""
        from app.models.agent import Agent

        # Check that system_prompt column exists and is required
        assert hasattr(Agent, "system_prompt")

    def test_agent_name_unique_constraint(self) -> None:
        """Agent should have unique constraint on name."""
        from app.models.agent import Agent

        # SQLAlchemy 2.0: Check if there's a unique constraint on name
        # This is verified through database behavior tests
        assert hasattr(Agent, "name")

    def test_agent_has_tools_relationship(self) -> None:
        """Agent should have tools relationship (many-to-many with Tool)."""
        from app.models.agent import Agent

        assert hasattr(Agent, "tools"), "Agent should have tools relationship"


class TestAgentModelBehavior:
    """Test Agent model behavior with database operations - RED PHASE."""

    @pytest.mark.asyncio
    async def test_agent_creation_with_model_config(
        self, db_session: AsyncSession
    ) -> None:
        """Agent should be creatable with model_config JSONB field."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()
        agent = Agent(
            owner_id=owner_id,
            name="Test Agent",
            system_prompt="You are a helpful assistant.",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-opus-20240229",
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.id is not None
        assert agent.name == "Test Agent"
        assert agent.model_config["provider"] == "anthropic"
        assert agent.model_config["model"] == "claude-3-opus-20240229"
        assert agent.model_config["temperature"] == 0.7
        assert agent.model_config["max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_agent_system_prompt_required(self, db_session: AsyncSession) -> None:
        """Agent should require system_prompt (not nullable)."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()

        # This should fail because system_prompt is required
        with pytest.raises(Exception):  # SQLAlchemy will raise an integrity error
            agent = Agent(
                owner_id=owner_id,
                name="Agent Without Prompt",
                # system_prompt missing - should fail
                model_config={"provider": "anthropic", "model": "claude-3-opus"},
            )
            db_session.add(agent)
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_agent_model_config_default_empty_dict(
        self, db_session: AsyncSession
    ) -> None:
        """Agent model_config should default to empty dict."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()
        agent = Agent(
            owner_id=owner_id,
            name="Default Config Agent",
            system_prompt="You are helpful.",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.model_config == {}

    @pytest.mark.asyncio
    async def test_agent_name_unique_constraint(self, db_session: AsyncSession) -> None:
        """Agent name should be unique per user."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()

        # Create first agent
        agent1 = Agent(
            owner_id=owner_id,
            name="Unique Agent",
            system_prompt="First agent.",
            model_config={"provider": "anthropic", "model": "claude-3"},
        )
        db_session.add(agent1)
        await db_session.commit()

        # Try to create second agent with same name
        agent2 = Agent(
            owner_id=owner_id,
            name="Unique Agent",  # Same name
            system_prompt="Second agent.",
            model_config={"provider": "openai", "model": "gpt-4"},
        )
        db_session.add(agent2)

        # Should raise integrity error due to unique constraint
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_agent_many_to_many_with_tools(
        self, db_session: AsyncSession
    ) -> None:
        """Agent should have many-to-many relationship with Tool."""
        from app.models.agent import Agent
        from app.models.tool import Tool
        from sqlalchemy.orm import selectinload

        owner_id = uuid.uuid4()

        # Create tools
        tool1 = Tool(
            owner_id=owner_id,
            name="HTTP Tool",
            tool_type=ToolType.HTTP,
            config={"url": "https://api.example.com"},
        )
        tool2 = Tool(
            owner_id=owner_id,
            name="Python Tool",
            tool_type=ToolType.PYTHON,
            config={"module": "tools.custom"},
        )
        db_session.add(tool1)
        db_session.add(tool2)
        await db_session.commit()

        # Create agent
        agent = Agent(
            owner_id=owner_id,
            name="Agent with Tools",
            system_prompt="You can use tools.",
            model_config={"provider": "anthropic", "model": "claude-3"},
        )
        agent.tools.append(tool1)
        agent.tools.append(tool2)
        db_session.add(agent)
        await db_session.commit()

        # Verify relationship with eager load
        result = await db_session.execute(
            select(Agent).where(Agent.id == agent.id).options(selectinload(Agent.tools))
        )
        agent = result.scalar_one()

        assert len(agent.tools) == 2
        assert agent.tools[0].name == "HTTP Tool"
        assert agent.tools[1].name == "Python Tool"

    @pytest.mark.asyncio
    async def test_agent_tools_relationship_loading(
        self, db_session: AsyncSession
    ) -> None:
        """Agent tools should be loadable from database."""
        from app.models.agent import Agent
        from app.models.tool import Tool
        from sqlalchemy.orm import selectinload

        owner_id = uuid.uuid4()

        # Create tool and agent
        tool = Tool(
            owner_id=owner_id,
            name="Test Tool",
            tool_type=ToolType.BUILTIN,
            config={"function": "test"},
        )
        agent = Agent(
            owner_id=owner_id,
            name="Test Agent",
            system_prompt="Test prompt.",
            model_config={"provider": "anthropic", "model": "claude-3"},
        )
        agent.tools.append(tool)

        db_session.add(agent)
        await db_session.commit()

        # Reload with eager load
        result = await db_session.execute(
            select(Agent).where(Agent.id == agent.id).options(selectinload(Agent.tools))
        )
        agent = result.scalar_one()

        # Load tools relationship
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "Test Tool"

    @pytest.mark.asyncio
    async def test_agent_cascade_delete_with_tools(
        self, db_session: AsyncSession
    ) -> None:
        """Deleting an agent should not delete associated tools (no cascade)."""
        from app.models.agent import Agent
        from app.models.tool import Tool

        owner_id = uuid.uuid4()

        # Create tool and agent
        tool = Tool(
            owner_id=owner_id,
            name="Persistent Tool",
            tool_type=ToolType.HTTP,
            config={"url": "https://example.com"},
        )
        agent = Agent(
            owner_id=owner_id,
            name="Temporary Agent",
            system_prompt="This agent will be deleted.",
            model_config={"provider": "anthropic", "model": "claude-3"},
        )
        agent.tools.append(tool)

        db_session.add(agent)
        await db_session.commit()

        agent_id = agent.id
        tool_id = tool.id

        # Delete agent
        await db_session.delete(agent)
        await db_session.commit()

        # Verify agent is deleted
        result = await db_session.execute(select(Agent).where(Agent.id == agent_id))
        assert result.scalar_one_or_none() is None

        # Verify tool still exists (no cascade)
        result = await db_session.execute(select(Tool).where(Tool.id == tool_id))
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_agent_repr(self, db_session: AsyncSession) -> None:
        """Agent __repr__ should include name and model provider."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Test Agent",
            system_prompt="Test.",
            model_config={"provider": "anthropic", "model": "claude-3-opus"},
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        repr_str = repr(agent)
        assert "Test Agent" in repr_str
        assert "anthropic" in repr_str
