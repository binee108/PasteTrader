"""User schema tests.

TAG: [SPEC-002] [AUTH] [SCHEMAS] [TEST]
REQ: REQ-001 - User Model with Email Identification
REQ: REQ-002 - Password Hashing
REQ: REQ-004 - Password Validation

Tests for User Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserInDB,
    UserLogin,
    UserResponse,
    UserUpdate,
)


class TestUserCreate:
    """Test UserCreate schema."""

    def test_valid_user_creation(self):
        """Test creating user with valid data."""
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
        )

        assert user_data.email == "test@example.com"
        assert user_data.password == "SecurePass123!"

    def test_email_validation(self):
        """Test that email must be valid format."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="invalid-email",
                password="SecurePass123!",
            )

        errors = exc_info.value.errors()
        assert any("email" in str(error).lower() for error in errors)

    def test_password_too_short(self):
        """Test that password must be at least 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="Short1!",
            )

        errors = exc_info.value.errors()
        assert any("password" in str(error).lower() for error in errors)

    def test_password_complexity_validation(self):
        """Test password complexity requirements."""
        # Missing uppercase
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="lowercase123!",
            )

        # Missing lowercase
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="UPPERCASE123!",
            )

        # Missing number
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="NoNumbers!",
            )

        # Missing special character
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="NoSpecialChars123",
            )

    def test_password_complexity_error_message(self):
        """Test that password complexity error has detailed message."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                password="short",
            )

        errors = exc_info.value.errors()
        password_errors = [
            e for e in errors if "password" in str(e.get("loc", [""])).lower()
        ]

        # Should have error about password
        assert len(password_errors) > 0

    def test_valid_complex_password(self):
        """Test that valid complex password passes."""
        user_data = UserCreate(
            email="test@example.com",
            password="ValidPass123!",
        )

        assert user_data.password == "ValidPass123!"


class TestUserUpdate:
    """Test UserUpdate schema."""

    def test_update_email_only(self):
        """Test updating only email."""
        user_data = UserUpdate(email="newemail@example.com")

        assert user_data.email == "newemail@example.com"
        assert user_data.password is None

    def test_update_password_only(self):
        """Test updating only password."""
        user_data = UserUpdate(password="NewSecurePass123!")

        assert user_data.email is None
        assert user_data.password == "NewSecurePass123!"

    def test_update_both_fields(self):
        """Test updating both email and password."""
        user_data = UserUpdate(
            email="newemail@example.com",
            password="NewSecurePass123!",
        )

        assert user_data.email == "newemail@example.com"
        assert user_data.password == "NewSecurePass123!"

    def test_update_no_fields(self):
        """Test updating with no fields (empty update)."""
        user_data = UserUpdate()

        assert user_data.email is None
        assert user_data.password is None

    def test_password_validation_on_update(self):
        """Test that password complexity is validated on update."""
        with pytest.raises(ValidationError):
            UserUpdate(password="short")

        with pytest.raises(ValidationError):
            UserUpdate(password="nouppercase123!")

    def test_password_none_returns_early(self):
        """Test that None password returns early without validation."""
        # This tests line 97: if v is None: return v
        user_data = UserUpdate(password=None)

        # Should not raise ValidationError
        assert user_data.password is None

    def test_password_complexity_error_message_on_update(self):
        """Test that password complexity error has detailed message on update."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(password="short")

        errors = exc_info.value.errors()
        password_errors = [
            e for e in errors if "password" in str(e.get("loc", [""])).lower()
        ]

        # Should have error about password
        assert len(password_errors) > 0


class TestUserLogin:
    """Test UserLogin schema."""

    def test_valid_login_data(self):
        """Test creating valid login data."""
        login_data = UserLogin(
            email="test@example.com",
            password="SecurePass123!",
        )

        assert login_data.email == "test@example.com"
        assert login_data.password == "SecurePass123!"

    def test_login_requires_email(self):
        """Test that email is required for login."""
        with pytest.raises(ValidationError):
            UserLogin(password="SecurePass123!")

    def test_login_requires_password(self):
        """Test that password is required for login."""
        with pytest.raises(ValidationError):
            UserLogin(email="test@example.com")


class TestUserChangePassword:
    """Test UserChangePassword schema."""

    def test_valid_password_change(self):
        """Test valid password change data."""
        change_data = UserChangePassword(
            old_password="OldPass123!",
            new_password="NewPass456!",
        )

        assert change_data.old_password == "OldPass123!"
        assert change_data.new_password == "NewPass456!"

    def test_new_password_complexity(self):
        """Test that new password meets complexity requirements."""
        with pytest.raises(ValidationError):
            UserChangePassword(
                old_password="OldPass123!",
                new_password="short",
            )

        with pytest.raises(ValidationError):
            UserChangePassword(
                old_password="OldPass123!",
                new_password="nouppercase123!",
            )

    def test_new_password_complexity_error_message(self):
        """Test that password complexity error has detailed message for password change."""
        with pytest.raises(ValidationError) as exc_info:
            UserChangePassword(
                old_password="OldPass123!",
                new_password="short",
            )

        errors = exc_info.value.errors()
        password_errors = [
            e for e in errors if "new_password" in str(e.get("loc", [""])).lower()
        ]

        # Should have error about new_password
        assert len(password_errors) > 0


class TestUserResponse:
    """Test UserResponse schema."""

    async def test_user_response_from_orm(self, db_session):
        """Test creating UserResponse from ORM object."""

        from app.models.user import User

        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create response from ORM object
        response = UserResponse.model_validate(user)

        assert response.id == user.id
        assert response.email == "test@example.com"
        assert response.is_active is True
        assert response.created_at is not None
        assert response.updated_at is not None

        # Password should not be in response
        assert (
            not hasattr(response, "hashed_password") or response.hashed_password is None
        )


class TestUserInDB:
    """Test UserInDB schema."""

    async def test_user_in_db_includes_password(self, db_session):
        """Test that UserInDB includes hashed_password."""
        from app.models.user import User

        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create UserInDB from ORM object
        user_in_db = UserInDB.model_validate(user)

        assert user_in_db.id == user.id
        assert user_in_db.email == "test@example.com"
        assert user_in_db.hashed_password == "hashed_password"
        assert user_in_db.is_active is True
