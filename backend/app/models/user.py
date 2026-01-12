"""User model for authentication and ownership.

TAG: [SPEC-002] [SPEC-007] [DATABASE] [USER]
REQ: REQ-001 - User Model Definition
REQ: REQ-002 - User-Workflow Foreign Key Support
REQ: REQ-003 - Account Status Management
REQ: REQ-005 - User-Workflow Relationship

This module defines the User model that serves as the owner reference
for workflows and other user-owned resources in PasteTrader.

Enhanced for SPEC-002 with password hashing support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.workflow import Workflow


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """User model for authentication and resource ownership.

    Provides the structure needed for user identification, authentication,
    and workflow ownership.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        email: Unique email address for the user
        hashed_password: Bcrypt hash of user password
        is_active: Whether the user account is active
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
        workflows: Relationship to owned Workflow models

    Security:
        - Passwords are stored as bcrypt hashes (cost factor 12)
        - Email addresses are case-insensitive (normalized to lowercase)
        - Soft delete prevents permanent data loss
        - is_active flag allows account deactivation
    """

    __tablename__ = "users"

    # User identification
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Password hash (bcrypt, cost factor 12)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Relationships
    workflows: Mapped[list[Workflow]] = relationship(
        "Workflow",
        back_populates="owner",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of the user."""
        return f"<User(id={self.id}, email='{self.email}')>"

    def set_password(self, password: str) -> None:
        """Set user password by hashing it with bcrypt.

        Args:
            password: Plain text password to hash and store
        """
        from app.core.security import hash_password

        self.hashed_password = hash_password(password)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        from app.core.security import verify_password

        return verify_password(password, self.hashed_password)


__all__ = ["User"]
