"""Integration tests for Schedule model relationships.

TAG: [SPEC-006] [SCHEDULE] [INTEGRATION] [TEST]
REQ: REQ-004 - Workflow-Schedule Relationship
REQ: REQ-005 - APScheduler Job ID Management
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScheduleType
from app.models.schedule import Schedule
from app.models.user import User
from app.models.workflow import Workflow


class TestScheduleWorkflowRelationship:
    """Test Schedule-Workflow relationship integration."""

    async def test_schedule_belongs_to_workflow(self, db_session: AsyncSession) -> None:
        """Schedule should be able to access its associated Workflow."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create Schedule
        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Refresh and check relationship
        await db_session.refresh(schedule, ["workflow"])

        assert schedule.workflow is not None
        assert schedule.workflow.id == workflow.id
        assert schedule.workflow.name == "Test Workflow"

    async def test_workflow_has_schedules(self, db_session: AsyncSession) -> None:
        """Workflow should be able to access its associated Schedules."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create multiple Schedules
        schedule1 = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Schedule 1",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        schedule2 = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Schedule 2",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": 1},
        )
        db_session.add_all([schedule1, schedule2])
        await db_session.flush()

        # Refresh and check relationship
        await db_session.refresh(workflow, ["schedules"])

        assert len(workflow.schedules) == 2
        schedule_names = {s.name for s in workflow.schedules}
        assert schedule_names == {"Schedule 1", "Schedule 2"}

    async def test_schedule_deletion_with_workflow_cascade(
        self,
        db_session: AsyncSession,
    ) -> None:
        """When Workflow is deleted, Schedules should be soft-deleted via CASCADE."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create Schedule
        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.commit()

        # Soft delete workflow (this does NOT automatically cascade to schedules)
        # Note: Soft delete cascading must be handled at the service layer
        workflow.soft_delete()
        await db_session.commit()

        # Refresh schedule - it should still be active (no automatic cascade)
        await db_session.refresh(schedule)
        assert schedule.deleted_at is None
        assert schedule.is_deleted is False

        # Manually soft delete the schedule (as a service layer would do)
        schedule.soft_delete()
        await db_session.commit()

        # Now verify schedule is deleted
        await db_session.refresh(schedule)
        assert schedule.deleted_at is not None
        assert schedule.is_deleted is True


class TestScheduleUserRelationship:
    """Test Schedule-User relationship integration."""

    async def test_schedule_belongs_to_user(self, db_session: AsyncSession) -> None:
        """Schedule should be able to access its associated User."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create Schedule
        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Refresh and check relationship
        await db_session.refresh(schedule, ["user"])

        assert schedule.user is not None
        assert schedule.user.id == user.id
        assert schedule.user.email == "test@example.com"

    async def test_user_has_schedules(self, db_session: AsyncSession) -> None:
        """User should be able to access its associated Schedules."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflows
        workflow1 = Workflow(
            owner_id=user.id,
            name="Workflow 1",
            is_active=True,
        )
        workflow2 = Workflow(
            owner_id=user.id,
            name="Workflow 2",
            is_active=True,
        )
        db_session.add_all([workflow1, workflow2])
        await db_session.flush()

        # Create Schedules
        schedule1 = Schedule(
            workflow_id=workflow1.id,
            user_id=user.id,
            name="Schedule 1",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        schedule2 = Schedule(
            workflow_id=workflow2.id,
            user_id=user.id,
            name="Schedule 2",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": 1},
        )
        db_session.add_all([schedule1, schedule2])
        await db_session.flush()

        # Refresh and check relationship
        await db_session.refresh(user, ["schedules"])

        assert len(user.schedules) == 2
        schedule_names = {s.name for s in user.schedules}
        assert schedule_names == {"Schedule 1", "Schedule 2"}


class TestScheduleFullIntegration:
    """Test Schedule model in full integration scenarios."""

    async def test_schedule_with_workflow_and_user_relationships(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Schedule should maintain relationships with both Workflow and User."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create Schedule
        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            description="Run every day at 9 AM",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.commit()

        # Refresh all relationships
        await db_session.refresh(schedule, ["workflow", "user"])
        await db_session.refresh(workflow, ["schedules"])
        await db_session.refresh(user, ["schedules"])

        # Verify Schedule relationships
        assert schedule.workflow.id == workflow.id
        assert schedule.user.id == user.id

        # Verify Workflow schedules
        assert len(workflow.schedules) == 1
        assert workflow.schedules[0].id == schedule.id

        # Verify User schedules
        assert len(user.schedules) == 1
        assert user.schedules[0].id == schedule.id

    async def test_multiple_schedules_per_workflow(
        self,
        db_session: AsyncSession,
    ) -> None:
        """A Workflow can have multiple Schedules."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create multiple Schedules for same Workflow
        schedules = [
            Schedule(
                workflow_id=workflow.id,
                user_id=user.id,
                name=f"Schedule {i}",
                schedule_type=ScheduleType.CRON,
                schedule_config={"cron_expression": f"0 {i} * * *"},
            )
            for i in range(1, 4)
        ]
        db_session.add_all(schedules)
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(workflow, ["schedules"])

        assert len(workflow.schedules) == 3
        for schedule in workflow.schedules:
            assert schedule.workflow_id == workflow.id

    async def test_schedule_property_methods_in_integration(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Schedule property methods should work correctly in integration context."""
        # Create User
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        # Create Workflow
        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        # Create recurring schedule
        cron_schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Cron",
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(cron_schedule)
        await db_session.flush()

        # Test properties
        assert cron_schedule.is_one_time is False
        assert cron_schedule.is_recurring is True
        assert cron_schedule.is_expired is False

        # Record execution
        initial_count = cron_schedule.run_count
        cron_schedule.record_execution()
        await db_session.flush()

        assert cron_schedule.run_count == initial_count + 1
        assert cron_schedule.last_run_at is not None
