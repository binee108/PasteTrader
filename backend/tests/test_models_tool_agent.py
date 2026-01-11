"""Tests for Tool and Agent models.

TAG: [SPEC-004] [DATABASE] [TOOL] [AGENT]
REQ: REQ-001 - Tool Model Definition
REQ: REQ-003 - Agent Model Definition
REQ: REQ-002 - Tool Type Enum Update
REQ: REQ-004 - Model Provider Enum
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import String, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ModelProvider, ToolType

# Test will use SQLite for unit testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestToolTypeEnum:
    """Test ToolType enum values."""

    def test_tooltype_http_exists(self) -> None:
        """ToolType should have HTTP value."""
        assert ToolType.HTTP.value == "http"

    def test_tooltype_mcp_exists(self) -> None:
        """ToolType should have MCP value."""
        assert ToolType.MCP.value == "mcp"

    def test_tooltype_python_exists(self) -> None:
        """ToolType should have PYTHON value."""
        assert ToolType.PYTHON.value == "python"

    def test_tooltype_shell_exists(self) -> None:
        """ToolType should have SHELL value."""
        assert ToolType.SHELL.value == "shell"

    def test_tooltype_builtin_exists(self) -> None:
        """ToolType should have BUILTIN value."""
        assert ToolType.BUILTIN.value == "builtin"


class TestModelProviderEnum:
    """Test ModelProvider enum values."""

    def test_modelprovider_anthropic_exists(self) -> None:
        """ModelProvider should have ANTHROPIC value."""
        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_modelprovider_openai_exists(self) -> None:
        """ModelProvider should have OPENAI value."""
        assert ModelProvider.OPENAI.value == "openai"

    def test_modelprovider_glm_exists(self) -> None:
        """ModelProvider should have GLM value."""
        assert ModelProvider.GLM.value == "glm"


class TestToolModelStructure:
    """Test Tool model class structure."""

    def test_tool_class_exists(self) -> None:
        """Tool class should exist in models.tool module."""
        from app.models.tool import Tool

        assert Tool is not None

    def test_tool_has_tablename(self) -> None:
        """Tool should have __tablename__ = 'tools'."""
        from app.models.tool import Tool

        assert Tool.__tablename__ == "tools"

    def test_tool_has_id_attribute(self) -> None:
        """Tool should have id attribute (from UUIDMixin)."""
        from app.models.tool import Tool

        assert hasattr(Tool, "id")

    def test_tool_has_owner_id_attribute(self) -> None:
        """Tool should have owner_id attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "owner_id")

    def test_tool_has_name_attribute(self) -> None:
        """Tool should have name attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "name")

    def test_tool_has_description_attribute(self) -> None:
        """Tool should have description attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "description")

    def test_tool_has_tool_type_attribute(self) -> None:
        """Tool should have tool_type attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "tool_type")

    def test_tool_has_config_attribute(self) -> None:
        """Tool should have config attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "config")

    def test_tool_has_input_schema_attribute(self) -> None:
        """Tool should have input_schema attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "input_schema")

    def test_tool_has_output_schema_attribute(self) -> None:
        """Tool should have output_schema attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "output_schema")

    def test_tool_has_auth_config_attribute(self) -> None:
        """Tool should have auth_config attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "auth_config")

    def test_tool_has_rate_limit_attribute(self) -> None:
        """Tool should have rate_limit attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "rate_limit")

    def test_tool_has_is_active_attribute(self) -> None:
        """Tool should have is_active attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "is_active")

    def test_tool_has_is_public_attribute(self) -> None:
        """Tool should have is_public attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "is_public")

    def test_tool_has_timestamp_attributes(self) -> None:
        """Tool should have created_at and updated_at attributes."""
        from app.models.tool import Tool

        assert hasattr(Tool, "created_at")
        assert hasattr(Tool, "updated_at")

    def test_tool_has_soft_delete_attribute(self) -> None:
        """Tool should have deleted_at attribute."""
        from app.models.tool import Tool

        assert hasattr(Tool, "deleted_at")


class TestAgentModelStructure:
    """Test Agent model class structure."""

    def test_agent_class_exists(self) -> None:
        """Agent class should exist in models.agent module."""
        from app.models.agent import Agent

        assert Agent is not None

    def test_agent_has_tablename(self) -> None:
        """Agent should have __tablename__ = 'agents'."""
        from app.models.agent import Agent

        assert Agent.__tablename__ == "agents"

    def test_agent_has_id_attribute(self) -> None:
        """Agent should have id attribute (from UUIDMixin)."""
        from app.models.agent import Agent

        assert hasattr(Agent, "id")

    def test_agent_has_owner_id_attribute(self) -> None:
        """Agent should have owner_id attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "owner_id")

    def test_agent_has_name_attribute(self) -> None:
        """Agent should have name attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "name")

    def test_agent_has_description_attribute(self) -> None:
        """Agent should have description attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "description")

    def test_agent_has_model_provider_attribute(self) -> None:
        """Agent should have model_provider attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "model_provider")

    def test_agent_has_model_name_attribute(self) -> None:
        """Agent should have model_name attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "model_name")

    def test_agent_has_system_prompt_attribute(self) -> None:
        """Agent should have system_prompt attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "system_prompt")

    def test_agent_has_config_attribute(self) -> None:
        """Agent should have config attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "config")

    def test_agent_has_tools_attribute(self) -> None:
        """Agent should have tools attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "tools")

    def test_agent_has_memory_config_attribute(self) -> None:
        """Agent should have memory_config attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "memory_config")

    def test_agent_has_is_active_attribute(self) -> None:
        """Agent should have is_active attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "is_active")

    def test_agent_has_is_public_attribute(self) -> None:
        """Agent should have is_public attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "is_public")

    def test_agent_has_timestamp_attributes(self) -> None:
        """Agent should have created_at and updated_at attributes."""
        from app.models.agent import Agent

        assert hasattr(Agent, "created_at")
        assert hasattr(Agent, "updated_at")

    def test_agent_has_soft_delete_attribute(self) -> None:
        """Agent should have deleted_at attribute."""
        from app.models.agent import Agent

        assert hasattr(Agent, "deleted_at")


# Create a mock User model for testing FK references
_test_models_defined = False
_MockUserClass = None


def get_mock_user_class():
    """Get or create the mock User model class for testing."""
    global _test_models_defined, _MockUserClass

    if not _test_models_defined:
        from app.models.base import Base, UUIDMixin

        class User(UUIDMixin, Base):
            """Mock User model for testing FK references."""

            __tablename__ = "users"
            __table_args__ = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        _MockUserClass = User
        _test_models_defined = True

    return _MockUserClass


# Database behavior tests require session fixture
@pytest_asyncio.fixture
async def db_session():
    """Create async session for testing with tables created."""
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


class TestToolModelBehavior:
    """Test Tool model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_tool_creation_with_required_fields(self, db_session) -> None:
        """Tool should be creatable with required fields."""
        from app.models.tool import Tool

        owner_id = uuid.uuid4()
        tool = Tool(
            owner_id=owner_id,
            name="Test HTTP Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.id is not None
        assert tool.owner_id == owner_id
        assert tool.name == "Test HTTP Tool"
        assert tool.tool_type == ToolType.HTTP

    @pytest.mark.asyncio
    async def test_tool_creation_with_all_fields(self, db_session) -> None:
        """Tool should be creatable with all fields."""
        from app.models.tool import Tool

        owner_id = uuid.uuid4()
        tool = Tool(
            owner_id=owner_id,
            name="Complete Tool",
            description="A complete tool with all fields",
            tool_type=ToolType.MCP,
            config={"server_name": "mcp-server"},
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "string"},
            auth_config={"api_key": "encrypted_key"},
            rate_limit={"requests_per_minute": 60},
            is_active=True,
            is_public=True,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.description == "A complete tool with all fields"
        assert tool.config == {"server_name": "mcp-server"}
        assert tool.input_schema == {"type": "object", "properties": {}}
        assert tool.output_schema == {"type": "string"}
        assert tool.auth_config == {"api_key": "encrypted_key"}
        assert tool.rate_limit == {"requests_per_minute": 60}
        assert tool.is_active is True
        assert tool.is_public is True

    @pytest.mark.asyncio
    async def test_tool_http_type(self, db_session) -> None:
        """Tool with HTTP type should work correctly."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="HTTP API Tool",
            tool_type=ToolType.HTTP,
            config={"base_url": "https://api.example.com", "method": "POST"},
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(tool.tool_type) == "http"

    @pytest.mark.asyncio
    async def test_tool_mcp_type(self, db_session) -> None:
        """Tool with MCP type should work correctly."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="MCP Tool",
            tool_type=ToolType.MCP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(tool.tool_type) == "mcp"

    @pytest.mark.asyncio
    async def test_tool_python_type(self, db_session) -> None:
        """Tool with PYTHON type should work correctly."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Python Function Tool",
            tool_type=ToolType.PYTHON,
            config={"module": "app.tools.custom", "function": "execute"},
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(tool.tool_type) == "python"

    @pytest.mark.asyncio
    async def test_tool_shell_type(self, db_session) -> None:
        """Tool with SHELL type should work correctly."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Shell Command Tool",
            tool_type=ToolType.SHELL,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(tool.tool_type) == "shell"

    @pytest.mark.asyncio
    async def test_tool_builtin_type(self, db_session) -> None:
        """Tool with BUILTIN type should work correctly."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Builtin Tool",
            tool_type=ToolType.BUILTIN,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(tool.tool_type) == "builtin"

    @pytest.mark.asyncio
    async def test_tool_is_active_default(self, db_session) -> None:
        """Tool is_active should default to True."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Default Active Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.is_active is True

    @pytest.mark.asyncio
    async def test_tool_is_public_default(self, db_session) -> None:
        """Tool is_public should default to False."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Default Private Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.is_public is False

    @pytest.mark.asyncio
    async def test_tool_config_default(self, db_session) -> None:
        """Tool config should default to empty dict."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Default Config Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.config == {}

    @pytest.mark.asyncio
    async def test_tool_input_schema_default(self, db_session) -> None:
        """Tool input_schema should default to empty dict."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Default Schema Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.input_schema == {}

    @pytest.mark.asyncio
    async def test_tool_soft_delete(self, db_session) -> None:
        """Tool should support soft delete."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Deletable Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.deleted_at is None
        assert tool.is_deleted is False

        tool.soft_delete()
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.deleted_at is not None
        assert tool.is_deleted is True

    @pytest.mark.asyncio
    async def test_tool_timestamps(self, db_session) -> None:
        """Tool should have auto-generated timestamps."""
        from app.models.tool import Tool

        tool = Tool(
            owner_id=uuid.uuid4(),
            name="Timestamped Tool",
            tool_type=ToolType.HTTP,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.created_at is not None
        assert tool.updated_at is not None


class TestAgentModelBehavior:
    """Test Agent model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_agent_creation_with_required_fields(self, db_session) -> None:
        """Agent should be creatable with required fields."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()
        agent = Agent(
            owner_id=owner_id,
            name="Test Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.id is not None
        assert agent.owner_id == owner_id
        assert agent.name == "Test Agent"
        assert agent.model_provider == ModelProvider.ANTHROPIC
        assert agent.model_name == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_agent_creation_with_all_fields(self, db_session) -> None:
        """Agent should be creatable with all fields."""
        from app.models.agent import Agent

        owner_id = uuid.uuid4()
        tool_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        agent = Agent(
            owner_id=owner_id,
            name="Complete Agent",
            description="A complete agent with all fields",
            model_provider=ModelProvider.OPENAI,
            model_name="gpt-4-turbo",
            system_prompt="You are a helpful assistant.",
            config={"temperature": 0.7, "max_tokens": 4096},
            tools=tool_ids,
            memory_config={"type": "sliding_window", "max_messages": 20},
            is_active=True,
            is_public=True,
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.description == "A complete agent with all fields"
        assert agent.system_prompt == "You are a helpful assistant."
        assert agent.config == {"temperature": 0.7, "max_tokens": 4096}
        assert agent.tools == tool_ids
        assert agent.memory_config == {"type": "sliding_window", "max_messages": 20}
        assert agent.is_active is True
        assert agent.is_public is True

    @pytest.mark.asyncio
    async def test_agent_anthropic_provider(self, db_session) -> None:
        """Agent with ANTHROPIC provider should work correctly."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Anthropic Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-sonnet-20240229",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(agent.model_provider) == "anthropic"

    @pytest.mark.asyncio
    async def test_agent_openai_provider(self, db_session) -> None:
        """Agent with OPENAI provider should work correctly."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="OpenAI Agent",
            model_provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(agent.model_provider) == "openai"

    @pytest.mark.asyncio
    async def test_agent_glm_provider(self, db_session) -> None:
        """Agent with GLM provider should work correctly."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="GLM Agent",
            model_provider=ModelProvider.GLM,
            model_name="glm-4",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # SQLite stores as string, PostgreSQL preserves enum
        assert str(agent.model_provider) == "glm"

    @pytest.mark.asyncio
    async def test_agent_is_active_default(self, db_session) -> None:
        """Agent is_active should default to True."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Default Active Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.is_active is True

    @pytest.mark.asyncio
    async def test_agent_is_public_default(self, db_session) -> None:
        """Agent is_public should default to False."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Default Private Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.is_public is False

    @pytest.mark.asyncio
    async def test_agent_config_default(self, db_session) -> None:
        """Agent config should default to empty dict."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Default Config Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.config == {}

    @pytest.mark.asyncio
    async def test_agent_tools_default(self, db_session) -> None:
        """Agent tools should default to empty list."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Default Tools Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.tools == []

    @pytest.mark.asyncio
    async def test_agent_soft_delete(self, db_session) -> None:
        """Agent should support soft delete."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Deletable Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.deleted_at is None
        assert agent.is_deleted is False

        agent.soft_delete()
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.deleted_at is not None
        assert agent.is_deleted is True

    @pytest.mark.asyncio
    async def test_agent_timestamps(self, db_session) -> None:
        """Agent should have auto-generated timestamps."""
        from app.models.agent import Agent

        agent = Agent(
            owner_id=uuid.uuid4(),
            name="Timestamped Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        assert agent.created_at is not None
        assert agent.updated_at is not None
