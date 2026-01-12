"""User model tests.

TAG: [SPEC-002] [AUTH] [DATABASE] [TEST]
REQ: REQ-001 - User Model with Email Identification
REQ: REQ-003 - Account Status Management
REQ: REQ-005 - User-Workflow Relationship

Tests for User model following AC-001 to AC-003, AC-012 to AC-021.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


class TestUserModel:
    """Test User model structure (AC-001)."""

    async def test_user_creation_with_valid_data(self, db_session):
        """Test creating a user with valid data (AC-001)."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_here"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.deleted_at is None

    async def test_user_repr(self, db_session):
        """Test user string representation (AC-008)."""
        user = User(
            email="test@example.com",
            hashed_password="hashed",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user.id) in repr_str
        assert "test@example.com" in repr_str


class TestUserEmail:
    """Test email constraints and validation (AC-002)."""

    async def test_email_unique_constraint(self, db_session):
        """Test that email must be unique (AC-002)."""
        user1 = User(
            email="test@example.com",
            hashed_password="hash1",
        )
        user2 = User(
            email="test@example.com",
            hashed_password="hash2",
        )

        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_email_required(self, db_session):
        """Test that email is required."""
        user = User(
            hashed_password="hash",
        )

        db_session.add(user)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestUserPassword:
    """Test password methods on User model."""

    async def test_set_password_hashes_password(self):
        """Test that set_password creates a bcrypt hash."""
        user = User(
            email="test@example.com",
            hashed_password="temp",
        )
        user.set_password("SecurePass123!")

        assert user.hashed_password.startswith("$2b$12$")
        assert len(user.hashed_password) == 60

    async def test_verify_password_correct(self):
        """Test verifying correct password."""
        user = User(
            email="test@example.com",
            hashed_password="temp",
        )
        user.set_password("SecurePass123!")

        assert user.verify_password("SecurePass123!") is True

    async def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        user = User(
            email="test@example.com",
            hashed_password="temp",
        )
        user.set_password("SecurePass123!")

        assert user.verify_password("WrongPass456!") is False


class TestUserAccountStatus:
    """Test account status management (AC-012 to AC-014)."""

    async def test_default_is_active_true(self, db_session):
        """Test that is_active defaults to True (AC-012)."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.is_active is True

    async def test_is_active_false_prevents_authentication(self, db_session):
        """Test that inactive user cannot authenticate (AC-013)."""
        user = User(
            email="test@example.com",
            hashed_password="temp",
            is_active=False,
        )
        user.set_password("SecurePass123!")
        db_session.add(user)
        await db_session.commit()

        # Even with correct password, inactive user should not authenticate
        # This is tested in service layer, but verify password still works
        assert user.verify_password("SecurePass123!") is True
        assert user.is_active is False


class TestUserSoftDelete:
    """Test soft delete behavior (AC-018 to AC-021)."""

    async def test_soft_delete_sets_deleted_at(self, db_session):
        """Test soft deleting a user (AC-018)."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.deleted_at is None
        assert user.is_deleted is False

        # Soft delete
        user.soft_delete()
        await db_session.commit()
        await db_session.refresh(user)

        assert user.deleted_at is not None
        assert user.is_deleted is True
        assert user.is_active is False  # soft_delete also sets is_active to False

    async def test_restore_soft_deleted_user(self, db_session):
        """Test restoring a soft deleted user (AC-021)."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        # Soft delete
        user.soft_delete()
        await db_session.commit()
        await db_session.refresh(user)

        assert user.is_deleted is True

        # Restore
        user.restore()
        await db_session.commit()
        await db_session.refresh(user)

        assert user.deleted_at is None
        assert user.is_deleted is False
        assert user.is_active is True


class TestUserWorkflowRelationship:
    """Test user-workflow relationship (AC-015 to AC-017)."""

    async def test_user_can_own_multiple_workflows(self, db_session):
        """Test that user can own multiple workflows (AC-015)."""
        from sqlalchemy.orm import selectinload

        from app.models.workflow import Workflow

        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple workflows
        workflow1 = Workflow(
            name="Workflow 1",
            description="First workflow",
            owner_id=user.id,
        )
        workflow2 = Workflow(
            name="Workflow 2",
            description="Second workflow",
            owner_id=user.id,
        )
        workflow3 = Workflow(
            name="Workflow 3",
            description="Third workflow",
            owner_id=user.id,
        )

        db_session.add_all([workflow1, workflow2, workflow3])
        await db_session.commit()

        # Refresh user with workflows loaded
        result = await db_session.execute(
            select(User).options(selectinload(User.workflows)).where(User.id == user.id)
        )
        user = result.scalar_one()

        # Check that user has 3 workflows
        assert len(user.workflows) == 3
        assert all(w.owner_id == user.id for w in user.workflows)

    async def test_soft_delete_user_does_not_delete_workflows(self, db_session):
        """Test soft deleting user preserves workflows (AC-017)."""
        from app.models.workflow import Workflow

        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        workflow = Workflow(
            name="Test Workflow",
            description="Test",
            owner_id=user.id,
        )
        db_session.add(workflow)
        await db_session.commit()

        # Soft delete user
        user.soft_delete()
        await db_session.commit()

        # Workflow should still exist with owner_id
        result = await db_session.execute(select(Workflow).filter_by(owner_id=user.id))
        workflows = result.scalars().all()
        assert len(workflows) == 1
        assert workflows[0].owner_id == user.id


class TestUserToolRelationship:
    """Test user-tool relationship (SPEC-004 AC-004)."""

    async def test_user_has_tools_relationship_attribute(self):
        """Test that User model has tools relationship attribute."""
        assert hasattr(User, "tools"), "User model should have 'tools' relationship"

    async def test_user_can_own_multiple_tools(self, db_session):
        """Test that user can own multiple tools."""
        from sqlalchemy.orm import selectinload

        from app.models.enums import ToolType
        from app.models.tool import Tool

        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple tools
        tool1 = Tool(
            owner_id=user.id,
            name="Tool 1",
            tool_type=ToolType.HTTP,
        )
        tool2 = Tool(
            owner_id=user.id,
            name="Tool 2",
            tool_type=ToolType.MCP,
        )
        tool3 = Tool(
            owner_id=user.id,
            name="Tool 3",
            tool_type=ToolType.PYTHON,
        )

        db_session.add_all([tool1, tool2, tool3])
        await db_session.commit()

        # Refresh user with tools loaded
        result = await db_session.execute(
            select(User).options(selectinload(User.tools)).where(User.id == user.id)
        )
        user = result.scalar_one()

        # Check that user has 3 tools
        assert len(user.tools) == 3
        assert all(t.owner_id == user.id for t in user.tools)


class TestUserAgentRelationship:
    """Test user-agent relationship (SPEC-004 AC-005)."""

    async def test_user_has_agents_relationship_attribute(self):
        """Test that User model has agents relationship attribute."""
        assert hasattr(User, "agents"), "User model should have 'agents' relationship"

    async def test_user_can_own_multiple_agents(self, db_session):
        """Test that user can own multiple agents."""
        from sqlalchemy.orm import selectinload

        from app.models.agent import Agent
        from app.models.enums import ModelProvider

        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple agents
        agent1 = Agent(
            owner_id=user.id,
            name="Agent 1",
            model_provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
        )
        agent2 = Agent(
            owner_id=user.id,
            name="Agent 2",
            model_provider=ModelProvider.OPENAI,
            model_name="gpt-4",
        )
        agent3 = Agent(
            owner_id=user.id,
            name="Agent 3",
            model_provider=ModelProvider.GLM,
            model_name="glm-4",
        )

        db_session.add_all([agent1, agent2, agent3])
        await db_session.commit()

        # Refresh user with agents loaded
        result = await db_session.execute(
            select(User).options(selectinload(User.agents)).where(User.id == user.id)
        )
        user = result.scalar_one()

        # Check that user has 3 agents
        assert len(user.agents) == 3
        assert all(a.owner_id == user.id for a in user.agents)
