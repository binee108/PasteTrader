"""User service tests.

TAG: [SPEC-002] [AUTH] [SERVICE] [TEST]
REQ: REQ-001 - User Model with Email Identification
REQ: REQ-002 - Password Hashing
REQ: REQ-006 - Password Verification

Tests for UserService following AC-022 to AC-028.
"""

import pytest

from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


class TestCreateUser:
    """Test user creation (AC-022)."""

    async def test_create_user_with_password_hashing(self, db_session):
        """Test that service hashes password automatically (AC-022)."""
        service = UserService(db_session)

        user_data = UserCreate(
            email="test@example.com",
            password="PlainPass123!",
        )

        user = await service.create_user(user_data)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.hashed_password.startswith("$2b$12$")
        assert user.hashed_password != "PlainPass123!"
        assert user.is_active is True

    async def test_create_user_normalizes_email(self, db_session):
        """Test that email is normalized during creation."""
        service = UserService(db_session)

        user_data = UserCreate(
            email="  Test@Example.COM  ",
            password="PlainPass123!",
        )

        user = await service.create_user(user_data)

        # Email should be normalized
        assert user.email == "test@example.com"

    async def test_create_user_duplicate_email_fails(self, db_session):
        """Test that duplicate email raises IntegrityError."""
        service = UserService(db_session)

        user_data1 = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        user_data2 = UserCreate(
            email="test@example.com",
            password="Pass456!",
        )

        # First user should succeed
        await service.create_user(user_data1)

        # Second user with same email should fail
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            await service.create_user(user_data2)


class TestGetUser:
    """Test user retrieval (AC-023, AC-024)."""

    async def test_get_user_by_id(self, db_session):
        """Test retrieving user by ID (AC-023)."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        created_user = await service.create_user(user_data)

        # Retrieve by ID
        found_user = await service.get_user_by_id(str(created_user.id))

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "test@example.com"

    async def test_get_user_by_id_not_found(self, db_session):
        """Test retrieving non-existent user by ID."""
        from uuid import uuid4

        service = UserService(db_session)

        found_user = await service.get_user_by_id(str(uuid4()))

        assert found_user is None

    async def test_get_user_by_email(self, db_session):
        """Test retrieving user by email (AC-024)."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        await service.create_user(user_data)

        # Retrieve by email
        found_user = await service.get_user_by_email("test@example.com")

        assert found_user is not None
        assert found_user.email == "test@example.com"

    async def test_get_user_by_email_normalized(self, db_session):
        """Test that email lookup is case-insensitive."""
        service = UserService(db_session)

        # Create user with lowercase email
        user_data = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        await service.create_user(user_data)

        # Lookup with uppercase email
        found_user = await service.get_user_by_email("TEST@EXAMPLE.COM")

        assert found_user is not None
        assert found_user.email == "test@example.com"

    async def test_get_user_by_email_not_found(self, db_session):
        """Test retrieving non-existent user by email."""
        service = UserService(db_session)

        found_user = await service.get_user_by_email("nonexistent@example.com")

        assert found_user is None


class TestAuthenticateUser:
    """Test user authentication (AC-025 to AC-028)."""

    async def test_authenticate_with_valid_credentials(self, db_session):
        """Test successful authentication (AC-025)."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
        )
        await service.create_user(user_data)

        # Authenticate
        authenticated_user = await service.authenticate_user(
            "test@example.com",
            "SecurePass123!",
        )

        assert authenticated_user is not None
        assert authenticated_user.email == "test@example.com"
        assert authenticated_user.is_active is True

    async def test_authenticate_with_invalid_password(self, db_session):
        """Test failed authentication with wrong password (AC-026)."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
        )
        await service.create_user(user_data)

        # Authenticate with wrong password
        authenticated_user = await service.authenticate_user(
            "test@example.com",
            "WrongPass456!",
        )

        assert authenticated_user is None

    async def test_authenticate_inactive_user(self, db_session):
        """Test that inactive user cannot authenticate (AC-027)."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="SecurePass123!",
        )
        user = await service.create_user(user_data)

        # Deactivate user
        user.is_active = False
        await db_session.commit()

        # Try to authenticate
        authenticated_user = await service.authenticate_user(
            "test@example.com",
            "SecurePass123!",
        )

        assert authenticated_user is None

    async def test_authenticate_nonexistent_user(self, db_session):
        """Test failed authentication for non-existent user (AC-028)."""
        service = UserService(db_session)

        authenticated_user = await service.authenticate_user(
            "nonexistent@example.com",
            "AnyPass123!",
        )

        assert authenticated_user is None


class TestUpdateUser:
    """Test user updates."""

    async def test_update_user_email(self, db_session):
        """Test updating user email."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        user = await service.create_user(user_data)

        # Update email
        updated_user = await service.update_user(
            str(user.id),
            UserUpdate(email="newemail@example.com"),
        )

        assert updated_user is not None
        assert updated_user.email == "newemail@example.com"

    async def test_update_user_password(self, db_session):
        """Test updating user password."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="OldPass123!",
        )
        user = await service.create_user(user_data)

        # Update password
        updated_user = await service.update_user(
            str(user.id),
            UserUpdate(password="NewPass456!"),
        )

        assert updated_user is not None
        # New password should work
        assert updated_user.verify_password("NewPass456!")
        # Old password should not work
        assert not updated_user.verify_password("OldPass123!")

    async def test_update_user_not_found(self, db_session):
        """Test updating non-existent user."""
        from uuid import uuid4

        service = UserService(db_session)

        updated_user = await service.update_user(
            str(uuid4()),
            UserUpdate(email="new@example.com"),
        )

        assert updated_user is None


class TestDeleteUser:
    """Test user deletion (soft delete)."""

    async def test_soft_delete_user(self, db_session):
        """Test soft deleting a user."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="Pass123!",
        )
        user = await service.create_user(user_data)

        # Soft delete
        deleted = await service.delete_user(str(user.id))

        assert deleted is True

        # Refresh from database
        await db_session.refresh(user)

        assert user.is_deleted is True
        assert user.is_active is False

    async def test_delete_nonexistent_user(self, db_session):
        """Test deleting non-existent user."""
        from uuid import uuid4

        service = UserService(db_session)

        deleted = await service.delete_user(str(uuid4()))

        assert deleted is False


class TestChangePassword:
    """Test password changes."""

    async def test_change_password_success(self, db_session):
        """Test successful password change."""
        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="OldPass123!",
        )
        user = await service.create_user(user_data)

        # Change password
        changed = await service.change_password(
            str(user.id),
            "OldPass123!",
            "NewPass456!",
        )

        assert changed is True

        # Refresh user
        await db_session.refresh(user)

        # New password should work
        assert user.verify_password("NewPass456!")
        # Old password should not work
        assert not user.verify_password("OldPass123!")

    async def test_change_password_wrong_old_password(self, db_session):
        """Test changing password with wrong old password."""
        from uuid import uuid4

        service = UserService(db_session)

        # Create user
        user_data = UserCreate(
            email="test@example.com",
            password="OldPass123!",
        )
        user = await service.create_user(user_data)

        # Try to change with wrong old password
        changed = await service.change_password(
            str(user.id),
            "WrongOldPass!",
            "NewPass456!",
        )

        assert changed is False

    async def test_change_password_nonexistent_user(self, db_session):
        """Test changing password for non-existent user."""
        from uuid import uuid4

        service = UserService(db_session)

        changed = await service.change_password(
            str(uuid4()),
            "OldPass123!",
            "NewPass456!",
        )

        assert changed is False
