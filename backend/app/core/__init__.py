"""Core application configuration and utilities.

This package contains core functionality including:
- Configuration management (config.py)
- Security utilities (security.py)
- Logging setup (logging.py)
"""

from app.core.config import settings
from app.core.security import (
    PasswordComplexityError,
    benchmark_hash_performance,
    hash_password,
    is_password_complex_enough,
    verify_password,
)

__all__ = [
    "PasswordComplexityError",
    "benchmark_hash_performance",
    "hash_password",
    "is_password_complex_enough",
    "settings",
    "verify_password",
]
