"""Tests for API dependencies module.

Tests JWT authentication dependencies including get_current_user and
get_current_user_optional functions.

TAG: [SPEC-009] [AUTH] [JWT] [TEST]
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    CurrentUserOptional,
    get_current_user,
    get_current_user_optional,
)
from app.core.jwt import create_access_token
from app.models.user import User


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password_here",
    )
    return user


@pytest.fixture
def valid_token(mock_user: User) -> str:
    """Create a valid JWT token for testing."""
    return create_access_token(subject=str(mock_user.id))


@pytest.fixture
def expired_token() -> str:
    """Create an expired JWT token for testing."""
    from datetime import timedelta

    # Create a token that's already expired
    return create_access_token(
        subject=str(uuid4()),
        expires_delta=timedelta(seconds=-1),  # Expired 1 second ago
    )


@pytest.fixture
def invalid_token() -> str:
    """Create an invalid JWT token for testing."""
    return "invalid.token.here"


@pytest.fixture
def mock_db_session(mock_user: User) -> AsyncMock:
    """Create a mock database session that returns a user."""
    session = AsyncMock(spec=AsyncSession)

    # Mock execute to return our user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = mock_result

    return session


# =============================================================================
# get_current_user_optional Tests
# =============================================================================


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    async def test_no_authorization_header_returns_none(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that missing Authorization header returns None."""
        result = await get_current_user_optional(
            db=mock_db_session,
            authorization=None,
        )

        assert result is None
        mock_db_session.execute.assert_not_awaited()

    async def test_valid_token_returns_user(
        self,
        mock_db_session: AsyncMock,
        mock_user: User,
        valid_token: str,
    ) -> None:
        """Test that valid token returns the user."""
        authorization = f"Bearer {valid_token}"

        result = await get_current_user_optional(
            db=mock_db_session,
            authorization=authorization,
        )

        assert result is not None
        assert result.id == mock_user.id
        assert result.email == mock_user.email
        mock_db_session.execute.assert_awaited_once()

    async def test_invalid_scheme_returns_none(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that non-Bearer scheme returns None."""
        result = await get_current_user_optional(
            db=mock_db_session,
            authorization="Basic invalid",
        )

        assert result is None
        mock_db_session.execute.assert_not_awaited()

    async def test_malformed_header_returns_none(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that malformed header returns None."""
        result = await get_current_user_optional(
            db=mock_db_session,
            authorization="Bearer",
        )

        assert result is None
        mock_db_session.execute.assert_not_awaited()

    async def test_invalid_token_returns_none(
        self, mock_db_session: AsyncMock, invalid_token: str
    ) -> None:
        """Test that invalid token returns None."""
        result = await get_current_user_optional(
            db=mock_db_session,
            authorization=f"Bearer {invalid_token}",
        )

        assert result is None
        mock_db_session.execute.assert_not_awaited()

    async def test_user_not_found_returns_none(
        self, mock_db_session: AsyncMock, valid_token: str
    ) -> None:
        """Test that valid token with non-existent user returns None."""
        # Mock execute to return None (user not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await get_current_user_optional(
            db=mock_db_session,
            authorization=f"Bearer {valid_token}",
        )

        assert result is None
        mock_db_session.execute.assert_awaited_once()

    async def test_exception_returns_none(
        self, mock_db_session: AsyncMock, valid_token: str
    ) -> None:
        """Test that exceptions are caught and return None."""
        # Mock execute to raise an exception
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await get_current_user_optional(
            db=mock_db_session,
            authorization=f"Bearer {valid_token}",
        )

        assert result is None
        mock_db_session.execute.assert_awaited_once()


# =============================================================================
# get_current_user Tests
# =============================================================================


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    async def test_valid_token_returns_user(
        self,
        mock_db_session: AsyncMock,
        mock_user: User,
        valid_token: str,
    ) -> None:
        """Test that valid token returns the user."""
        authorization = f"Bearer {valid_token}"

        result = await get_current_user(
            db=mock_db_session,
            authorization=authorization,
        )

        assert result is not None
        assert result.id == mock_user.id
        assert result.email == mock_user.email
        mock_db_session.execute.assert_awaited_once()

    async def test_missing_authorization_header_raises_401(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that missing Authorization header raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=None,
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Not authenticated"
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"
        mock_db_session.execute.assert_not_awaited()

    async def test_invalid_scheme_raises_401(
        self, mock_db_session: AsyncMock, valid_token: str
    ) -> None:
        """Test that non-Bearer scheme raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=f"Basic {valid_token}",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication credentials"
        mock_db_session.execute.assert_not_awaited()

    async def test_malformed_header_raises_401(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that malformed header raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization="Bearer",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication credentials"
        mock_db_session.execute.assert_not_awaited()

    async def test_invalid_token_raises_401(
        self, mock_db_session: AsyncMock, invalid_token: str
    ) -> None:
        """Test that invalid token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=f"Bearer {invalid_token}",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication credentials"
        mock_db_session.execute.assert_not_awaited()

    async def test_expired_token_raises_401(
        self, mock_db_session: AsyncMock, expired_token: str
    ) -> None:
        """Test that expired token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=f"Bearer {expired_token}",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication credentials"
        mock_db_session.execute.assert_not_awaited()

    async def test_user_not_found_raises_401(
        self, mock_db_session: AsyncMock, valid_token: str
    ) -> None:
        """Test that valid token with non-existent user raises 401."""
        # Mock execute to return None (user not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=f"Bearer {valid_token}",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "User not found"
        mock_db_session.execute.assert_awaited_once()

    async def test_invalid_uuid_in_token_raises_401(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test that token with invalid UUID raises 401."""
        # Create a token with an invalid subject (not a UUID)
        from jose import jwt
        from app.core.config import settings

        token = jwt.encode(
            {"sub": "not-a-valid-uuid"}, settings.SECRET_KEY, algorithm="HS256"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=f"Bearer {token}",
            )

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication credentials"
        mock_db_session.execute.assert_not_awaited()


# =============================================================================
# Integration Tests
# =============================================================================


class TestJWTAuthenticationIntegration:
    """Integration tests for JWT authentication flow."""

    async def test_complete_authentication_flow(
        self, mock_db_session: AsyncMock, mock_user: User
    ) -> None:
        """Test complete authentication flow from token creation to user retrieval."""
        # Create token
        token = create_access_token(subject=str(mock_user.id))

        # Authenticate with token
        result = await get_current_user(
            db=mock_db_session,
            authorization=f"Bearer {token}",
        )

        assert result is not None
        assert result.id == mock_user.id
        assert result.email == mock_user.email

    async def test_optional_vs_required_auth_difference(
        self, mock_db_session: AsyncMock, invalid_token: str
    ) -> None:
        """Test difference between optional and required authentication."""
        authorization = f"Bearer {invalid_token}"

        # Optional auth should return None
        optional_result = await get_current_user_optional(
            db=mock_db_session,
            authorization=authorization,
        )
        assert optional_result is None

        # Required auth should raise 401
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                db=mock_db_session,
                authorization=authorization,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
