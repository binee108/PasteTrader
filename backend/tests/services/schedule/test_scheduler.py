"""
PersistentScheduler 테스트

TAG: SPEC-013-TASK-005-TEST-001
REQ: REQ-013-006, REQ-013-007, REQ-013-008
"""

from datetime import datetime

import pytest

from app.services.schedule.scheduler import PersistentScheduler
from app.services.schedule.triggers import build_cron_trigger


# 테스트용 더미 함수 (직렬화 가능)
async def dummy_job_func():
    """테스트용 더미 작업 함수"""


class TestPersistentSchedulerInit:
    """PersistentScheduler 초기화 테스트"""

    def test_init_with_defaults(self):
        """기본 설정으로 초기화 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)

        assert scheduler is not None
        assert scheduler.scheduler is not None
        assert scheduler.is_running is False

    def test_init_with_custom_config(self):
        """사용자 설정으로 초기화 테스트"""
        scheduler = PersistentScheduler(
            db_url="postgresql://user:pass@localhost/test",
            timezone="Asia/Seoul",
            use_sqlite=True,
        )

        assert scheduler is not None
        assert scheduler.is_running is False


class TestPersistentSchedulerLifecycle:
    """PersistentScheduler 라이프사이클 테스트"""

    @pytest.mark.asyncio
    async def test_start_scheduler(self):
        """스케줄러 시작 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        assert scheduler.is_running is True

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_scheduler(self):
        """스케줄러 종료 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()
        await scheduler.shutdown()

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """이미 실행 중일 때 시작 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        # 이미 실행 중인 상태에서 다시 시작해도 에러가 발생하지 않아야 함
        await scheduler.start()
        assert scheduler.is_running is True

        await scheduler.shutdown()


class TestPersistentSchedulerJobManagement:
    """PersistentScheduler 작업 관리 테스트"""

    @pytest.mark.asyncio
    async def test_add_cron_job(self):
        """cron 작업 추가 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        trigger = build_cron_trigger(hour=10, minute=30)
        job_id = await scheduler.add_cron_job(
            job_func=dummy_job_func,
            trigger_args={"hour": 10, "minute": 30},
            job_id="test_cron_job",
            name="Test Cron Job",
        )

        assert job_id == "test_cron_job"

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_add_interval_job(self):
        """interval 작업 추가 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        job_id = await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="test_interval_job",
            name="Test Interval Job",
        )

        assert job_id == "test_interval_job"

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_remove_job(self):
        """작업 제거 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        # 작업 추가
        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="job_to_remove",
            name="Job to Remove",
        )

        # 작업 제거
        result = await scheduler.remove_job("job_to_remove")
        assert result is True

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self):
        """작업 일시정지 및 재개 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        # 작업 추가
        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="job_to_pause",
            name="Job to Pause",
        )

        # 작업 일시정지
        pause_result = await scheduler.pause_job("job_to_pause")
        assert pause_result is True

        # 작업 재개
        resume_result = await scheduler.resume_job("job_to_pause")
        assert resume_result is True

        await scheduler.shutdown()


class TestPersistentSchedulerJobQuery:
    """PersistentScheduler 작업 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_job(self):
        """작업 조회 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="job_to_get",
            name="Job to Get",
        )

        job = await scheduler.get_job("job_to_get")
        assert job is not None
        assert job.id == "job_to_get"

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_all_jobs(self):
        """모든 작업 조회 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        # 여러 작업 추가
        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="job1",
            name="Job 1",
        )
        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=120,
            job_id="job2",
            name="Job 2",
        )

        jobs = await scheduler.get_all_jobs()
        assert len(jobs) >= 2

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_next_run_time(self):
        """다음 실행 시간 조회 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        await scheduler.add_interval_job(
            job_func=dummy_job_func,
            seconds=60,
            job_id="job_next_run",
            name="Job Next Run",
        )

        next_run_time = await scheduler.get_next_run_time("job_next_run")
        assert next_run_time is not None
        assert isinstance(next_run_time, datetime)

        await scheduler.shutdown()


class TestPersistentSchedulerEdgeCases:
    """PersistentScheduler 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self):
        """존재하지 않는 작업 제거 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        result = await scheduler.remove_job("nonexistent_job")
        assert result is False

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_pause_nonexistent_job(self):
        """존재하지 않는 작업 일시정지 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        result = await scheduler.pause_job("nonexistent_job")
        assert result is False

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_resume_nonexistent_job(self):
        """존재하지 않는 작업 재개 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        result = await scheduler.resume_job("nonexistent_job")
        assert result is False

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self):
        """존재하지 않는 작업 조회 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        job = await scheduler.get_job("nonexistent_job")
        assert job is None

        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_next_run_time_nonexistent_job(self):
        """존재하지 않는 작업의 다음 실행 시간 조회 테스트"""
        scheduler = PersistentScheduler(use_sqlite=True)
        await scheduler.start()

        next_run_time = await scheduler.get_next_run_time("nonexistent_job")
        assert next_run_time is None

        await scheduler.shutdown()
