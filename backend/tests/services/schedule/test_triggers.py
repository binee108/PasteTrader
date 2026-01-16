"""
Trigger Builders 테스트

TAG: SPEC-013-TASK-006-TEST-001
REQ: REQ-013-006 (AsyncIOScheduler Configuration)
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services.schedule.triggers import (
    build_cron_trigger,
    build_interval_trigger,
    validate_cron_expression,
    validate_interval_seconds,
)


class TestBuildCronTrigger:
    """cron 트리거 빌더 테스트"""

    def test_build_basic_cron_trigger(self):
        """기본 cron 트리거 생성 테스트"""
        trigger = build_cron_trigger(hour=10, minute=30)

        assert trigger is not None
        assert hasattr(trigger, "fields")
        # hour와 minute가 설정되었는지 확인
        hour_field = next(f for f in trigger.fields if f.name == "hour")
        minute_field = next(f for f in trigger.fields if f.name == "minute")
        assert hour_field.expressions[0].first == 10
        assert minute_field.expressions[0].first == 30

    def test_build_cron_trigger_with_all_fields(self):
        """모든 필드가 포함된 cron 트리거 생성 테스트"""
        trigger = build_cron_trigger(
            minute="*/5", hour="*", day="*", month="*", day_of_week="*"
        )

        assert trigger is not None
        # 5분마다 실행되는 트리거
        # AllExpression은 first 속성이 없으므로 step만 확인
        minute_field = next(f for f in trigger.fields if f.name == "minute")
        assert hasattr(minute_field.expressions[0], "step")
        assert minute_field.expressions[0].step == 5

    def test_build_cron_trigger_with_timezone(self):
        """시간대가 포함된 cron 트리거 생성 테스트"""
        kst = ZoneInfo("Asia/Seoul")
        trigger = build_cron_trigger(hour=10, minute=0, timezone=kst)

        assert trigger is not None
        assert trigger.timezone == kst

    def test_build_cron_trigger_with_start_date(self):
        """시작일이 포함된 cron 트리거 생성 테스트"""
        start_date = datetime(2026, 1, 20, 10, 0, 0)
        trigger = build_cron_trigger(hour=10, minute=0, start_date=start_date)

        assert trigger is not None
        # 시작일이 설정되었는지 확인
        assert trigger.start_date is not None

    def test_build_cron_trigger_with_end_date(self):
        """종료일이 포함된 cron 트리거 생성 테스트"""
        end_date = datetime(2026, 12, 31, 23, 59, 59)
        trigger = build_cron_trigger(hour=10, minute=0, end_date=end_date)

        assert trigger is not None
        assert trigger.end_date is not None


class TestBuildIntervalTrigger:
    """interval 트리거 빌더 테스트"""

    def test_build_basic_interval_trigger(self):
        """기본 interval 트리거 생성 테스트"""
        trigger = build_interval_trigger(seconds=60)

        assert trigger is not None
        assert trigger.interval == timedelta(seconds=60)

    def test_build_interval_trigger_with_minutes(self):
        """분 단위 interval 트리거 생성 테스트"""
        trigger = build_interval_trigger(minutes=5)

        assert trigger is not None
        assert trigger.interval == timedelta(minutes=5)

    def test_build_interval_trigger_with_hours(self):
        """시간 단위 interval 트리거 생성 테스트"""
        trigger = build_interval_trigger(hours=2)

        assert trigger is not None
        assert trigger.interval == timedelta(hours=2)

    def test_build_interval_trigger_with_combined_units(self):
        """복합 단위 interval 트리거 생성 테스트"""
        trigger = build_interval_trigger(hours=1, minutes=30, seconds=45)

        assert trigger is not None
        expected = timedelta(hours=1, minutes=30, seconds=45)
        assert trigger.interval == expected

    def test_build_interval_trigger_with_start_date(self):
        """시작일이 포함된 interval 트리거 생성 테스트"""
        start_date = datetime(2026, 1, 20, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
        trigger = build_interval_trigger(seconds=60, start_date=start_date)

        assert trigger is not None
        assert trigger.start_date == start_date

    def test_build_interval_trigger_with_end_date(self):
        """종료일이 포함된 interval 트리거 생성 테스트"""
        end_date = datetime(2026, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
        trigger = build_interval_trigger(seconds=60, end_date=end_date)

        assert trigger is not None
        assert trigger.end_date == end_date

    def test_build_interval_trigger_with_timezone(self):
        """시간대가 포함된 interval 트리거 생성 테스트"""
        kst = ZoneInfo("Asia/Seoul")
        trigger = build_interval_trigger(seconds=60, timezone=kst)

        assert trigger is not None
        assert trigger.timezone == kst


class TestValidateCronExpression:
    """cron 표현식 유효성 검사 테스트"""

    def test_valid_cron_expressions(self):
        """유효한 cron 표현식 테스트"""
        valid_cases = [
            {"hour": "10", "minute": "30"},
            {"hour": "*", "minute": "*/5"},
            {"hour": "0-12", "minute": "0"},
            {"hour": "*/2", "minute": "30"},
        ]

        for case in valid_cases:
            assert validate_cron_expression(**case) is True

    def test_invalid_cron_expressions(self):
        """유효하지 않은 cron 표현식 테스트"""
        invalid_cases = [
            {"hour": "25", "minute": "30"},  # invalid hour
            {"hour": "10", "minute": "70"},  # invalid minute
            {"hour": "abc", "minute": "30"},  # non-numeric
        ]

        for case in invalid_cases:
            assert validate_cron_expression(**case) is False

    def test_cron_expression_with_day_fields(self):
        """day 필드가 포함된 cron 표현식 테스트"""
        assert validate_cron_expression(day="1-15") is True
        assert validate_cron_expression(day_of_week="mon-fri") is True


class TestValidateIntervalSeconds:
    """interval 초 유효성 검사 테스트"""

    def test_valid_intervals(self):
        """유효한 interval 값 테스트"""
        valid_cases = [1, 30, 60, 300, 3600]

        for seconds in valid_cases:
            assert validate_interval_seconds(seconds) is True

    def test_invalid_intervals(self):
        """유효하지 않은 interval 값 테스트"""
        invalid_cases = [0, -1, -60, 0.5, "60"]

        for seconds in invalid_cases:
            assert validate_interval_seconds(seconds) is False

    def test_minimum_interval_boundary(self):
        """최소 interval 경계값 테스트"""
        # 1초는 유효해야 함
        assert validate_interval_seconds(1) is True
        # 0초는 유효하지 않음
        assert validate_interval_seconds(0) is False
