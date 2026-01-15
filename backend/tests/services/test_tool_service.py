"""Tool service tests.

TAG: [SPEC-009] [TESTS] [SERVICE] [TOOL]
REQ: REQ-001 - ToolService CRUD Operations Tests
REQ: REQ-002 - Tool Test Execution Tests
REQ: REQ-003 - Tool Filtering and Search Tests

Comprehensive tests for ToolService covering all CRUD operations,
error cases, and edge cases to achieve 80%+ code coverage.
"""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.models.enums import ToolType
from app.schemas.tool import ToolCreate, ToolUpdate
from app.services.tool_service import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolService,
    ToolServiceError,
)

# =============================================================================
# Test Fixtures
# =============================================================================


class ToolCreateFactory:
    """Factory for creating ToolCreate instances."""

    @staticmethod
    def create(**kwargs):
        """Create a ToolCreate instance with defaults."""
        defaults = {
            "name": "Test HTTP Tool",
            "description": "A test HTTP tool",
            "tool_type": "http",
            "config": {
                "url": "https://api.example.com/endpoint",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "output_schema": {
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            "auth_config": {"api_key": "test_key"},
            "rate_limit": {"max_calls": 100, "period": "hour"},
            "is_active": True,
            "is_public": False,
        }
        defaults.update(kwargs)
        return ToolCreate(**defaults)


@pytest.fixture
def tool_create_factory():
    """Fixture for ToolCreate factory."""
    return ToolCreateFactory.create


@pytest.fixture
def sample_owner_id():
    """Sample owner ID for testing."""
    return UUID("00000000-0000-0000-0000-000000000001")


# =============================================================================
# Test ToolService.__init__
# =============================================================================


class TestToolServiceInit:
    """Test ToolService initialization."""

    async def test_init_with_db_session(self, db_session):
        """Test that ToolService initializes with db session."""
        service = ToolService(db_session)
        assert service.db == db_session


# =============================================================================
# Test ToolService.create
# =============================================================================


class TestToolServiceCreate:
    """Test tool creation."""

    async def test_create_tool_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool creation."""
        service = ToolService(db_session)
        data = tool_create_factory()

        tool = await service.create(sample_owner_id, data)

        assert tool.id is not None
        assert tool.owner_id == sample_owner_id
        assert tool.name == "Test HTTP Tool"
        assert tool.description == "A test HTTP tool"
        assert tool.tool_type == ToolType.HTTP
        assert tool.config == {
            "url": "https://api.example.com/endpoint",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
        }
        assert tool.is_active is True
        assert tool.is_public is False
        assert tool.created_at is not None
        assert tool.updated_at is not None
        assert tool.deleted_at is None

    async def test_create_tool_with_all_fields(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test tool creation with all optional fields."""
        service = ToolService(db_session)
        data = tool_create_factory(
            name="Python Script Tool",
            description="Executes Python code",
            tool_type="python",
            config={"code": "print('hello')"},
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            auth_config={"token": "secret"},
            rate_limit={"max_calls": 50, "period": "minute"},
            is_active=False,
            is_public=True,
        )

        tool = await service.create(sample_owner_id, data)

        assert tool.name == "Python Script Tool"
        assert tool.description == "Executes Python code"
        assert tool.tool_type == ToolType.PYTHON
        assert tool.is_active is False
        assert tool.is_public is True

    async def test_create_tool_with_minimal_fields(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test tool creation with minimal required fields."""
        service = ToolService(db_session)
        data = tool_create_factory(
            description=None,
            output_schema=None,
            auth_config=None,
            rate_limit=None,
        )

        tool = await service.create(sample_owner_id, data)

        assert tool.name == "Test HTTP Tool"
        assert tool.description is None
        assert tool.output_schema is None
        assert tool.auth_config is None
        assert tool.rate_limit is None

    async def test_create_tool_service_error_on_exception(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that ToolServiceError is raised on database error."""
        service = ToolService(db_session)
        data = tool_create_factory()

        # Mock db.add to raise an exception
        with patch.object(db_session, "add", side_effect=Exception("DB error")):
            with pytest.raises(ToolServiceError) as exc_info:
                await service.create(sample_owner_id, data)

            assert "Failed to create tool" in str(exc_info.value)
            assert "DB error" in str(exc_info.value)

    async def test_create_tool_flush_error(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that ToolServiceError is raised on flush error."""
        service = ToolService(db_session)
        data = tool_create_factory()

        # Mock db.flush to raise an exception
        with patch.object(db_session, "flush", side_effect=Exception("Flush failed")):
            with pytest.raises(ToolServiceError) as exc_info:
                await service.create(sample_owner_id, data)

            assert "Failed to create tool" in str(exc_info.value)


# =============================================================================
# Test ToolService.get
# =============================================================================


class TestToolServiceGet:
    """Test tool retrieval by ID."""

    async def test_get_tool_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool retrieval."""
        service = ToolService(db_session)

        # Create a tool first
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Get the tool
        tool = await service.get(created_tool.id)

        assert tool is not None
        assert tool.id == created_tool.id
        assert tool.name == "Test HTTP Tool"

    async def test_get_tool_not_found(self, db_session):
        """Test getting non-existent tool returns None."""
        service = ToolService(db_session)
        tool = await service.get(uuid4())
        assert tool is None

    async def test_get_tool_include_deleted_false(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that deleted tools are not returned by default."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Delete the tool
        await service.delete(created_tool.id)

        # Try to get the tool without include_deleted
        tool = await service.get(created_tool.id, include_deleted=False)
        assert tool is None

    async def test_get_tool_include_deleted_true(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that deleted tools are returned when include_deleted=True."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Delete the tool
        deleted_tool = await service.delete(created_tool.id)

        # Get the tool with include_deleted=True
        tool = await service.get(created_tool.id, include_deleted=True)

        assert tool is not None
        assert tool.id == deleted_tool.id
        assert tool.deleted_at is not None


# =============================================================================
# Test ToolService.list
# =============================================================================


class TestToolServiceList:
    """Test tool listing with filtering."""

    async def test_list_tools_empty(self, db_session, sample_owner_id):
        """Test listing tools when none exist."""
        service = ToolService(db_session)
        tools = await service.list(sample_owner_id)
        assert tools == []

    async def test_list_tools_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool listing."""
        service = ToolService(db_session)

        # Create multiple tools
        await service.create(sample_owner_id, tool_create_factory(name="Tool 1"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool 2"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool 3"))

        tools = await service.list(sample_owner_id)

        assert len(tools) == 3
        assert all(t.owner_id == sample_owner_id for t in tools)

    async def test_list_tools_with_skip_limit(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test listing with pagination."""
        service = ToolService(db_session)

        # Create multiple tools
        for i in range(5):
            await service.create(sample_owner_id, tool_create_factory(name=f"Tool {i}"))

        # List with skip and limit
        tools = await service.list(sample_owner_id, skip=2, limit=2)

        assert len(tools) == 2

    async def test_list_tools_filter_by_type(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test filtering tools by type."""
        service = ToolService(db_session)

        # Create tools of different types
        await service.create(
            sample_owner_id, tool_create_factory(name="HTTP Tool", tool_type="http")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Python Tool", tool_type="python")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="MCP Tool", tool_type="mcp")
        )

        # Filter by http type
        tools = await service.list(sample_owner_id, tool_type="http")

        assert len(tools) == 1
        assert tools[0].tool_type == ToolType.HTTP

    async def test_list_tools_filter_by_is_active(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test filtering tools by active status."""
        service = ToolService(db_session)

        # Create active and inactive tools
        await service.create(
            sample_owner_id, tool_create_factory(name="Active Tool", is_active=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Inactive Tool", is_active=False)
        )

        # Filter by active status
        tools = await service.list(sample_owner_id, is_active=True)

        assert len(tools) == 1
        assert tools[0].is_active is True

    async def test_list_tools_filter_by_is_public(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test filtering tools by public status."""
        service = ToolService(db_session)

        # Create public and private tools
        await service.create(
            sample_owner_id, tool_create_factory(name="Public Tool", is_public=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Private Tool", is_public=False)
        )

        # Filter by public status
        tools = await service.list(sample_owner_id, is_public=True)

        assert len(tools) == 1
        assert tools[0].is_public is True

    async def test_list_tools_include_deleted(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test including deleted tools in list."""
        service = ToolService(db_session)

        # Create tools
        tool1 = await service.create(
            sample_owner_id, tool_create_factory(name="Tool 1")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Tool 2")
        )

        # Delete one tool
        await service.delete(tool1.id)

        # List without deleted
        tools = await service.list(sample_owner_id, include_deleted=False)
        assert len(tools) == 1

        # List with deleted
        tools = await service.list(sample_owner_id, include_deleted=True)
        assert len(tools) == 2

    async def test_list_tools_with_combined_filters(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test listing with multiple filters combined."""
        service = ToolService(db_session)

        # Create various tools
        await service.create(
            sample_owner_id,
            tool_create_factory(name="HTTP Active", tool_type="http", is_active=True),
        )
        await service.create(
            sample_owner_id,
            tool_create_factory(
                name="HTTP Inactive", tool_type="http", is_active=False
            ),
        )
        await service.create(
            sample_owner_id,
            tool_create_factory(
                name="Python Active", tool_type="python", is_active=True
            ),
        )

        # Filter by type and active status
        tools = await service.list(sample_owner_id, tool_type="http", is_active=True)

        assert len(tools) == 1
        assert tools[0].tool_type == ToolType.HTTP
        assert tools[0].is_active is True

    async def test_list_tools_different_owner(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that only tools for specific owner are returned."""
        service = ToolService(db_session)

        # Create tools for different owners
        other_owner_id = UUID("00000000-0000-0000-0000-000000000002")
        await service.create(sample_owner_id, tool_create_factory(name="Owner 1 Tool"))
        await service.create(other_owner_id, tool_create_factory(name="Owner 2 Tool"))

        # List for sample_owner_id
        tools = await service.list(sample_owner_id)

        assert len(tools) == 1
        assert tools[0].owner_id == sample_owner_id

    async def test_list_tools_ordering(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that tools are ordered by created_at descending."""
        service = ToolService(db_session)

        # Create tools
        await service.create(sample_owner_id, tool_create_factory(name="Tool A"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool B"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool C"))

        tools = await service.list(sample_owner_id)

        # Should be ordered by created_at descending (most recent first)
        assert tools[0].name == "Tool C"
        assert tools[1].name == "Tool B"
        assert tools[2].name == "Tool A"


# =============================================================================
# Test ToolService.count
# =============================================================================


class TestToolServiceCount:
    """Test tool counting with filtering."""

    async def test_count_tools_empty(self, db_session, sample_owner_id):
        """Test counting when no tools exist."""
        service = ToolService(db_session)
        count = await service.count(sample_owner_id)
        assert count == 0

    async def test_count_tools_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool counting."""
        service = ToolService(db_session)

        # Create multiple tools
        await service.create(sample_owner_id, tool_create_factory(name="Tool 1"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool 2"))
        await service.create(sample_owner_id, tool_create_factory(name="Tool 3"))

        count = await service.count(sample_owner_id)

        assert count == 3

    async def test_count_tools_filter_by_type(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting by tool type."""
        service = ToolService(db_session)

        # Create tools of different types
        await service.create(
            sample_owner_id, tool_create_factory(name="HTTP Tool 1", tool_type="http")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="HTTP Tool 2", tool_type="http")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Python Tool", tool_type="python")
        )

        count = await service.count(sample_owner_id, tool_type="http")

        assert count == 2

    async def test_count_tools_filter_by_is_active(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting by active status."""
        service = ToolService(db_session)

        # Create active and inactive tools
        await service.create(
            sample_owner_id, tool_create_factory(name="Active 1", is_active=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Active 2", is_active=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Inactive", is_active=False)
        )

        count = await service.count(sample_owner_id, is_active=True)

        assert count == 2

    async def test_count_tools_filter_by_is_public(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting by public status."""
        service = ToolService(db_session)

        # Create public and private tools
        await service.create(
            sample_owner_id, tool_create_factory(name="Public 1", is_public=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Public 2", is_public=True)
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Private", is_public=False)
        )

        count = await service.count(sample_owner_id, is_public=True)

        assert count == 2

    async def test_count_tools_include_deleted(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting including deleted tools."""
        service = ToolService(db_session)

        # Create tools
        tool1 = await service.create(
            sample_owner_id, tool_create_factory(name="Tool 1")
        )
        await service.create(
            sample_owner_id, tool_create_factory(name="Tool 2")
        )

        # Delete one tool
        await service.delete(tool1.id)

        # Count without deleted
        count = await service.count(sample_owner_id, include_deleted=False)
        assert count == 1

        # Count with deleted
        count = await service.count(sample_owner_id, include_deleted=True)
        assert count == 2

    async def test_count_tools_with_combined_filters(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting with multiple filters."""
        service = ToolService(db_session)

        # Create various tools
        await service.create(
            sample_owner_id,
            tool_create_factory(name="HTTP Active", tool_type="http", is_active=True),
        )
        await service.create(
            sample_owner_id,
            tool_create_factory(
                name="HTTP Inactive", tool_type="http", is_active=False
            ),
        )
        await service.create(
            sample_owner_id,
            tool_create_factory(
                name="Python Active", tool_type="python", is_active=True
            ),
        )

        # Count by type and active status
        count = await service.count(sample_owner_id, tool_type="http", is_active=True)

        assert count == 1

    async def test_count_tools_different_owner(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test counting only for specific owner."""
        service = ToolService(db_session)

        # Create tools for different owners
        other_owner_id = UUID("00000000-0000-0000-0000-000000000002")
        await service.create(sample_owner_id, tool_create_factory(name="Owner 1 Tool"))
        await service.create(
            sample_owner_id, tool_create_factory(name="Owner 1 Tool 2")
        )
        await service.create(other_owner_id, tool_create_factory(name="Owner 2 Tool"))

        # Count for sample_owner_id
        count = await service.count(sample_owner_id)

        assert count == 2


# =============================================================================
# Test ToolService.update
# =============================================================================


class TestToolServiceUpdate:
    """Test tool updates."""

    async def test_update_tool_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool update."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory(name="Original Name")
        created_tool = await service.create(sample_owner_id, data)

        # Update the tool
        update_data = ToolUpdate(name="Updated Name")
        updated_tool = await service.update(created_tool.id, update_data)

        assert updated_tool.name == "Updated Name"
        assert updated_tool.id == created_tool.id

    async def test_update_tool_multiple_fields(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test updating multiple fields."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Update multiple fields
        update_data = ToolUpdate(
            name="Updated Name",
            description="Updated description",
            is_active=False,
            is_public=True,
        )
        updated_tool = await service.update(created_tool.id, update_data)

        assert updated_tool.name == "Updated Name"
        assert updated_tool.description == "Updated description"
        assert updated_tool.is_active is False
        assert updated_tool.is_public is True

    async def test_update_tool_only_updates_provided_fields(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that only provided fields are updated."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory(
            name="Original Name", description="Original Description", is_active=True
        )
        created_tool = await service.create(sample_owner_id, data)

        # Update only name
        update_data = ToolUpdate(name="Updated Name")
        updated_tool = await service.update(created_tool.id, update_data)

        # Only name should be updated
        assert updated_tool.name == "Updated Name"
        assert updated_tool.description == "Original Description"
        assert updated_tool.is_active is True

    async def test_update_tool_not_found(self, db_session):
        """Test updating non-existent tool raises ToolNotFoundError."""
        service = ToolService(db_session)

        update_data = ToolUpdate(name="Updated Name")

        with pytest.raises(ToolNotFoundError) as exc_info:
            await service.update(uuid4(), update_data)

        assert "not found" in str(exc_info.value)

    async def test_update_tool_service_error_on_exception(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that ToolServiceError is raised on database error during update."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Mock refresh to raise an exception
        with patch.object(
            db_session, "refresh", side_effect=Exception("Refresh failed")
        ):
            with pytest.raises(ToolServiceError) as exc_info:
                update_data = ToolUpdate(name="Updated Name")
                await service.update(created_tool.id, update_data)

            assert "Failed to update tool" in str(exc_info.value)

    async def test_update_tool_updates_timestamp(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that updated_at timestamp is updated."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)
        original_updated_at = created_tool.updated_at

        # Wait a bit and update
        import time

        time.sleep(0.01)
        update_data = ToolUpdate(name="Updated Name")
        updated_tool = await service.update(created_tool.id, update_data)

        assert updated_tool.updated_at > original_updated_at


# =============================================================================
# Test ToolService.delete
# =============================================================================


class TestToolServiceDelete:
    """Test tool soft deletion."""

    async def test_delete_tool_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool soft deletion."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Delete the tool
        deleted_tool = await service.delete(created_tool.id)

        assert deleted_tool.id == created_tool.id
        assert deleted_tool.deleted_at is not None

        # Verify tool is soft deleted (cannot be retrieved without include_deleted)
        tool = await service.get(created_tool.id)
        assert tool is None

    async def test_delete_tool_not_found(self, db_session):
        """Test deleting non-existent tool raises ToolNotFoundError."""
        service = ToolService(db_session)

        with pytest.raises(ToolNotFoundError) as exc_info:
            await service.delete(uuid4())

        assert "not found" in str(exc_info.value)

    async def test_delete_tool_already_deleted(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test deleting an already deleted tool raises ToolNotFoundError."""
        service = ToolService(db_session)

        # Create a tool
        data = tool_create_factory()
        created_tool = await service.create(sample_owner_id, data)

        # Delete the tool
        await service.delete(created_tool.id)

        # Try to delete again
        with pytest.raises(ToolNotFoundError):
            await service.delete(created_tool.id)


# =============================================================================
# Test ToolService.test_execute
# =============================================================================


class TestToolServiceTestExecute:
    """Test tool test execution."""

    async def test_test_execute_success(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test successful tool test execution."""
        service = ToolService(db_session)

        # Create an active tool
        data = tool_create_factory(is_active=True)
        created_tool = await service.create(sample_owner_id, data)

        # Test execute
        input_data = {"query": "test query"}
        result = await service.test_execute(created_tool.id, input_data)

        assert result["success"] is True
        assert "output" in result
        assert result["output"]["message"] == "Tool execution simulated"
        assert result["output"]["input"] == input_data
        assert result["error"] is None
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0

    async def test_test_execute_tool_not_found(self, db_session):
        """Test executing non-existent tool raises ToolNotFoundError."""
        service = ToolService(db_session)

        with pytest.raises(ToolNotFoundError) as exc_info:
            await service.test_execute(uuid4(), {"query": "test"})

        assert "not found" in str(exc_info.value)

    async def test_test_execute_tool_not_active(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test executing inactive tool raises ToolExecutionError."""
        service = ToolService(db_session)

        # Create an inactive tool
        data = tool_create_factory(is_active=False)
        created_tool = await service.create(sample_owner_id, data)

        # Try to test execute
        with pytest.raises(ToolExecutionError) as exc_info:
            await service.test_execute(created_tool.id, {"query": "test"})

        assert "not active" in str(exc_info.value)

    async def test_test_execute_with_various_input(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test test execution with various input data."""
        service = ToolService(db_session)

        # Create an active tool
        data = tool_create_factory(is_active=True)
        created_tool = await service.create(sample_owner_id, data)

        # Test with different inputs
        test_cases = [
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"array": [1, 2, 3]},
            {},
        ]

        for input_data in test_cases:
            result = await service.test_execute(created_tool.id, input_data)
            assert result["success"] is True
            assert result["output"]["input"] == input_data

    async def test_test_execute_execution_time_measured(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test that execution time is measured."""
        service = ToolService(db_session)

        # Create an active tool
        data = tool_create_factory(is_active=True)
        created_tool = await service.create(sample_owner_id, data)

        # Test execute
        result = await service.test_execute(created_tool.id, {"query": "test"})

        # Execution time should be a positive number
        assert isinstance(result["execution_time_ms"], float)
        assert result["execution_time_ms"] >= 0

    async def test_test_execute_with_empty_input(
        self, db_session, tool_create_factory, sample_owner_id
    ):
        """Test test execution with empty input data."""
        service = ToolService(db_session)

        # Create an active tool
        data = tool_create_factory(is_active=True)
        created_tool = await service.create(sample_owner_id, data)

        # Test with empty input
        result = await service.test_execute(created_tool.id, {})

        assert result["success"] is True
        assert result["output"]["input"] == {}
        assert result["error"] is None
