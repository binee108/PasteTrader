"""
Schedule Management Service

TAG: SPEC-013-TASK-005-INIT
REQ: REQ-013-006, REQ-013-007, REQ-013-008

이 서비스는 스케줄러 인프라를 제공합니다:
- PersistentScheduler: APScheduler 래퍼
- Trigger Builders: cron/interval 트리거 빌더
"""

# Import trigger builders (always available)
from app.services.schedule.triggers import (
    build_cron_trigger,
    build_interval_trigger,
    validate_cron_expression,
    validate_interval_seconds,
)

__all__ = [
    "build_cron_trigger",
    "build_interval_trigger",
    "validate_cron_expression",
    "validate_interval_seconds",
]

# Try to import scheduler (may fail if DB not configured)
try:
    from app.services.schedule.scheduler import (
        PersistentScheduler,  # noqa: F401
        persistent_scheduler,  # noqa: F401
    )

    __all__.extend(["PersistentScheduler", "persistent_scheduler"])
except ImportError:
    pass

# Try to import service (may fail if dependencies not available)
try:
    from app.services.schedule.service import ScheduleService  # noqa: F401

    __all__.append("ScheduleService")
except ImportError:
    pass
