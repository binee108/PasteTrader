"""Password hashing and verification utilities.

TAG: [SPEC-002] [AUTH] [SECURITY]
REQ: REQ-002 - Password Hashing
REQ: REQ-004 - Password Validation
REQ: REQ-006 - Password Verification

This module provides secure password hashing using bcrypt with cost factor 12,
following security best practices for authentication systems.

Features:
- Bcrypt password hashing with automatic salt generation
- Timing-safe password verification to prevent timing attacks
- Password complexity validation
- Performance-optimized implementation (completes within 500ms)
- Comprehensive security event logging

Logging:
    - Logs password hashing operations (without sensitive data)
    - Logs password verification operations
    - Logs security violation attempts
    - Logs password complexity validation failures
"""

from __future__ import annotations

import re
from time import perf_counter

# Fix compatibility between passlib 1.7.4 and bcrypt 4.x
# bcrypt 4.x removed __about__ attribute, add a workaround
import bcrypt

if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.1.3")
    bcrypt.__about__ = _About()  # type: ignore[attr-defined]

from passlib.context import CryptContext  # type: ignore[import-untyped]


class PasswordComplexityError(ValueError):
    """Exception raised when password does not meet complexity requirements."""

    def __init__(
        self, message: str = "Password does not meet complexity requirements"
    ) -> None:
        """Initialize password complexity error.

        Args:
            message: Error message describing the complexity requirements
        """
        self.message = message
        super().__init__(self.message)


# Bcrypt configuration with cost factor 12
# Cost factor 12 provides good security vs performance balance
# Each increment doubles the hashing time
BCRYPT_ROUNDS = 12
BCRYPT_SALT_PREFIX = b"$2b$12$"


def _prepare_password(password: str) -> bytes:
    """Prepare password for bcrypt hashing.

    Bcrypt has a 72-byte limit on password length. This function
    truncates passwords longer than 72 bytes before encoding.

    Args:
        password: Plain text password to prepare

    Returns:
        Password bytes truncated to 72 bytes if necessary
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return password_bytes


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12.

    This function uses bcrypt with a cost factor of 12, which provides
    a good balance between security and performance. Each hash uses a
    unique salt, so the same password will produce different hashes.

    Note:
        Bcrypt has a 72-byte limit on password length. Passwords longer
        than 72 bytes are automatically truncated to 72 bytes before hashing.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hash string (60 characters, starts with $2b$12$)

    Examples:
        >>> hashed = hash_password("SecurePass123!")
        >>> hashed.startswith("$2b$12$")
        True
        >>> len(hashed)
        60

    Performance:
        Completes within 500ms on modern hardware (AC-031)

    Logging:
        Logs password hashing operations without exposing sensitive data
    """
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    # Log password hashing operation (without sensitive data)
    password_length = len(password)
    truncated = len(password.encode("utf-8")) > 72

    logger.debug(
        "Password hashing operation",
        extra={
            "context": {
                "action": "hash_password",
                "password_length": password_length,
                "truncated": truncated,
            }
        },
    )

    # Prepare password (truncate to 72 bytes if necessary)
    password_bytes = _prepare_password(password)

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    hashed: str = hashed_bytes.decode("utf-8")

    logger.info(
        "Password hashed successfully",
        extra={
            "context": {
                "action": "hash_password",
                "hash_prefix": hashed[:7],  # Only log algorithm identifier
                "hash_length": len(hashed),
                "status": "success",
            }
        },
    )

    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.

    This function uses timing-safe comparison to prevent timing attacks.
    The verification time is consistent regardless of whether the password
    is correct or incorrect, preventing attackers from guessing passwords
    based on timing information.

    Note:
        Bcrypt has a 72-byte limit on password length. Passwords longer
        than 72 bytes are automatically truncated to 72 bytes before verification.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored bcrypt hash to compare against

    Returns:
        True if password matches, False otherwise

    Examples:
        >>> hashed = hash_password("SecurePass123!")
        >>> verify_password("SecurePass123!", hashed)
        True
        >>> verify_password("WrongPass456!", hashed)
        False

    Security:
        - Uses timing-safe comparison (AC-030)
        - Prevents timing attack vectors
        - Returns False for invalid hash formats

    Performance:
        Completes within 500ms on modern hardware (AC-031)

    Logging:
        Logs password verification operations without exposing sensitive data
    """
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    # Log password verification operation (without sensitive data)
    password_length = len(plain_password)
    truncated = len(plain_password.encode("utf-8")) > 72

    # Validate hash format
    valid_hash_format = (
        hashed_password.startswith("$2b$12$") if hashed_password else False
    )

    logger.debug(
        "Password verification operation",
        extra={
            "context": {
                "action": "verify_password",
                "password_length": password_length,
                "truncated": truncated,
                "valid_hash_format": valid_hash_format,
            }
        },
    )

    try:
        # Prepare password (truncate to 72 bytes if necessary)
        password_bytes = _prepare_password(plain_password)
        hashed_bytes = hashed_password.encode("utf-8")

        # Use bcrypt's timing-safe verify
        result: bool = bcrypt.checkpw(password_bytes, hashed_bytes)

        logger.info(
            "Password verification completed",
            extra={
                "context": {
                    "action": "verify_password",
                    "result": result,
                    "status": "success",
                }
            },
        )

        return result
    except Exception as e:
        # Log verification error (security event)
        logger.warning(
            "Password verification failed with exception",
            extra={
                "context": {
                    "action": "verify_password",
                    "error_type": type(e).__name__,
                    "status": "failed",
                }
            },
        )
        # Return False for any error (invalid hash format, etc.)
        # This prevents information leakage about password validity
        return False


def is_password_complex_enough(
    password: str,
    min_length: int = 8,
    raise_error: bool = False,
) -> bool:
    """Validate password complexity requirements.

    This function checks if a password meets the following requirements:
    - Minimum length (default: 8 characters)
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one number
    - At least one special character

    Args:
        password: Password to validate
        min_length: Minimum required length (default: 8)
        raise_error: If True, raises PasswordComplexityError on failure

    Returns:
        True if password meets complexity requirements, False otherwise

    Raises:
        PasswordComplexityError: If raise_error=True and validation fails

    Examples:
        >>> is_password_complex_enough("SecurePass123!")
        True
        >>> is_password_complex_enough("short")
        False
        >>> is_password_complex_enough("short", raise_error=True)
        Traceback (most recent call last):
            ...
        PasswordComplexityError

    Note:
        This is a basic implementation. For production use, consider:
        - Checking against common password dictionaries
        - Preventing sequential/repeated characters
        - Checking for personal information (email, name, etc.)

    Logging:
        Logs password complexity validation failures for security monitoring
    """
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    errors = []
    password_length = len(password)

    # Check minimum length
    if password_length < min_length:
        errors.append(f"at least {min_length} characters")

    # Check for lowercase letter
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")

    # Check for uppercase letter
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")

    # Check for number
    if not re.search(r"\d", password):
        errors.append("at least one number")

    # Check for special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("at least one special character")

    if errors:
        # Log password complexity validation failure
        logger.warning(
            "Password complexity validation failed",
            extra={
                "context": {
                    "action": "password_complexity_check",
                    "status": "failed",
                    "password_length": password_length,
                    "required_length": min_length,
                    "missing_requirements": len(errors),
                }
            },
        )

        if raise_error:
            error_msg = f"Password must contain {', '.join(errors)}"
            raise PasswordComplexityError(error_msg)
        return False

    logger.debug(
        "Password complexity validation passed",
        extra={
            "context": {
                "action": "password_complexity_check",
                "status": "passed",
                "password_length": password_length,
            }
        },
    )

    return True


def benchmark_hash_performance(iterations: int = 10) -> dict[str, float]:
    """Benchmark password hashing and verification performance.

    This function is useful for verifying that password operations
    complete within acceptable time limits (AC-031: < 500ms).

    Args:
        iterations: Number of iterations to run (default: 10)

    Returns:
        Dictionary with performance metrics:
        'hash_mean', 'hash_max', 'verify_mean', 'verify_max' (seconds)

    Examples:
        >>> stats = benchmark_hash_performance(10)
        >>> stats['hash_mean'] < 0.5  # Should be under 500ms
        True
        >>> stats['verify_mean'] < 0.5
        True
    """
    test_password = "BenchmarkPass123!"
    test_hash = hash_password(test_password)

    hash_times = []
    verify_times = []

    for _ in range(iterations):
        # Benchmark hashing
        start = perf_counter()
        hash_password(test_password)
        hash_times.append(perf_counter() - start)

        # Benchmark verification
        start = perf_counter()
        verify_password(test_password, test_hash)
        verify_times.append(perf_counter() - start)

    return {
        "hash_mean": sum(hash_times) / len(hash_times),
        "hash_max": max(hash_times),
        "verify_mean": sum(verify_times) / len(verify_times),
        "verify_max": max(verify_times),
    }


__all__ = [
    "PasswordComplexityError",
    "benchmark_hash_performance",
    "hash_password",
    "is_password_complex_enough",
    "verify_password",
]
