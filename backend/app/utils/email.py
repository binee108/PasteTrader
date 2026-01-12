"""Email validation and normalization utilities.

TAG: [SPEC-002] [AUTH] [EMAIL]
REQ: REQ-007 - Email Normalization

This module provides email validation and normalization functions
to ensure consistent email handling across the application.

Features:
- Email normalization (lowercase, trim whitespace)
- Email format validation using regex
- Support for common email formats (plus tags, dots, etc.)
"""

from __future__ import annotations

import re
from typing import Final


# Email validation regex pattern
# Supports: local@domain, local+tag@domain, first.last@domain.co.uk
EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def normalize_email(email: str | None) -> str:
    """Normalize email address for storage and comparison.

    This function performs the following normalizations:
    - Converts email to lowercase
    - Trims leading and trailing whitespace
    - Handles None/empty strings

    Args:
        email: Raw email address to normalize

    Returns:
        Normalized email address, or empty string if email is None/empty

    Examples:
        >>> normalize_email("Test@Example.COM")
        'test@example.com'
        >>> normalize_email("  test@example.com  ")
        'test@example.com'
        >>> normalize_email("user+tag@example.com")
        'user+tag@example.com'

    Note:
        This function preserves plus tags and dots in the local part,
        which are valid email characters according to RFC 5322.
    """
    if not email:
        return ""

    # Convert to lowercase
    email = email.lower()

    # Trim whitespace
    email = email.strip()

    return email


def is_valid_email_format(email: str | None) -> bool:
    """Validate email format using regex pattern.

    This function checks if the email matches the expected format
    but does not verify that the email address actually exists.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise

    Examples:
        >>> is_valid_email_format("user@example.com")
        True
        >>> is_valid_email_format("invalid-email")
        False
        >>> is_valid_email_format("user+tag@example.co.uk")
        True

    Note:
        This is a basic validation. For production use, consider:
        - Using email-validator library for more comprehensive validation
        - Verifying domain has MX records
        - Sending verification email to confirm ownership
    """
    if not email:
        return False

    # Use regex pattern to validate format
    return EMAIL_PATTERN.match(email) is not None


__all__ = [
    "normalize_email",
    "is_valid_email_format",
]
