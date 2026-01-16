"""
Trigger Builders for APScheduler

TAG: SPEC-013-TASK-006-001
REQ: REQ-013-006 (AsyncIOScheduler Configuration)

이 모듈은 APScheduler 트리거 생성을 위한 빌더 함수를 제공합니다.
"""

from datetime import datetime
from typing import Any

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from zoneinfo import ZoneInfo


def build_cron_trigger(
    hour: str | int | None = None,
    minute: str | int | None = None,
    second: str | int | None = None,
    day: str | None = None,
    month: str | None = None,
    day_of_week: str | None = None,
    timezone: ZoneInfo | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> CronTrigger:
    """
    Cron 트리거를 생성합니다.

    TAG: SPEC-013-TASK-006-FUNC-001
    REQ: REQ-013-006

    Args:
        hour: 시간 (0-23)
        minute: 분 (0-59)
        second: 초 (0-59)
        day: 일 (1-31)
        month: 월 (1-12)
        day_of_week: 요일 (0-6, mon-fri)
        timezone: 시간대
        start_date: 시작일
        end_date: 종료일

    Returns:
        CronTrigger: APScheduler CronTrigger 인스턴스

    Examples:
        >>> # 매일 10시 30분에 실행
        >>> trigger = build_cron_trigger(hour=10, minute=30)

        >>> # 5분마다 실행
        >>> trigger = build_cron_trigger(minute="*/5")

        >>> # 매일 자정에 실행 (KST)
        >>> kst = ZoneInfo("Asia/Seoul")
        >>> trigger = build_cron_trigger(hour=0, minute=0, timezone=kst)
    """
    trigger_args: dict[str, Any] = {}

    if hour is not None:
        trigger_args["hour"] = hour
    if minute is not None:
        trigger_args["minute"] = minute
    if second is not None:
        trigger_args["second"] = second
    if day is not None:
        trigger_args["day"] = day
    if month is not None:
        trigger_args["month"] = month
    if day_of_week is not None:
        trigger_args["day_of_week"] = day_of_week
    if timezone is not None:
        trigger_args["timezone"] = timezone
    if start_date is not None:
        trigger_args["start_date"] = start_date
    if end_date is not None:
        trigger_args["end_date"] = end_date

    return CronTrigger(**trigger_args)


def build_interval_trigger(
    seconds: int = 0,
    minutes: int = 0,
    hours: int = 0,
    days: int = 0,
    weeks: int = 0,
    timezone: ZoneInfo | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> IntervalTrigger:
    """
    Interval 트리거를 생성합니다.

    TAG: SPEC-013-TASK-006-FUNC-002
    REQ: REQ-013-006

    Args:
        seconds: 초 단위 간격
        minutes: 분 단위 간격
        hours: 시간 단위 간격
        days: 일 단위 간격
        weeks: 주 단위 간격
        timezone: 시간대
        start_date: 시작일
        end_date: 종료일

    Returns:
        IntervalTrigger: APScheduler IntervalTrigger 인스턴스

    Examples:
        >>> # 60초마다 실행
        >>> trigger = build_interval_trigger(seconds=60)

        >>> # 5분마다 실행
        >>> trigger = build_interval_trigger(minutes=5)

        >>> # 2시간마다 실행
        >>> trigger = build_interval_trigger(hours=2)

        >>> # 1시간 30분 45초마다 실행
        >>> trigger = build_interval_trigger(hours=1, minutes=30, seconds=45)
    """
    trigger_args: dict[str, Any] = {
        "seconds": seconds,
        "minutes": minutes,
        "hours": hours,
        "days": days,
        "weeks": weeks,
    }

    if timezone is not None:
        trigger_args["timezone"] = timezone
    if start_date is not None:
        trigger_args["start_date"] = start_date
    if end_date is not None:
        trigger_args["end_date"] = end_date

    return IntervalTrigger(**trigger_args)


def validate_cron_expression(**kwargs: Any) -> bool:
    """
    Cron 표현식의 유효성을 검사합니다.

    TAG: SPEC-013-TASK-006-FUNC-003
    REQ: REQ-013-006

    Args:
        **kwargs: cron 필드 (hour, minute, second, day, month, day_of_week)

    Returns:
        bool: 유효하면 True, 그렇지 않으면 False

    Examples:
        >>> validate_cron_expression(hour="10", minute="30")
        True

        >>> validate_cron_expression(hour="25", minute="30")  # invalid hour
        False
    """
    try:
        # CronTrigger를 생성하여 유효성 검사
        CronTrigger(**kwargs)
        return True
    except (ValueError, TypeError):
        return False


def validate_interval_seconds(seconds: int) -> bool:
    """
    Interval 초 값의 유효성을 검사합니다.

    TAG: SPEC-013-TASK-006-FUNC-004
    REQ: REQ-013-006

    Args:
        seconds: 초 단위 간격

    Returns:
        bool: 유효하면 True, 그렇지 않으면 False

    Examples:
        >>> validate_interval_seconds(60)
        True

        >>> validate_interval_seconds(0)  # 0은 유효하지 않음
        False

        >>> validate_interval_seconds(-1)  # 음수는 유효하지 않음
        False
    """
    # 정수이고 0보다 커야 함
    if not isinstance(seconds, int):
        return False
    return seconds > 0
