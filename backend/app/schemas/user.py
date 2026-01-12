"""Pydantic schemas for user operations.

TAG: [SPEC-002] [AUTH] [SCHEMAS]
REQ: REQ-001 - User Model with Email Identification
REQ: REQ-002 - Password Hashing
REQ: REQ-004 - Password Validation

This module provides Pydantic schemas for user-related operations
including creation, updates, and API responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.base import BaseResponse


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., max_length=255, description="User email address")


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime


class UserCreate(UserBase):
    """Schema for user creation.

    Attributes:
        email: User email address (validated)
        password: Plain text password (will be hashed before storage)
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Validate password complexity requirements.

        Ensures password contains:
        - At least 8 characters
        - At least one lowercase letter
        - At least one uppercase letter
        - At least one number
        - At least one special character

        Args:
            v: Password to validate

        Returns:
            Validated password

        Raises:
            ValueError: If password doesn't meet complexity requirements
        """
        from app.core.security import (
            PasswordComplexityError,
            is_password_complex_enough,
        )

        try:
            if not is_password_complex_enough(v, raise_error=True):
                raise ValueError("Password does not meet complexity requirements")
        except PasswordComplexityError as e:
            raise ValueError(str(e)) from e

        return v


class UserUpdate(BaseModel):
    """Schema for user updates.

    All fields are optional to support partial updates.
    """

    email: EmailStr | None = Field(None, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str | None) -> str | None:
        """Validate password complexity if password is provided."""
        if v is None:
            return v

        from app.core.security import (
            PasswordComplexityError,
            is_password_complex_enough,
        )

        try:
            if not is_password_complex_enough(v, raise_error=True):
                raise ValueError("Password does not meet complexity requirements")
        except PasswordComplexityError as e:
            raise ValueError(str(e)) from e

        return v


class UserInDB(UserBase, TimestampMixin):
    """Schema for user in database.

    Includes all fields from the database model.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hashed_password: str
    is_active: bool


class UserResponse(UserBase, TimestampMixin):
    """Schema for user API responses.

    Excludes sensitive data like hashed_password.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool


class UserLogin(BaseModel):
    """Schema for user login.

    Attributes:
        email: User email address
        password: Plain text password
    """

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserChangePassword(BaseModel):
    """Schema for changing user password.

    Attributes:
        old_password: Current password
        new_password: New password to set
    """

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (min 8 characters)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Validate new password complexity requirements."""
        from app.core.security import (
            PasswordComplexityError,
            is_password_complex_enough,
        )

        try:
            if not is_password_complex_enough(v, raise_error=True):
                raise ValueError("Password does not meet complexity requirements")
        except PasswordComplexityError as e:
            raise ValueError(str(e)) from e

        return v


__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserResponse",
    "UserLogin",
    "UserChangePassword",
]
