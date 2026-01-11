"""Base model and mixins for SQLAlchemy models.

TAG: [SPEC-001] [DATABASE] [BASE-MODEL]
REQ: REQ-003 - Base Model with Mixins

This module provides the base model class and reusable mixins
for common database patterns like timestamps and soft deletion.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, event, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models should inherit from this class to ensure consistent
    behavior and configuration across the application.
    """

    # Configure naming conventions for constraints
    # This ensures consistent naming for foreign keys, indexes, etc.
    pass


class UUIDMixin:
    """Mixin that adds UUID primary key to models.

    The UUID is generated on the Python side for SQLite compatibility,
    but uses server-side generation for PostgreSQL.
    """

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """UUID primary key with auto-generation."""
        return mapped_column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp fields.

    Both fields are timezone-aware and automatically managed:
    - created_at: Set on record creation, never changes
    - updated_at: Updated on every modification
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when record was created."""
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(UTC),
            server_default=func.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when record was last updated."""
        return mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(UTC),
            server_default=func.now(),
            onupdate=lambda: datetime.now(UTC),
            nullable=False,
        )


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality to models.

    Instead of permanently deleting records, they are marked as deleted
    by setting the deleted_at timestamp. This allows for data recovery
    and audit trails.
    """

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        """Timestamp when record was soft-deleted, None if active."""
        return mapped_column(
            DateTime(timezone=True),
            default=None,
            nullable=True,
        )

    @property
    def is_deleted(self) -> bool:
        """Check if the record has been soft-deleted.

        Returns:
            True if the record is deleted, False otherwise.
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as soft-deleted.

        Sets deleted_at to the current UTC timestamp.
        """
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore a soft-deleted record.

        Clears the deleted_at timestamp.
        """
        self.deleted_at = None


__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
]
