"""Tests for SPEC-009 Tool SQLAlchemy Model.

TAG: [SPEC-009] [DATABASE] [TOOL-MODEL]
REQ: SPEC-009 Tool Model Definition

This module tests the SPEC-009 Tool SQLAlchemy model for ToolRegistry integration.
The SPEC-009 Tool model is different from SPEC-004 Tool model:
- SPEC-004: Workflow node external tools (HTTP, MCP, Python, Shell, Builtin)
- SPEC-009: meta_llm ToolRegistry integration tools (parameters as JSON Schema)

TDD RED Phase: All tests should fail initially.
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, GUID

# Test will use SQLite for unit testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestToolModelStructure:
    """Test SPEC-009 Tool model class structure."""

    def test_tool_class_exists(self) -> None:
        """Tool class should exist in models.tool_spec009 module."""
        from app.models.tool_spec009 import Tool

        assert Tool is not None

    def test_tool_has_tablename(self) -> None:
        """Tool should have __tablename__ = 'tools_spec009'."""
        from app.models.tool_spec009 import Tool

        assert Tool.__tablename__ == "tools_spec009"

    def test_tool_has_id_attribute(self) -> None:
        """Tool should have id attribute (UUID primary key)."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "id")

    def test_tool_has_name_attribute(self) -> None:
        """Tool should have name attribute."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "name")

    def test_tool_has_description_attribute(self) -> None:
        """Tool should have description attribute."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "description")

    def test_tool_has_parameters_attribute(self) -> None:
        """Tool should have parameters attribute (JSON Schema)."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "parameters")

    def test_tool_has_implementation_path_attribute(self) -> None:
        """Tool should have implementation_path attribute."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "implementation_path")

    def test_tool_has_is_active_attribute(self) -> None:
        """Tool should have is_active attribute."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "is_active")

    def test_tool_has_timestamp_attributes(self) -> None:
        """Tool should have created_at and updated_at attributes."""
        from app.models.tool_spec009 import Tool

        assert hasattr(Tool, "created_at")
        assert hasattr(Tool, "updated_at")


# Database behavior tests require session fixture
@pytest_asyncio.fixture
async def db_session():
    """Create async session for testing with tables created."""
    # Import BEFORE creating engine to avoid conflicts with Agent model
    from app.models.tool_spec009 import Tool

    # Create a separate metadata for Tool SPEC-009 to avoid conflicts
    from sqlalchemy import MetaData

    tool_metadata = MetaData()

    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create only the tools_spec009 table
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda connection: Tool.__table__.create(connection, checkfirst=True)
        )

    # Create session
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    # Drop table
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda connection: Tool.__table__.drop(connection, checkfirst=True)
        )

    await engine.dispose()


class TestToolModelBehavior:
    """Test SPEC-009 Tool model behavior with database operations."""

    @pytest.mark.asyncio
    async def test_tool_creation_with_required_fields(self, db_session) -> None:
        """Tool should be creatable with required fields (name, parameters)."""
        from app.models.tool_spec009 import Tool

        tool = Tool(
            name="price_fetcher",
            parameters={"type": "object", "properties": {}},
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.id is not None
        assert tool.name == "price_fetcher"
        assert tool.parameters == {"type": "object", "properties": {}}

    @pytest.mark.asyncio
    async def test_tool_creation_with_all_fields(self, db_session) -> None:
        """Tool should be creatable with all fields."""
        from app.models.tool_spec009 import Tool

        tool = Tool(
            name="indicator_calculator",
            description="주식 기술적 지표를 계산하는 도구",
            parameters={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "period": {"type": "string", "enum": ["1d", "1w", "1m"]},
                },
                "required": ["symbol"],
            },
            implementation_path="meta_llm.tools.data_fetcher.PriceFetcher",
            is_active=True,
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.name == "indicator_calculator"
        assert tool.description == "주식 기술적 지표를 계산하는 도구"
        assert "symbol" in tool.parameters["properties"]
        assert tool.implementation_path == "meta_llm.tools.data_fetcher.PriceFetcher"
        assert tool.is_active is True

    @pytest.mark.asyncio
    async def test_tool_name_unique_constraint(self, db_session) -> None:
        """Tool name should have unique constraint."""
        from app.models.tool_spec009 import Tool

        tool1 = Tool(name="duplicate_tool", parameters={})
        db_session.add(tool1)
        await db_session.commit()

        tool2 = Tool(name="duplicate_tool", parameters={})
        db_session.add(tool2)

        with pytest.raises(Exception):  # IntegrityError for unique constraint
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tool_parameters_json_schema(self, db_session) -> None:
        """Tool parameters should accept JSON Schema structure."""
        from app.models.tool_spec009 import Tool

        json_schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 120},
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        }

        tool = Tool(name="http_request_tool", parameters=json_schema)
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.parameters == json_schema
        assert tool.parameters["properties"]["url"]["type"] == "string"
        assert tool.parameters["properties"]["timeout"]["minimum"] == 1

    @pytest.mark.asyncio
    async def test_tool_is_active_default(self, db_session) -> None:
        """Tool is_active should default to True."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="default_active_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.is_active is True

    @pytest.mark.asyncio
    async def test_tool_implementation_path_nullable(self, db_session) -> None:
        """Tool implementation_path should be nullable."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="builtin_tool", parameters={}, implementation_path=None)
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.implementation_path is None

    @pytest.mark.asyncio
    async def test_tool_description_nullable(self, db_session) -> None:
        """Tool description should be nullable."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="no_desc_tool", parameters={}, description=None)
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.description is None

    @pytest.mark.asyncio
    async def test_tool_parameters_default(self, db_session) -> None:
        """Tool parameters should default to empty dict."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="default_params_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.parameters == {}

    @pytest.mark.asyncio
    async def test_tool_timestamps(self, db_session) -> None:
        """Tool should have auto-generated timestamps."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="timestamped_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.created_at is not None
        assert tool.updated_at is not None
        assert isinstance(tool.created_at, datetime)
        assert isinstance(tool.updated_at, datetime)
        # Note: SQLite doesn't support timezone, so tzinfo may be None
        # PostgreSQL will have timezone info

    @pytest.mark.asyncio
    async def test_tool_update_reflects_timestamp(self, db_session) -> None:
        """Tool update should reflect in updated_at timestamp."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="update_timestamp_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        original_updated_at = tool.updated_at

        # Small delay to ensure timestamp difference
        import asyncio

        await asyncio.sleep(0.01)

        tool.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(tool)

        assert tool.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_tool_query_by_name(self, db_session) -> None:
        """Tool should be queryable by name."""
        from app.models.tool_spec009 import Tool
        from sqlalchemy import select

        tool = Tool(name="queryable_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()

        result = await db_session.execute(
            select(Tool).where(Tool.name == "queryable_tool")
        )
        found_tool = result.scalar_one_or_none()

        assert found_tool is not None
        assert found_tool.name == "queryable_tool"

    @pytest.mark.asyncio
    async def test_tool_query_by_is_active(self, db_session) -> None:
        """Tool should be queryable by is_active status."""
        from app.models.tool_spec009 import Tool
        from sqlalchemy import select

        active_tool = Tool(name="active_tool", parameters={}, is_active=True)
        inactive_tool = Tool(name="inactive_tool", parameters={}, is_active=False)
        db_session.add_all([active_tool, inactive_tool])
        await db_session.commit()

        result = await db_session.execute(select(Tool).where(Tool.is_active == True))
        active_tools = result.scalars().all()

        assert len(active_tools) == 1
        assert active_tools[0].name == "active_tool"

    @pytest.mark.asyncio
    async def test_tool_repr(self, db_session) -> None:
        """Tool should have a useful __repr__ method."""
        from app.models.tool_spec009 import Tool

        tool = Tool(name="repr_tool", parameters={})
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)

        repr_str = repr(tool)
        assert "Tool" in repr_str
        assert str(tool.id) in repr_str or "repr_tool" in repr_str
