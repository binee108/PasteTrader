"""User service layer for business logic.

TAG: [SPEC-002] [AUTH] [SERVICE]
REQ: REQ-001 - User Model with Email Identification
REQ: REQ-002 - Password Hashing
REQ: REQ-003 - Account Status Management
REQ: REQ-006 - Password Verification

This module provides the service layer for user management operations,
including creation, retrieval, authentication, and updates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.utils.email import normalize_email

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service layer for user management operations.

    This service provides a clean abstraction over database operations
    for user management, including password hashing, email normalization,
    and soft delete filtering.

    Logging:
        - Logs all user creation attempts
        - Logs authentication events (success/failure)
        - Logs password changes
        - Logs security events for audit trail
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user service.

        Args:
            session: Async SQLAlchemy session
        """
        from app.core.logging import get_logger

        self.session = session
        self.logger = get_logger(__name__)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password.

        This method performs the following:
        - Normalizes email address
        - Hashes password using bcrypt
        - Creates user with is_active=True
        - Commits to database

        Args:
            user_data: User creation data with plain password

        Returns:
            Created user instance

        Raises:
            IntegrityError: If email already exists

        Examples:
            >>> service = UserService(session)
            >>> user = await service.create_user(
            ...     UserCreate(email="test@example.com", password="SecurePass123!")
            ... )
            >>> assert user.email == "test@example.com"
            >>> assert user.is_active is True
        """
        # Log user creation attempt
        self.logger.info(
            "Attempting to create new user",
            extra={
                "context": {
                    "email": user_data.email,
                    "action": "create_user",
                }
            },
        )

        # Normalize email
        normalized_email = normalize_email(user_data.email)

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user instance
        user = User(
            email=normalized_email,
            hashed_password=hashed_password,
            is_active=True,
        )

        # Add to session and commit
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        # Log successful user creation
        self.logger.info(
            "User created successfully",
            extra={
                "context": {
                    "user_id": str(user.id),
                    "email": user.email,
                    "action": "create_user",
                    "status": "success",
                }
            },
        )

        return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID with soft delete filtering.

        Args:
            user_id: UUID of the user

        Returns:
            User instance or None if not found

        Examples:
            >>> service = UserService(session)
            >>> user = await service.get_user_by_id("user-uuid-123")
            >>> if user:
            ...     print(user.email)
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email with soft delete filtering.

        Args:
            email: User email address

        Returns:
            User instance or None if not found

        Examples:
            >>> service = UserService(session)
            >>> user = await service.get_user_by_email("test@example.com")
            >>> if user:
            ...     print(user.id)
        """
        # Normalize email for lookup
        normalized_email = normalize_email(email)

        result = await self.session.execute(
            select(User).where(User.email == normalized_email)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user_id: str, user_data: UserUpdate) -> User | None:
        """Update user with partial data.

        Args:
            user_id: UUID of the user to update
            user_data: Partial user update data

        Returns:
            Updated user instance or None if not found

        Raises:
            IntegrityError: If email already exists (if email is being updated)

        Examples:
            >>> service = UserService(session)
            >>> user = await service.update_user(
            ...     "user-uuid-123",
            ...     UserUpdate(password="NewSecurePass123!")
            ... )
        """
        self.logger.info(
            "Attempting to update user",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "update_user",
                    "has_email": user_data.email is not None,
                    "has_password": user_data.password is not None,
                }
            },
        )

        user = await self.get_user_by_id(user_id)

        if not user:
            self.logger.warning(
                "User not found for update",
                extra={
                    "context": {
                        "user_id": user_id,
                        "action": "update_user",
                        "status": "not_found",
                    }
                },
            )
            return None

        # Update email if provided
        if user_data.email is not None:
            user.email = normalize_email(user_data.email)

        # Update password if provided
        if user_data.password is not None:
            user.hashed_password = hash_password(user_data.password)
            self.logger.info(
                "Password updated",
                extra={
                    "context": {
                        "user_id": user_id,
                        "action": "password_change",
                        "status": "success",
                    }
                },
            )

        await self.session.commit()
        await self.session.refresh(user)

        self.logger.info(
            "User updated successfully",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "update_user",
                    "status": "success",
                }
            },
        )

        return user

    async def delete_user(self, user_id: str) -> bool:
        """Soft delete user by ID.

        Args:
            user_id: UUID of the user to delete

        Returns:
            True if user was deleted, False if not found

        Examples:
            >>> service = UserService(session)
            >>> deleted = await service.delete_user("user-uuid-123")
            >>> assert deleted is True
        """
        self.logger.info(
            "Attempting to delete user",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "delete_user",
                }
            },
        )

        user = await self.get_user_by_id(user_id)

        if not user:
            self.logger.warning(
                "User not found for deletion",
                extra={
                    "context": {
                        "user_id": user_id,
                        "action": "delete_user",
                        "status": "not_found",
                    }
                },
            )
            return False

        # Soft delete using User model method
        user.soft_delete()
        await self.session.commit()

        self.logger.info(
            "User deleted successfully",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "delete_user",
                    "status": "success",
                }
            },
        )

        return True

    async def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> User | None:
        """Authenticate user with email and password.

        This method performs the following:
        - Normalizes email address
        - Finds user by email
        - Checks if user is active
        - Verifies password against hash

        Args:
            email: User email address
            password: Plain text password

        Returns:
            Authenticated user instance or None if authentication fails

        Examples:
            >>> service = UserService(session)
            >>> user = await service.authenticate_user(
            ...     "test@example.com",
            ...     "SecurePass123!"
            ... )
            >>> if user:
            ...     print("Authentication successful")

        Security:
            - Returns None for both non-existent users and incorrect passwords
            - This prevents user enumeration attacks
            - Timing should be consistent regardless of failure reason

        Logging:
            - Logs authentication attempts for security audit
            - Does not log passwords or sensitive data
            - Logs both successes and failures
        """
        normalized_email = normalize_email(email)

        self.logger.info(
            "Authentication attempt",
            extra={
                "context": {
                    "email": normalized_email,
                    "action": "authenticate",
                }
            },
        )

        # Find user by email
        user = await self.get_user_by_email(normalized_email)

        # Check if user exists and is active
        if not user:
            self.logger.warning(
                "Authentication failed: user not found",
                extra={
                    "context": {
                        "email": normalized_email,
                        "action": "authenticate",
                        "status": "failed",
                        "reason": "user_not_found",
                    }
                },
            )
            return None

        if not user.is_active:
            self.logger.warning(
                "Authentication failed: user inactive",
                extra={
                    "context": {
                        "email": normalized_email,
                        "action": "authenticate",
                        "status": "failed",
                        "reason": "user_inactive",
                    }
                },
            )
            return None

        # Verify password
        if not verify_password(password, user.hashed_password):
            self.logger.warning(
                "Authentication failed: invalid password",
                extra={
                    "context": {
                        "email": normalized_email,
                        "action": "authenticate",
                        "status": "failed",
                        "reason": "invalid_password",
                    }
                },
            )
            return None

        self.logger.info(
            "Authentication successful",
            extra={
                "context": {
                    "user_id": str(user.id),
                    "email": normalized_email,
                    "action": "authenticate",
                    "status": "success",
                }
            },
        )

        return user

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change user password.

        Args:
            user_id: UUID of the user
            old_password: Current password
            new_password: New password to set

        Returns:
            True if password was changed, False if user not found or old password incorrect

        Examples:
            >>> service = UserService(session)
            >>> changed = await service.change_password(
            ...     "user-uuid-123",
            ...     "OldPass123!",
            ...     "NewPass456!"
            ... )
        """
        self.logger.info(
            "Password change attempt",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "change_password",
                }
            },
        )

        user = await self.get_user_by_id(user_id)

        if not user:
            self.logger.warning(
                "Password change failed: user not found",
                extra={
                    "context": {
                        "user_id": user_id,
                        "action": "change_password",
                        "status": "failed",
                        "reason": "user_not_found",
                    }
                },
            )
            return False

        # Verify old password
        if not verify_password(old_password, user.hashed_password):
            self.logger.warning(
                "Password change failed: invalid old password",
                extra={
                    "context": {
                        "user_id": user_id,
                        "action": "change_password",
                        "status": "failed",
                        "reason": "invalid_old_password",
                    }
                },
            )
            return False

        # Set new password (hashed)
        user.set_password(new_password)
        await self.session.commit()

        self.logger.info(
            "Password changed successfully",
            extra={
                "context": {
                    "user_id": user_id,
                    "action": "change_password",
                    "status": "success",
                }
            },
        )

        return True


__all__ = [
    "UserService",
]
