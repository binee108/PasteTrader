"""Unit tests for soft delete filtering (SPEC-001 REQ-008).

TAG: [SPEC-001] [TESTS] [SOFT_DELETE]
REQ: REQ-008 - Soft Delete Filtering Implementation

This test module verifies that services properly filter soft-deleted records
and respect the include_deleted parameter.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.agent import Agent
from app.models.tool import Tool
from app.models.workflow import Workflow
from app.services.workflow_service import WorkflowService


class TestWorkflowServiceSoftDelete:
    """Test suite for WorkflowService soft delete filtering."""

    @pytest.mark.asyncio
    async def test_get_excludes_soft_deleted_by_default(self, db_session):
        """Test that get() excludes soft-deleted workflows by default."""
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow.soft_delete()  # Mark as deleted

        db_session.add(workflow)
        await db_session.flush()

        result = await WorkflowService(db_session).get(workflow.id)

        # Should return None because soft-deleted records are excluded by default
        assert result is None

    @pytest.mark.asyncio
    async def test_get_includes_soft_deleted_when_flag_true(self, db_session):
        """Test that get() includes soft-deleted workflows when include_deleted=True."""
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow.soft_delete()  # Mark as deleted

        db_session.add(workflow)
        await db_session.flush()

        result = await WorkflowService(db_session).get(
            workflow.id, include_deleted=True
        )

        # Should return the workflow when include_deleted=True
        assert result is not None
        assert result.id == workflow.id
        assert result.deleted_at is not None

    @pytest.mark.asyncio
    async def test_get_with_nodes_excludes_soft_deleted_by_default(self, db_session):
        """Test that get_with_nodes() excludes soft-deleted workflows by default."""
        workflow = Workflow(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow.soft_delete()  # Mark as deleted

        db_session.add(workflow)
        await db_session.flush()

        with pytest.raises(Exception):  # WorkflowNotFoundError
            await WorkflowService(db_session).get_with_nodes(workflow.id)

    @pytest.mark.asyncio
    async def test_list_excludes_soft_deleted_by_default(self, db_session):
        """Test that list() excludes soft-deleted workflows by default."""
        owner_id = uuid4()
        workflow1 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Active Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Deleted Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2.soft_delete()  # Mark workflow2 as deleted

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        workflows = await WorkflowService(db_session).list(owner_id, skip=0, limit=10)

        # Should only return non-deleted workflows
        assert len(workflows) == 1
        assert workflows[0].name == "Active Workflow"

    @pytest.mark.asyncio
    async def test_list_includes_soft_deleted_when_flag_true(self, db_session):
        """Test that list() includes soft-deleted workflows when include_deleted=True."""
        owner_id = uuid4()
        workflow1 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Active Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Deleted Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2.soft_delete()  # Mark workflow2 as deleted

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        workflows = await WorkflowService(db_session).list(
            owner_id, skip=0, limit=10, include_deleted=True
        )

        # Should return all workflows including deleted ones
        assert len(workflows) == 2
        workflow_names = {w.name for w in workflows}
        assert "Active Workflow" in workflow_names
        assert "Deleted Workflow" in workflow_names

    @pytest.mark.asyncio
    async def test_count_excludes_soft_deleted_by_default(self, db_session):
        """Test that count() excludes soft-deleted workflows by default."""
        owner_id = uuid4()
        workflow1 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Active Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Deleted Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2.soft_delete()  # Mark workflow2 as deleted

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        count = await WorkflowService(db_session).count(owner_id)

        # Should only count non-deleted workflows
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_includes_soft_deleted_when_flag_true(self, db_session):
        """Test that count() includes soft-deleted workflows when include_deleted=True."""
        owner_id = uuid4()
        workflow1 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Active Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2 = Workflow(
            id=uuid4(),
            owner_id=owner_id,
            name="Deleted Workflow",
            description="Test",
            config={},
            variables={},
            is_active=True,
            version=1,
        )
        workflow2.soft_delete()  # Mark workflow2 as deleted

        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        count = await WorkflowService(db_session).count(owner_id, include_deleted=True)

        # Should count all workflows including deleted ones
        assert count == 2


class TestAgentModelSoftDelete:
    """Test suite for Agent model soft delete functionality."""

    @pytest.mark.asyncio
    async def test_agent_soft_delete_mixin(self, db_session):
        """Test that Agent model properly supports soft delete."""
        from app.models.enums import ModelProvider

        agent = Agent(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Agent",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-20241022",
            system_prompt="You are a helpful assistant",
            config={},
            tools=[],
            is_active=True,
            is_public=False,
        )

        # Initially not deleted
        assert agent.deleted_at is None
        assert agent.is_deleted is False

        # Soft delete the agent
        agent.soft_delete()

        # Verify soft delete
        assert agent.deleted_at is not None
        assert agent.is_deleted is True
        assert agent.is_active is False  # Should also set is_active to False

        # Restore the agent
        agent.restore()

        # Verify restoration
        assert agent.deleted_at is None
        assert agent.is_deleted is False
        # is_active may not be restored to True depending on implementation


class TestToolModelSoftDelete:
    """Test suite for Tool model soft delete functionality."""

    @pytest.mark.asyncio
    async def test_tool_soft_delete_mixin(self, db_session):
        """Test that Tool model properly supports soft delete."""
        from app.models.enums import ToolType

        tool = Tool(
            id=uuid4(),
            owner_id=uuid4(),
            name="Test Tool",
            tool_type=ToolType.HTTP,
            config={},
            input_schema={},
            output_schema=None,
            auth_config=None,
            rate_limit=None,
            is_active=True,
            is_public=False,
        )

        # Initially not deleted
        assert tool.deleted_at is None
        assert tool.is_deleted is False

        # Soft delete the tool
        tool.soft_delete()

        # Verify soft delete
        assert tool.deleted_at is not None
        assert tool.is_deleted is True
        assert tool.is_active is False  # Should also set is_active to False

        # Restore the tool
        tool.restore()

        # Verify restoration
        assert tool.deleted_at is None
        assert tool.is_deleted is False
        # is_active may not be restored to True depending on implementation
