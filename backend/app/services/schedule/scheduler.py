"""
Persistent Scheduler Wrapper for APScheduler

TAG: SPEC-013-TASK-005-001
REQ: REQ-013-006 (AsyncIOScheduler Configuration)
REQ: REQ-013-007 (PostgreSQL Job Store Persistence)
REQ: REQ-013-008 (Scheduler Lifecycle Management)

이 모듈은 APScheduler AsyncIOScheduler 래퍼를 제공합니다.
PostgreSQL job store를 사용하여 스케줄을 영구적으로 저장합니다.
"""

import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel

from app.services.schedule.triggers import build_cron_trigger

logger = logging.getLogger(__name__)


class SchedulerConfig(BaseModel):
    """스케줄러 설정 모델

    TAG: SPEC-013-TASK-005-CONFIG-001
    """

    db_url: str = "postgresql://paste_trader:password@localhost:5432/paste_trader"
    timezone: str = "UTC"
    job_defaults_coalesce: bool = True
    job_defaults_max_instances: int = 1


class PersistentScheduler:
    """
    APScheduler AsyncIOScheduler 래퍼 클래스

    TAG: SPEC-013-TASK-005-CLASS-001
    REQ: REQ-013-006, REQ-013-007, REQ-013-008

    PostgreSQL job store를 사용하여 스케줄을 영구적으로 저장합니다.

    Attributes:
        scheduler: APScheduler AsyncIOScheduler 인스턴스
        is_running: 스케줄러 실행 상태

    Examples:
        >>> scheduler = PersistentScheduler()
        >>> await scheduler.start()
        >>> await scheduler.add_cron_job(
        ...     job_func=my_function,
        ...     trigger_args={"hour": 10, "minute": 30},
        ...     job_id="daily_job",
        ...     name="Daily Job",
        ... )
        >>> await scheduler.shutdown()
    """

    def __init__(
        self,
        db_url: str | None = None,
        timezone: str | None = None,
        use_sqlite: bool = False,
        sqlite_path: str | None = None,
    ):
        """
        PersistentScheduler 초기화

        TAG: SPEC-013-TASK-005-INIT-001

        Args:
            db_url: 데이터베이스 URL (기본값: PostgreSQL 설정)
            timezone: 시간대 (기본값: UTC)
            use_sqlite: SQLite job store 사용 여부 (테스트용)
            sqlite_path: SQLite 데이터베이스 파일 경로 (테스트용)
        """
        import os
        import tempfile

        self._config = SchedulerConfig(
            db_url=db_url
            or "postgresql://paste_trader:password@localhost:5432/paste_trader",
            timezone=timezone or "UTC",
        )

        # 테스트 환경에서 SQLite 사용
        if use_sqlite or os.getenv("TESTING") == "1":
            # 각 인스턴스마다 고유한 임시 파일 사용
            if sqlite_path is None:
                fd, sqlite_path = tempfile.mkstemp(suffix=".sqlite")
                os.close(fd)
            jobstores = {
                "default": SQLAlchemyJobStore(url=f"sqlite:///{sqlite_path}"),
            }
        else:
            # PostgreSQL job store 설정
            # APScheduler 제한사항: 동기 드라이버만 지원
            jobstore_url = self._convert_to_sync_url(self._config.db_url)

            jobstores = {
                "default": SQLAlchemyJobStore(url=jobstore_url),
            }

        # 스케줄러 초기화
        self.scheduler = AsyncIOScheduler(
            timezone=self._config.timezone,
            jobstores=jobstores,
            job_defaults={
                "coalesce": self._config.job_defaults_coalesce,
                "max_instances": self._config.job_defaults_max_instances,
            },
        )

        self.is_running = False

    def _convert_to_sync_url(self, async_url: str) -> str:
        """
        비동기 DB URL을 동기 URL로 변환합니다.

        TAG: SPEC-013-TASK-005-FUNC-001

        APScheduler는 동기 드라이버만 지원하므로 URL을 변환해야 합니다.

        Args:
            async_url: 비동기 DB URL (예: postgresql+asyncpg://...)

        Returns:
            str: 동기 DB URL (예: postgresql+psycopg2://...)
        """
        # postgresql+asyncpg:// -> postgresql+psycopg2://
        if "postgresql+asyncpg://" in async_url:
            return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        # postgresql:// -> postgresql+psycopg2://
        if "postgresql://" in async_url and "+" not in async_url:
            return async_url.replace("postgresql://", "postgresql+psycopg2://")
        return async_url

    async def start(self) -> None:
        """
        스케줄러를 시작합니다.

        TAG: SPEC-013-TASK-005-FUNC-002
        REQ: REQ-013-008 (Scheduler Lifecycle Management)

        이미 실행 중인 경우 아무것도 하지 않습니다.
        """
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("PersistentScheduler started")

    async def shutdown(self, wait: bool = True) -> None:
        """
        스케줄러를 종료합니다.

        TAG: SPEC-013-TASK-005-FUNC-003
        REQ: REQ-013-008 (Scheduler Lifecycle Management)

        Args:
            wait: 실행 중인 작업을 완료할 때까지 대기 여부
        """
        if self.is_running:
            self.scheduler.shutdown(wait=wait)
            self.is_running = False
            logger.info("PersistentScheduler shutdown")

    async def add_cron_job(
        self,
        job_func: Callable[..., Any],
        trigger_args: dict[str, Any],
        job_id: str,
        name: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Cron 트리거 기반 작업을 추가합니다.

        TAG: SPEC-013-TASK-005-FUNC-004
        REQ: REQ-013-006 (AsyncIOScheduler Configuration)

        Args:
            job_func: 실행할 함수
            trigger_args: cron 트리거 인자 (hour, minute, 등)
            job_id: 작업 ID
            name: 작업 이름
            **kwargs: 추가 작업 인자

        Returns:
            str: 추가된 작업 ID
        """
        trigger = build_cron_trigger(**trigger_args)

        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=name or job_id,
            **kwargs,
        )

        logger.info(f"Cron job added: {job_id}")
        return str(job.id)

    async def add_interval_job(
        self,
        job_func: Callable[..., Any],
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        weeks: int = 0,
        job_id: str | None = None,
        name: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Interval 트리거 기반 작업을 추가합니다.

        TAG: SPEC-013-TASK-005-FUNC-005
        REQ: REQ-013-006 (AsyncIOScheduler Configuration)

        Args:
            job_func: 실행할 함수
            seconds: 초 단위 간격
            minutes: 분 단위 간격
            hours: 시간 단위 간격
            days: 일 단위 간격
            weeks: 주 단위 간격
            job_id: 작업 ID
            name: 작업 이름
            **kwargs: 추가 작업 인자

        Returns:
            str: 추가된 작업 ID
        """
        trigger = IntervalTrigger(
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            days=days,
            weeks=weeks,
        )

        job = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=name or job_id,
            **kwargs,
        )

        logger.info(f"Interval job added: {job.id}")
        return str(job.id)

    async def remove_job(self, job_id: str) -> bool:
        """
        작업을 제거합니다.

        TAG: SPEC-013-TASK-005-FUNC-006

        Args:
            job_id: 제거할 작업 ID

        Returns:
            bool: 제거 성공 여부
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job removed: {job_id}")
            return True
        except Exception:
            logger.warning(f"Failed to remove job: {job_id}")
            return False

    async def pause_job(self, job_id: str) -> bool:
        """
        작업을 일시정지합니다.

        TAG: SPEC-013-TASK-005-FUNC-007

        Args:
            job_id: 일시정지할 작업 ID

        Returns:
            bool: 일시정지 성공 여부
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Job paused: {job_id}")
                return True
            return False
        except Exception:
            logger.warning(f"Failed to pause job: {job_id}")
            return False

    async def resume_job(self, job_id: str) -> bool:
        """
        일시정지된 작업을 재개합니다.

        TAG: SPEC-013-TASK-005-FUNC-008

        Args:
            job_id: 재개할 작업 ID

        Returns:
            bool: 재개 성공 여부
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Job resumed: {job_id}")
                return True
            return False
        except Exception:
            logger.warning(f"Failed to resume job: {job_id}")
            return False

    async def get_job(self, job_id: str) -> Any | None:
        """
        작업을 조회합니다.

        TAG: SPEC-013-TASK-005-FUNC-009

        Args:
            job_id: 조회할 작업 ID

        Returns:
            Job: APScheduler Job 객체 또는 None
        """
        try:
            return self.scheduler.get_job(job_id)
        except Exception:
            return None

    async def get_all_jobs(self) -> list[Any]:
        """
        모든 작업을 조회합니다.

        TAG: SPEC-013-TASK-005-FUNC-010

        Returns:
            list[Job]: APScheduler Job 객체 리스트
        """
        jobs = self.scheduler.get_jobs()
        return list(jobs) if jobs is not None else []

    async def get_next_run_time(self, job_id: str) -> datetime | None:
        """
        작업의 다음 실행 시간을 조회합니다.

        TAG: SPEC-013-TASK-005-FUNC-011

        Args:
            job_id: 조회할 작업 ID

        Returns:
            datetime: 다음 실행 시간 또는 None
        """
        job = await self.get_job(job_id)
        if job:
            # Cast to datetime to satisfy mypy
            return datetime.fromtimestamp(job.next_run_time.timestamp(), tz=UTC)
        return None


# Singleton 인스턴스
# TAG: SPEC-013-TASK-005-SINGLETON-001

# 테스트 환경에서는 SQLite를 사용
persistent_scheduler = PersistentScheduler(use_sqlite=os.getenv("TESTING") == "1")
