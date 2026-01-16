"""Unit tests for ScheduleHistory model.

TAG: [SPEC-013] [SCHEDULE_HISTORY] [MODEL] [TEST]
REQ: REQ-013-011 - Schedule History Tracking

This module contains comprehensive tests for the ScheduleHistory model
following TDD RED-GREEN-REFACTOR cycle.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExecutionHistoryStatus
from app.models.schedule import Schedule, ScheduleHistory
from app.models.user import User
from app.models.workflow import Workflow


class TestScheduleHistoryModel:
    """Test ScheduleHistory model attributes and constraints."""

    async def test_schedule_history_creation(self, db_session: AsyncSession) -> None:
        """ScheduleHistory 모델이 성공적으로 생성되어야 함."""
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
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create ScheduleHistory
        triggered_at = datetime.now(UTC)
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=triggered_at,
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=1500,
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        # Verify creation
        await db_session.refresh(history)

        assert history.id is not None
        assert history.schedule_id == schedule.id
        assert history.status == ExecutionHistoryStatus.COMPLETED
        assert history.duration_ms == 1500
        assert history.error_message is None
        # SQLite doesn't preserve timezone info, compare naive datetime
        assert history.triggered_at.replace(tzinfo=None) == triggered_at.replace(tzinfo=None)

    async def test_schedule_history_with_error(self, db_session: AsyncSession) -> None:
        """실패한 스케줄 실행의 히스토리가 에러 메시지를 저장해야 함."""
        # Create User, Workflow, Schedule
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create ScheduleHistory with error
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.FAILED,
            duration_ms=500,
            error_message="Workflow execution failed: Timeout exceeded",
        )
        db_session.add(history)
        await db_session.flush()

        # Verify error was saved
        await db_session.refresh(history)

        assert history.status == ExecutionHistoryStatus.FAILED
        assert history.error_message == "Workflow execution failed: Timeout exceeded"
        assert history.duration_ms == 500

    async def test_schedule_history_status_enum(
        self,
        db_session: AsyncSession,
    ) -> None:
        """모든 ExecutionHistoryStatus 상태가 저장되어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="interval",
            schedule_config={"hours": 1},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Test all status values
        statuses = [
            ExecutionHistoryStatus.PENDING,
            ExecutionHistoryStatus.RUNNING,
            ExecutionHistoryStatus.COMPLETED,
            ExecutionHistoryStatus.FAILED,
        ]

        for status in statuses:
            history = ScheduleHistory(
                schedule_id=schedule.id,
                workflow_execution_id=uuid4(),
                triggered_at=datetime.now(UTC),
                status=status,
                duration_ms=1000,
                error_message=None,
            )
            db_session.add(history)
            await db_session.flush()

            await db_session.refresh(history)
            assert history.status == status

    async def test_schedule_history_duration_ms(
        self,
        db_session: AsyncSession,
    ) -> None:
        """duration_ms 필드가 정확히 저장되어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Test various duration values
        durations = [0, 100, 1500, 5000, 60000]

        for duration in durations:
            history = ScheduleHistory(
                schedule_id=schedule.id,
                workflow_execution_id=uuid4(),
                triggered_at=datetime.now(UTC),
                status=ExecutionHistoryStatus.COMPLETED,
                duration_ms=duration,
                error_message=None,
            )
            db_session.add(history)
            await db_session.flush()

            await db_session.refresh(history)
            assert history.duration_ms == duration


class TestScheduleHistoryRelationships:
    """Test ScheduleHistory model relationships."""

    async def test_schedule_history_belongs_to_schedule(
        self,
        db_session: AsyncSession,
    ) -> None:
        """ScheduleHistory가 Schedule과 관계를 맺어야 함."""
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
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create ScheduleHistory
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=1000,
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        # Refresh and check relationship
        await db_session.refresh(history, ["schedule"])

        assert history.schedule is not None
        assert history.schedule.id == schedule.id
        assert history.schedule.name == "Daily Schedule"

    async def test_schedule_has_multiple_histories(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Schedule은 여러 개의 ScheduleHistory를 가질 수 있어야 함."""
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
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create multiple ScheduleHistory entries
        histories = []
        for i in range(5):
            history = ScheduleHistory(
                schedule_id=schedule.id,
                workflow_execution_id=uuid4(),
                triggered_at=datetime.now(UTC),
                status=ExecutionHistoryStatus.COMPLETED,
                duration_ms=1000 + (i * 100),
                error_message=None,
            )
            db_session.add(history)
            histories.append(history)

        await db_session.flush()

        # Refresh schedule and check histories
        await db_session.refresh(schedule, ["histories"])

        assert len(schedule.histories) == 5


class TestScheduleHistoryProperties:
    """Test ScheduleHistory model properties and methods."""

    async def test_schedule_history_repr(self, db_session: AsyncSession) -> None:
        """__repr__ 메서드가 올바른 문자열을 반환해야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=1000,
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        repr_str = repr(history)
        assert "ScheduleHistory" in repr_str
        assert str(history.id) in repr_str

    async def test_schedule_history_timestamps(
        self,
        db_session: AsyncSession,
    ) -> None:
        """triggered_at 타임스탬프가 정확히 저장되어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Daily Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Test with specific timestamp
        test_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=test_time,
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=1000,
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        await db_session.refresh(history)
        # SQLite doesn't preserve timezone info, compare naive datetime
        assert history.triggered_at.replace(tzinfo=None) == test_time.replace(tzinfo=None)

    async def test_schedule_history_cascade_delete(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Schedule이 삭제되면 ScheduleHistory도 CASCADE로 삭제되어야 함."""
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
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create multiple ScheduleHistory entries
        history1 = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=1000,
            error_message=None,
        )
        history2 = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.FAILED,
            duration_ms=500,
            error_message="Test error",
        )
        db_session.add_all([history1, history2])
        await db_session.flush()
        await db_session.commit()

        # Store history IDs
        history1_id = history1.id
        history2_id = history2.id

        # Delete the schedule (hard delete for testing CASCADE)
        await db_session.delete(schedule)
        await db_session.commit()

        # Verify histories are also deleted
        from sqlalchemy import select

        result = await db_session.execute(
            select(ScheduleHistory).where(ScheduleHistory.id.in_([history1_id, history2_id]))
        )
        histories = result.scalars().all()

        assert len(histories) == 0

    async def test_schedule_history_zero_duration(
        self,
        db_session: AsyncSession,
    ) -> None:
        """duration_ms가 0일 수 있어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create history with zero duration
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.PENDING,
            duration_ms=0,
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        await db_session.refresh(history)
        assert history.duration_ms == 0

    async def test_schedule_history_large_duration(
        self,
        db_session: AsyncSession,
    ) -> None:
        """duration_ms가 큰 값을 저장할 수 있어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create history with large duration (1 hour)
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.COMPLETED,
            duration_ms=3600000,  # 1 hour
            error_message=None,
        )
        db_session.add(history)
        await db_session.flush()

        await db_session.refresh(history)
        assert history.duration_ms == 3600000

    async def test_schedule_history_long_error_message(
        self,
        db_session: AsyncSession,
    ) -> None:
        """긴 에러 메시지가 저장되어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="cron",
            schedule_config={"cron_expression": "0 9 * * *"},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create history with long error message
        long_error = "Error: " + "x" * 1000
        history = ScheduleHistory(
            schedule_id=schedule.id,
            workflow_execution_id=uuid4(),
            triggered_at=datetime.now(UTC),
            status=ExecutionHistoryStatus.FAILED,
            duration_ms=100,
            error_message=long_error,
        )
        db_session.add(history)
        await db_session.flush()

        await db_session.refresh(history)
        assert history.error_message == long_error
        assert len(history.error_message) > 1000

    async def test_schedule_history_all_statuses_have_histories(
        self,
        db_session: AsyncSession,
    ) -> None:
        """모든 상태에 대해 여러 히스토리를 생성할 수 있어야 함."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
        )
        db_session.add(user)
        await db_session.flush()

        workflow = Workflow(
            owner_id=user.id,
            name="Test Workflow",
            is_active=True,
        )
        db_session.add(workflow)
        await db_session.flush()

        schedule = Schedule(
            workflow_id=workflow.id,
            user_id=user.id,
            name="Test Schedule",
            schedule_type="interval",
            schedule_config={"hours": 1},
        )
        db_session.add(schedule)
        await db_session.flush()

        # Create histories with all statuses
        statuses = [
            ExecutionHistoryStatus.PENDING,
            ExecutionHistoryStatus.RUNNING,
            ExecutionHistoryStatus.COMPLETED,
            ExecutionHistoryStatus.FAILED,
            ExecutionHistoryStatus.PENDING,
            ExecutionHistoryStatus.COMPLETED,
        ]

        for i, status in enumerate(statuses):
            history = ScheduleHistory(
                schedule_id=schedule.id,
                workflow_execution_id=uuid4(),
                triggered_at=datetime.now(UTC),
                status=status,
                duration_ms=100 * (i + 1),
                error_message="Error" if status == ExecutionHistoryStatus.FAILED else None,
            )
            db_session.add(history)

        await db_session.flush()

        # Refresh and verify all histories were created
        await db_session.refresh(schedule, ["histories"])
        assert len(schedule.histories) == len(statuses)

        # Verify status distribution
        status_counts = {}
        for history in schedule.histories:
            status_counts[history.status] = status_counts.get(history.status, 0) + 1

        assert status_counts.get(ExecutionHistoryStatus.PENDING) == 2
        assert status_counts.get(ExecutionHistoryStatus.RUNNING) == 1
        assert status_counts.get(ExecutionHistoryStatus.COMPLETED) == 2
        assert status_counts.get(ExecutionHistoryStatus.FAILED) == 1
