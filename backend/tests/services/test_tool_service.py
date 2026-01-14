"""Service layer tests for ToolService.

TAG: [SPEC-007] [TESTS] [SERVICE] [TOOL]
REQ: REQ-001 - ToolService CRUD Operations
REQ: REQ-002 - Tool Test Execution
REQ: REQ-003 - Tool Filtering and Search
REQ: REQ-004 - Soft Delete Behavior
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.enums import ToolType
from app.models.tool import Tool
from app.schemas.tool import ToolCreate, ToolUpdate
from app.services.tool_service import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolService,
    ToolServiceError,
)


# =============================================================================
# ToolService CRUD Tests
# =============================================================================


class TestToolServiceCreate:
    """Test ToolService.create() method."""

    @pytest.mark.asyncio
    async def test_create_tool_success(self, db_session):
        """Test successful tool creation."""
        owner_id = uuid4()
        data = ToolCreate(
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.HTTP,
            config={"url": "https://api.example.com"},
            input_schema={"type": "object"},
            output_schema=None,
            auth_config=None,
            rate_limit=None,
            is_active=True,
            is_public=False,
        )

        service = ToolService(db_session)
        tool = await service.create(owner_id, data)

        assert tool.id is not None
        assert tool.name == "Test Tool"
        assert tool.tool_type == ToolType.HTTP
        assert tool.is_active is True

    @pytest.mark.asyncio
    async def test_create_tool_database_failure(self, db_session, monkeypatch):
        """Test tool creation with database failure."""
        owner_id = uuid4()
        data = ToolCreate(
            name="Test Tool",
            tool_type=ToolType.HTTP,
            config={"url": "https://api.example.com"},
            input_schema={},
        )

        service = ToolService(db_session)

        # Mock flush to raise database error
        async def mock_flush():
            raise SQLAlchemyError("Database connection lost")

        monkeypatch.setattr(db_session, "flush", mock_flush)

        with pytest.raises(ToolServiceError, match="Failed to create tool"):
            await service.create(owner_id, data)


class TestToolServiceGet:
    """Test ToolService.get() method."""

    @pytest.mark.asyncio
    async def test_get_tool_found(self, db_session, tool_factory):
        """Test getting an existing tool."""
        tool = tool_factory(name="Test Tool")
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        result = await service.get(tool.id)

        assert result is not None
        assert result.id == tool.id
        assert result.name == "Test Tool"

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, db_session):
        """Test getting a non-existent tool."""
        service = ToolService(db_session)
        result = await service.get(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tool_include_deleted_true(self, db_session, tool_factory):
        """Test getting a deleted tool with include_deleted=True."""
        tool = tool_factory(name="Deleted Tool")
        tool.soft_delete()
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)

        # Without include_deleted, should return None
        result = await service.get(tool.id, include_deleted=False)
        assert result is None

        # With include_deleted=True, should return the tool
        result = await service.get(tool.id, include_deleted=True)
        assert result is not None
        assert result.id == tool.id

    @pytest.mark.asyncio
    async def test_get_tool_include_deleted_false(self, db_session, tool_factory):
        """Test that deleted tools are excluded by default."""
        tool = tool_factory(name="Active Tool")
        db_session.add(tool)
        await db_session.flush()

        # Create deleted tool
        deleted_tool = tool_factory(name="Deleted Tool")
        deleted_tool.soft_delete()
        db_session.add(deleted_tool)
        await db_session.flush()

        service = ToolService(db_session)

        # Should only return active tool
        result = await service.get(tool.id, include_deleted=False)
        assert result is not None
        assert result.id == tool.id

        # Deleted tool should return None
        result = await service.get(deleted_tool.id, include_deleted=False)
        assert result is None


class TestToolServiceList:
    """Test ToolService.list() method."""

    @pytest.mark.asyncio
    async def test_list_tools_no_filters(self, db_session, tool_factory):
        """Test listing tools without filters."""
        owner_id = uuid4()
        for i in range(3):
            tool = tool_factory(owner_id=owner_id, name=f"Tool {i}")
            db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        results = await service.list(owner_id)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_tools_with_tool_type_filter(self, db_session, tool_factory):
        """Test listing tools filtered by tool type."""
        owner_id = uuid4()
        http_tool = tool_factory(owner_id=owner_id, tool_type=ToolType.HTTP)
        mcp_tool = tool_factory(owner_id=owner_id, tool_type=ToolType.MCP)
        db_session.add_all([http_tool, mcp_tool])
        await db_session.flush()

        service = ToolService(db_session)
        results = await service.list(owner_id, tool_type="http")

        assert len(results) == 1
        assert results[0].tool_type == ToolType.HTTP

    @pytest.mark.asyncio
    async def test_list_tools_with_is_active_filter(self, db_session, tool_factory):
        """Test listing tools filtered by active status."""
        owner_id = uuid4()
        active_tool = tool_factory(owner_id=owner_id, is_active=True)
        inactive_tool = tool_factory(owner_id=owner_id, is_active=False)
        db_session.add_all([active_tool, inactive_tool])
        await db_session.flush()

        service = ToolService(db_session)

        # Filter for active tools
        results = await service.list(owner_id, is_active=True)
        assert len(results) == 1
        assert results[0].is_active is True

        # Filter for inactive tools
        results = await service.list(owner_id, is_active=False)
        assert len(results) == 1
        assert results[0].is_active is False

    @pytest.mark.asyncio
    async def test_list_tools_with_is_public_filter(self, db_session, tool_factory):
        """Test listing tools filtered by public status."""
        owner_id = uuid4()
        public_tool = tool_factory(owner_id=owner_id, is_public=True)
        private_tool = tool_factory(owner_id=owner_id, is_public=False)
        db_session.add_all([public_tool, private_tool])
        await db_session.flush()

        service = ToolService(db_session)
        results = await service.list(owner_id, is_public=True)

        assert len(results) == 1
        assert results[0].is_public is True

    @pytest.mark.asyncio
    async def test_list_tools_multiple_filters(self, db_session, tool_factory):
        """Test listing tools with multiple filters."""
        owner_id = uuid4()
        tool1 = tool_factory(
            owner_id=owner_id,
            tool_type=ToolType.HTTP,
            is_active=True,
            is_public=True,
        )
        tool2 = tool_factory(
            owner_id=owner_id,
            tool_type=ToolType.MCP,
            is_active=True,
            is_public=True,
        )
        tool3 = tool_factory(
            owner_id=owner_id,
            tool_type=ToolType.HTTP,
            is_active=False,
            is_public=True,
        )
        db_session.add_all([tool1, tool2, tool3])
        await db_session.flush()

        service = ToolService(db_session)
        results = await service.list(
            owner_id, tool_type="http", is_active=True, is_public=True
        )

        assert len(results) == 1
        assert results[0].tool_type == ToolType.HTTP
        assert results[0].is_active is True

    @pytest.mark.asyncio
    async def test_list_tools_include_deleted(self, db_session, tool_factory):
        """Test listing tools with include_deleted flag."""
        owner_id = uuid4()
        active_tool = tool_factory(owner_id=owner_id, name="Active Tool")
        deleted_tool = tool_factory(owner_id=owner_id, name="Deleted Tool")
        deleted_tool.soft_delete()
        db_session.add_all([active_tool, deleted_tool])
        await db_session.flush()

        service = ToolService(db_session)

        # Without include_deleted, should only return active
        results = await service.list(owner_id, include_deleted=False)
        assert len(results) == 1
        assert results[0].name == "Active Tool"

        # With include_deleted=True, should return both
        results = await service.list(owner_id, include_deleted=True)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_tools_pagination(self, db_session, tool_factory):
        """Test tool listing with pagination."""
        owner_id = uuid4()
        for i in range(5):
            tool = tool_factory(owner_id=owner_id, name=f"Tool {i}")
            db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        results = await service.list(owner_id, skip=2, limit=2)

        assert len(results) == 2


class TestToolServiceCount:
    """Test ToolService.count() method."""

    @pytest.mark.asyncio
    async def test_count_tools_all(self, db_session, tool_factory):
        """Test counting all tools."""
        owner_id = uuid4()
        for i in range(3):
            tool = tool_factory(owner_id=owner_id)
            db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        count = await service.count(owner_id)

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_tools_with_filters(self, db_session, tool_factory):
        """Test counting tools with filters."""
        owner_id = uuid4()
        http_tool = tool_factory(owner_id=owner_id, tool_type=ToolType.HTTP)
        mcp_tool = tool_factory(owner_id=owner_id, tool_type=ToolType.MCP)
        db_session.add_all([http_tool, mcp_tool])
        await db_session.flush()

        service = ToolService(db_session)
        count = await service.count(owner_id, tool_type="http")

        assert count == 1

    @pytest.mark.asyncio
    async def test_count_tools_returns_zero(self, db_session):
        """Test count returns zero when no tools match."""
        owner_id = uuid4()
        service = ToolService(db_session)
        count = await service.count(owner_id)

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_tools_include_deleted(self, db_session, tool_factory):
        """Test counting with include_deleted flag."""
        owner_id = uuid4()
        active_tool = tool_factory(owner_id=owner_id)
        deleted_tool = tool_factory(owner_id=owner_id)
        deleted_tool.soft_delete()
        db_session.add_all([active_tool, deleted_tool])
        await db_session.flush()

        service = ToolService(db_session)

        # Without include_deleted
        count = await service.count(owner_id, include_deleted=False)
        assert count == 1

        # With include_deleted
        count = await service.count(owner_id, include_deleted=True)
        assert count == 2


class TestToolServiceUpdate:
    """Test ToolService.update() method."""

    @pytest.mark.asyncio
    async def test_update_tool_success(self, db_session, tool_factory):
        """Test successful tool update."""
        tool = tool_factory(name="Original Name")
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        update_data = ToolUpdate(name="Updated Name", is_active=False)

        updated = await service.update(tool.id, update_data)

        assert updated.name == "Updated Name"
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_update_tool_partial_fields(self, db_session, tool_factory):
        """Test updating tool with partial fields."""
        tool = tool_factory(
            name="Test",
            description="Original",
            is_active=True,
            is_public=False,
        )
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        update_data = ToolUpdate(description="Updated Description")

        updated = await service.update(tool.id, update_data)

        assert updated.description == "Updated Description"
        assert updated.name == "Test"  # Unchanged
        assert updated.is_active is True  # Unchanged

    @pytest.mark.asyncio
    async def test_update_tool_not_found(self, db_session):
        """Test updating non-existent tool raises error."""
        service = ToolService(db_session)
        update_data = ToolUpdate(name="Updated")

        with pytest.raises(ToolNotFoundError):
            await service.update(uuid4(), update_data)

    @pytest.mark.asyncio
    async def test_update_tool_database_failure(
        self, db_session, tool_factory, monkeypatch
    ):
        """Test update with database failure."""
        tool = tool_factory()
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        update_data = ToolUpdate(name="Updated")

        # Mock flush to raise database error
        async def mock_flush():
            raise SQLAlchemyError("Database connection lost")

        monkeypatch.setattr(db_session, "flush", mock_flush)

        with pytest.raises(ToolServiceError, match="Failed to update tool"):
            await service.update(tool.id, update_data)


class TestToolServiceDelete:
    """Test ToolService.delete() method."""

    @pytest.mark.asyncio
    async def test_delete_tool_success(self, db_session, tool_factory):
        """Test successful tool soft delete."""
        tool = tool_factory(name="To Delete")
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        deleted = await service.delete(tool.id)

        assert deleted.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_tool_not_found(self, db_session):
        """Test deleting non-existent tool raises error."""
        service = ToolService(db_session)

        with pytest.raises(ToolNotFoundError):
            await service.delete(uuid4())

    @pytest.mark.asyncio
    async def test_delete_tool_sets_deleted_at(self, db_session, tool_factory):
        """Test that delete sets deleted_at timestamp."""
        tool = tool_factory()
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        deleted = await service.delete(tool.id)

        assert deleted.deleted_at is not None


class TestToolServiceTestExecute:
    """Test ToolService.test_execute() method."""

    @pytest.mark.asyncio
    async def test_tool_execute_success(self, db_session, tool_factory):
        """Test successful tool execution."""
        tool = tool_factory(is_active=True)
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        input_data = {"param1": "value1"}

        result = await service.test_execute(tool.id, input_data)

        assert result["success"] is True
        assert "execution_time_ms" in result
        assert result["output"]["input"] == input_data

    @pytest.mark.asyncio
    async def test_tool_execute_tool_not_found(self, db_session):
        """Test tool execution with non-existent tool."""
        service = ToolService(db_session)

        with pytest.raises(ToolNotFoundError):
            await service.test_execute(uuid4(), {})

    @pytest.mark.asyncio
    async def test_tool_execute_inactive_tool(self, db_session, tool_factory):
        """Test tool execution on inactive tool raises error."""
        tool = tool_factory(is_active=False)
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)

        with pytest.raises(ToolExecutionError, match="not active"):
            await service.test_execute(tool.id, {})

    @pytest.mark.asyncio
    async def test_tool_execute_returns_execution_time(self, db_session, tool_factory):
        """Test that tool execution returns execution time."""
        tool = tool_factory(is_active=True)
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        result = await service.test_execute(tool.id, {})

        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], float)
        assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_tool_execute_mock_response_structure(self, db_session, tool_factory):
        """Test that tool execution returns correct response structure."""
        tool = tool_factory(is_active=True)
        db_session.add(tool)
        await db_session.flush()

        service = ToolService(db_session)
        input_data = {"test": "data"}
        result = await service.test_execute(tool.id, input_data)

        # Verify response structure
        assert "success" in result
        assert "output" in result
        assert "error" in result
        assert "execution_time_ms" in result
        assert result["success"] is True
        assert result["error"] is None
        assert result["output"]["input"] == input_data
