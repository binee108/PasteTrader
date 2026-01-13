"""ToolService unit tests.

TAG: [SPEC-009] [TESTING] [TOOL-SERVICE]
REQ: REQ-T005 - ToolService CRUD Implementation

Test suite for ToolService business logic layer covering:
- Create tool with name uniqueness validation
- Read tool by ID and name
- List tools with filtering (is_active, search)
- Update tool fields
- Delete tool with usage prevention
- Error handling and edge cases
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_spec009 import Tool as ToolModel
from app.schemas.tool import ToolCreate, ToolUpdate


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def tool_service():
    """Provide ToolService instance for testing.

    Returns:
        ToolService: Service instance for CRUD operations.
    """
    from app.services.tool_service import ToolService

    return ToolService()


@pytest_asyncio.fixture
async def sample_tool_create():
    """Provide sample ToolCreate data.

    Returns:
        ToolCreate: Sample tool creation schema.
    """
    return ToolCreate(
        name="test_tool",
        description="Test tool for unit testing",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "timeout": {"type": "integer"},
            },
        },
        implementation_path="tools.test_tool",
    )


@pytest_asyncio.fixture
async def existing_tool(
    db_session: AsyncSession,
    sample_tool_create: ToolCreate,
) -> ToolModel:
    """Create an existing tool in database for testing.

    Args:
        db_session: Database session fixture.
        sample_tool_create: Tool creation data.

    Returns:
        ToolModel: Created tool instance.
    """
    tool = ToolModel(**sample_tool_create.model_dump())
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest_asyncio.fixture
async def multiple_tools(
    db_session: AsyncSession,
) -> list[ToolModel]:
    """Create multiple tools for list testing.

    Args:
        db_session: Database session fixture.

    Returns:
        list[ToolModel]: List of created tools.
    """
    tools = [
        ToolModel(
            name="active_tool_1",
            description="First active tool",
            parameters={"type": "object"},
            is_active=True,
        ),
        ToolModel(
            name="active_tool_2",
            description="Second active tool",
            parameters={"type": "object"},
            is_active=True,
        ),
        ToolModel(
            name="inactive_tool",
            description="Inactive tool",
            parameters={"type": "object"},
            is_active=False,
        ),
        ToolModel(
            name="search_match_tool",
            description="Tool with searchable name",
            parameters={"type": "object"},
            is_active=True,
        ),
    ]
    for tool in tools:
        db_session.add(tool)
    await db_session.commit()
    return tools


# =============================================================================
# Create Tool Tests
# =============================================================================


class TestCreateTool:
    """Test suite for tool creation operations."""

    @pytest.mark.asyncio
    async def test_create_tool_success(
        self,
        db_session: AsyncSession,
        tool_service,
        sample_tool_create: ToolCreate,
    ):
        """Test successful tool creation.

        GIVEN: Valid ToolCreate schema
        WHEN: create_tool is called
        THEN: Tool is created with all fields populated
        """
        # Act
        result = await tool_service.create_tool(db_session, sample_tool_create)

        # Assert
        assert result is not None
        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.name == sample_tool_create.name
        assert result.description == sample_tool_create.description
        assert result.parameters == sample_tool_create.parameters
        assert result.implementation_path == sample_tool_create.implementation_path
        assert result.is_active is True
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)

    @pytest.mark.asyncio
    async def test_create_tool_duplicate_name_raises_error(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
        sample_tool_create: ToolCreate,
    ):
        """Test creating tool with duplicate name raises ValueError.

        GIVEN: Tool with name 'test_tool' already exists
        WHEN: create_tool is called with same name
        THEN: ValueError is raised with appropriate message
        """
        # Arrange - sample_tool_create has same name as existing_tool
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await tool_service.create_tool(db_session, sample_tool_create)

        assert "already exists" in str(exc_info.value)
        assert sample_tool_create.name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_tool_with_optional_fields(
        self,
        db_session: AsyncSession,
        tool_service,
    ):
        """Test creating tool with minimal required fields.

        GIVEN: ToolCreate with only required fields
        WHEN: create_tool is called
        THEN: Tool is created with defaults for optional fields
        """
        # Arrange
        tool_in = ToolCreate(
            name="minimal_tool",
            parameters={"type": "object"},
            description=None,
            implementation_path=None,
        )

        # Act
        result = await tool_service.create_tool(db_session, tool_in)

        # Assert
        assert result.name == "minimal_tool"
        assert result.description is None
        assert result.implementation_path is None
        assert result.is_active is True  # Default value


# =============================================================================
# Read Tool Tests
# =============================================================================


class TestGetTool:
    """Test suite for tool retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_tool_by_id_success(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test retrieving tool by ID.

        GIVEN: Tool with known ID exists
        WHEN: get_tool is called with that ID
        THEN: Tool is returned with all fields
        """
        # Act
        result = await tool_service.get_tool(db_session, existing_tool.id)

        # Assert
        assert result is not None
        assert result.id == existing_tool.id
        assert result.name == existing_tool.name

    @pytest.mark.asyncio
    async def test_get_tool_by_id_not_found(
        self,
        db_session: AsyncSession,
        tool_service,
    ):
        """Test retrieving non-existent tool by ID.

        GIVEN: No tool with the given ID exists
        WHEN: get_tool is called with that ID
        THEN: None is returned
        """
        # Arrange
        non_existent_id = uuid4()

        # Act
        result = await tool_service.get_tool(db_session, non_existent_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tool_by_name_success(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test retrieving tool by name.

        GIVEN: Tool with known name exists
        WHEN: get_tool_by_name is called with that name
        THEN: Tool is returned
        """
        # Act
        result = await tool_service.get_tool_by_name(db_session, existing_tool.name)

        # Assert
        assert result is not None
        assert result.id == existing_tool.id
        assert result.name == existing_tool.name

    @pytest.mark.asyncio
    async def test_get_tool_by_name_not_found(
        self,
        db_session: AsyncSession,
        tool_service,
    ):
        """Test retrieving non-existent tool by name.

        GIVEN: No tool with the given name exists
        WHEN: get_tool_by_name is called with that name
        THEN: None is returned
        """
        # Act
        result = await tool_service.get_tool_by_name(db_session, "non_existent_tool")

        # Assert
        assert result is None


# =============================================================================
# List Tools Tests
# =============================================================================


class TestListTools:
    """Test suite for tool listing operations."""

    @pytest.mark.asyncio
    async def test_list_tools_all(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing all tools without filters.

        GIVEN: Multiple tools exist in database
        WHEN: list_tools is called without filters
        THEN: All tools are returned
        """
        # Act
        result = await tool_service.list_tools(db_session)

        # Assert
        assert len(result) == 4
        assert isinstance(result, list)
        assert all(isinstance(tool, ToolModel) for tool in result)

    @pytest.mark.asyncio
    async def test_list_tools_filter_active_only(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing tools filtered by active status.

        GIVEN: Mix of active and inactive tools exist
        WHEN: list_tools is called with is_active=True
        THEN: Only active tools are returned
        """
        # Act
        result = await tool_service.list_tools(db_session, is_active=True)

        # Assert
        assert len(result) == 3
        assert all(tool.is_active for tool in result)

    @pytest.mark.asyncio
    async def test_list_tools_filter_inactive_only(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing tools filtered by inactive status.

        GIVEN: Mix of active and inactive tools exist
        WHEN: list_tools is called with is_active=False
        THEN: Only inactive tools are returned
        """
        # Act
        result = await tool_service.list_tools(db_session, is_active=False)

        # Assert
        assert len(result) == 1
        assert all(not tool.is_active for tool in result)

    @pytest.mark.asyncio
    async def test_list_tools_with_search(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing tools with name search.

        GIVEN: Multiple tools with different names exist
        WHEN: list_tools is called with search parameter
        THEN: Only tools matching search term are returned

        Note:
            Search is case-insensitive partial match using ILIKE.
            "inactive_tool" also contains "active" in its name,
            so searching for "active" returns 3 tools.
        """
        # Act - search for "active" matches active_tool_1, active_tool_2, and inactive_tool
        result = await tool_service.list_tools(db_session, search="active")

        # Assert - all 3 tools with "active" in name are returned
        assert len(result) == 3
        assert all("active" in tool.name for tool in result)

    @pytest.mark.asyncio
    async def test_list_tools_with_pagination(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing tools with pagination.

        GIVEN: Multiple tools exist
        WHEN: list_tools is called with limit and offset
        THEN: Correct subset is returned
        """
        # Act
        result = await tool_service.list_tools(db_session, limit=2, offset=0)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_tools_combined_filters(
        self,
        db_session: AsyncSession,
        tool_service,
        multiple_tools: list[ToolModel],
    ):
        """Test listing tools with combined filters.

        GIVEN: Multiple tools exist
        WHEN: list_tools is called with active filter and search
        THEN: Only tools matching all criteria are returned
        """
        # Act
        result = await tool_service.list_tools(
            db_session, is_active=True, search="tool"
        )

        # Assert
        assert len(result) == 3
        assert all(tool.is_active for tool in result)


# =============================================================================
# Update Tool Tests
# =============================================================================


class TestUpdateTool:
    """Test suite for tool update operations."""

    @pytest.mark.asyncio
    async def test_update_tool_success(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test updating tool fields.

        GIVEN: Tool exists in database
        WHEN: update_tool is called with new data
        THEN: Tool fields are updated
        """
        # Arrange
        tool_update = ToolUpdate(
            description="Updated description",
            is_active=False,
        )

        # Act
        result = await tool_service.update_tool(
            db_session, existing_tool.id, tool_update
        )

        # Assert
        assert result is not None
        assert result.id == existing_tool.id
        assert result.description == "Updated description"
        assert result.is_active is False
        assert result.name == existing_tool.name  # Unchanged

    @pytest.mark.asyncio
    async def test_update_tool_not_found(
        self,
        db_session: AsyncSession,
        tool_service,
    ):
        """Test updating non-existent tool.

        GIVEN: No tool with given ID exists
        WHEN: update_tool is called with that ID
        THEN: None is returned
        """
        # Arrange
        tool_update = ToolUpdate(description="Updated")
        non_existent_id = uuid4()

        # Act
        result = await tool_service.update_tool(
            db_session, non_existent_id, tool_update
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_tool_partial_fields(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test updating tool with partial fields.

        GIVEN: Tool exists in database
        WHEN: update_tool is called with only some fields
        THEN: Only specified fields are updated
        """
        # Arrange
        original_description = existing_tool.description
        tool_update = ToolUpdate(is_active=False)

        # Act
        result = await tool_service.update_tool(
            db_session, existing_tool.id, tool_update
        )

        # Assert
        assert result is not None
        assert result.is_active is False
        assert result.description == original_description  # Unchanged


# =============================================================================
# Delete Tool Tests
# =============================================================================


class TestDeleteTool:
    """Test suite for tool deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_tool_success(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test successful tool deletion.

        GIVEN: Tool exists in database and is not in use
        WHEN: delete_tool is called with tool ID
        THEN: Tool is deleted and True is returned
        """
        # Act
        result = await tool_service.delete_tool(db_session, existing_tool.id)

        # Assert - verify deletion
        assert result is True
        deleted = await tool_service.get_tool(db_session, existing_tool.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_tool_not_found(
        self,
        db_session: AsyncSession,
        tool_service,
    ):
        """Test deleting non-existent tool.

        GIVEN: No tool with given ID exists
        WHEN: delete_tool is called with that ID
        THEN: False is returned
        """
        # Arrange
        non_existent_id = uuid4()

        # Act
        result = await tool_service.delete_tool(db_session, non_existent_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_tool_in_use_raises_error(
        self,
        db_session: AsyncSession,
        tool_service,
        existing_tool: ToolModel,
    ):
        """Test deleting tool that is in use fails.

        GIVEN: Tool is referenced by agents or workflows
        WHEN: delete_tool is called
        THEN: Error is raised or False returned
        """
        # Note: This test will need implementation after relationship tracking is added
        # For now, we'll skip or mark as xfail
        pytest.skip("TODO: Implement after relationship tracking is added")
