"""Schedule service test configuration - Minimal fixtures for scheduler testing.

TAG: SPEC-013-TASK-005-TEST-CONF
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def sample_cron_config():
    """Sample cron configuration for testing."""
    return {
        "hour": 10,
        "minute": 30,
    }


@pytest.fixture
def sample_interval_config():
    """Sample interval configuration for testing."""
    return {
        "seconds": 60,
    }


@pytest.fixture
def kst_timezone():
    """KST timezone fixture for testing."""
    return ZoneInfo("Asia/Seoul")


@pytest.fixture
def utc_timezone():
    """UTC timezone fixture for testing."""
    return ZoneInfo("UTC")


@pytest.fixture
def future_start_date():
    """Future start date for testing."""
    return datetime(2026, 1, 20, 10, 0, 0, tzinfo=ZoneInfo("UTC"))


@pytest.fixture
def future_end_date():
    """Future end date for testing."""
    return datetime(2026, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
