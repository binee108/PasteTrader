"""Base Pydantic schemas with common patterns.

TAG: [SPEC-007] [SCHEMAS] [BASE]
REQ: REQ-001 - Base Schema Definitions
REQ: REQ-002 - Paginated Response Generic
REQ: REQ-003 - Common Validators

This module defines base schemas and common patterns used across the API.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Required at runtime for Pydantic
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID  # noqa: TC003 - Required at runtime for Pydantic

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

# Generic type for paginated response items
T = TypeVar("T")

# Common field definitions for reuse
ConfigField: FieldInfo = cast(
    "FieldInfo",
    Field(
        default_factory=dict,
        description="Configuration object (JSON)",
        examples=[{"timeout": 300, "retry": True}],
    ),
)


class BaseSchema(BaseModel):
    """Base schema with common configuration for all schemas.

    Configures Pydantic v2 settings for consistent behavior across all schemas.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class BaseResponse(BaseSchema):
    """Base response schema with common fields.

    Includes id, created_at, and updated_at fields common to most responses.
    """

    id: UUID = Field(
        ...,
        description="Unique identifier (UUID v4)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the resource was created",
        examples=["2024-01-15T10:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the resource was last updated",
        examples=["2024-01-15T12:45:00Z"],
    )


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
        examples=[1],
    )
    size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
        examples=[20],
    )

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size


class PaginatedResponse[T](BaseSchema):
    """Generic paginated response wrapper.

    Provides consistent pagination metadata for all list endpoints.
    """

    items: list[T] = Field(
        ...,
        description="List of items in the current page",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages",
        examples=[100],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1],
    )
    size: int = Field(
        ...,
        ge=1,
        description="Number of items per page",
        examples=[20],
    )
    pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        examples=[5],
    )

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        size: int,
    ) -> PaginatedResponse[T]:
        """Create a paginated response from items and pagination info.

        Args:
            items: List of items for the current page.
            total: Total number of items across all pages.
            page: Current page number.
            size: Number of items per page.

        Returns:
            A PaginatedResponse instance with calculated pages.
        """
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


class ErrorResponse(BaseSchema):
    """Standard error response schema."""

    error: str = Field(
        ...,
        description="Error type identifier",
        examples=["ValidationError"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["The request payload is invalid"],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details",
        examples=[{"field": "name", "reason": "Field is required"}],
    )


class SuccessResponse(BaseSchema):
    """Standard success response for operations without return data."""

    success: bool = Field(
        default=True,
        description="Indicates if the operation was successful",
    )
    message: str = Field(
        ...,
        description="Human-readable success message",
        examples=["Resource deleted successfully"],
    )


class MessageResponse(BaseSchema):
    """Simple message response schema."""

    message: str = Field(
        ...,
        description="Response message",
        examples=["Operation completed successfully"],
    )


# Common field definitions for reuse
NameField: FieldInfo = cast(
    "FieldInfo",
    Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Workflow"],
    ),
)

OptionalNameField: FieldInfo = cast(
    "FieldInfo",
    Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Display name",
        examples=["My Workflow"],
    ),
)

DescriptionField: FieldInfo = cast(
    "FieldInfo",
    Field(
        default=None,
        max_length=2000,
        description="Optional description",
        examples=["This workflow processes incoming data"],
    ),
)

VersionField: FieldInfo = cast(
    "FieldInfo",
    Field(
        ...,
        ge=1,
        description="Version number for optimistic locking",
        examples=[1],
    ),
)


__all__ = [
    "BaseResponse",
    "BaseSchema",
    "ConfigField",
    "DescriptionField",
    "ErrorResponse",
    "MessageResponse",
    "NameField",
    "OptionalNameField",
    "PaginatedResponse",
    "PaginationParams",
    "SuccessResponse",
    "VersionField",
]
