"""JWT token creation and validation utilities.

TAG: [SPEC-002] [AUTH] [JWT]
REQ: REQ-007 - JWT Token Authentication

This module provides JWT token generation and validation for user authentication.
Uses python-jose for JWT operations.

Features:
- JWT token generation with expiration
- Token validation and decoding
- Timing-safe token verification
- Configurable token expiration time
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTError as JoseJWTError

from app.core.config import settings


# JWT Configuration
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: Subject of the token (usually user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Examples:
        >>> token = create_access_token("user-123")
        >>> isinstance(token, str)
        True
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload if valid, None otherwise

    Examples:
        >>> token = create_access_token("user-123")
        >>> payload = decode_access_token(token)
        >>> payload["sub"]
        'user-123'
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        # Token has expired
        return None
    except (JWTError, JoseJWTError):
        # Invalid token
        return None


def verify_token(token: str) -> str | None:
    """Verify a JWT token and return the subject (user ID).

    Args:
        token: JWT token string to verify

    Returns:
        User ID (subject) if token is valid, None otherwise

    Examples:
        >>> token = create_access_token("user-123")
        >>> user_id = verify_token(token)
        >>> user_id
        'user-123'
        >>> verify_token("invalid-token")
        None
    """
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.get("sub")


__all__ = [
    "create_access_token",
    "decode_access_token",
    "verify_token",
]
