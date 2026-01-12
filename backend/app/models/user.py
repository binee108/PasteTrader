"""User model for authentication and ownership.

TAG: [SPEC-007] [DATABASE] [USER]
REQ: REQ-001 - User Model Definition
REQ: REQ-002 - User-Workflow Foreign Key Support

This module defines the User model that serves as the owner reference
for workflows and other user-owned resources in PasteTrader.
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

    Provides the minimal structure needed for user identification
    and workflow ownership.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        email: Unique email address for the user
        is_active: Whether the user account is active
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
        workflows: Relationship to owned Workflow models
    """

    __tablename__ = "users"

    # User identification
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
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


__all__ = ["User"]
