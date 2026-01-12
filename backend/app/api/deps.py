"""API dependencies.

Common dependencies for API routes including database sessions,
authentication, pagination, and other shared utilities.

TAG: [SPEC-001] [API] [DEPENDENCIES]
REQ: REQ-007 - API Route Dependencies
"""

from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

# =============================================================================
# Database Session Dependency
# =============================================================================

DBSession = Annotated[AsyncSession, Depends(get_db)]
"""Type alias for database session dependency injection.

Usage:
    @router.get("/items")
    async def get_items(db: DBSession):
        result = await db.execute(select(Item))
        return result.scalars().all()
"""


# =============================================================================
# Pagination Dependencies
# =============================================================================


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints.

    Attributes:
        skip: Number of records to skip (offset).
        limit: Maximum number of records to return.
    """

    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum number of records to return"
    )

    @property
    def offset(self) -> int:
        """Alias for skip, commonly used in SQL queries."""
        return self.skip


def get_pagination_params(
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of records to return")
    ] = 20,
) -> PaginationParams:
    """Get pagination parameters from query string.

    Args:
        skip: Number of records to skip (default: 0).
        limit: Maximum number of records to return (default: 20, max: 100).

    Returns:
        PaginationParams: Pagination configuration.
    """
    return PaginationParams(skip=skip, limit=limit)


Pagination = Annotated[PaginationParams, Depends(get_pagination_params)]
"""Type alias for pagination dependency injection.

Usage:
    @router.get("/items")
    async def list_items(pagination: Pagination):
        return await service.get_items(
            skip=pagination.skip,
            limit=pagination.limit
        )
"""


# =============================================================================
# Sorting/Ordering Dependencies
# =============================================================================


class SortParams(BaseModel):
    """Sorting parameters for list endpoints.

    Attributes:
        sort_by: Field name to sort by.
        sort_order: Sort direction (asc or desc).
    """

    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order: asc or desc",
    )

    @property
    def is_descending(self) -> bool:
        """Check if sort order is descending."""
        return self.sort_order == "desc"


def get_sort_params(
    sort_by: Annotated[str | None, Query(description="Field to sort by")] = None,
    sort_order: Annotated[
        str, Query(pattern="^(asc|desc)$", description="Sort order: asc or desc")
    ] = "asc",
) -> SortParams:
    """Get sorting parameters from query string.

    Args:
        sort_by: Field name to sort by (optional).
        sort_order: Sort direction, either 'asc' or 'desc' (default: 'asc').

    Returns:
        SortParams: Sorting configuration.
    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)


Sorting = Annotated[SortParams, Depends(get_sort_params)]
"""Type alias for sorting dependency injection.

Usage:
    @router.get("/items")
    async def list_items(sorting: Sorting):
        return await service.get_items(
            sort_by=sorting.sort_by,
            descending=sorting.is_descending
        )
"""


# =============================================================================
# Authentication Dependencies (Placeholder)
# =============================================================================

# TODO: Implement actual authentication when auth system is added


async def get_current_user_optional() -> Any | None:
    """Get current user if authenticated (optional).

    Returns:
        User object if authenticated, None otherwise.
    """
    # Placeholder for future implementation
    return None


async def get_current_user() -> Any:
    """Get current authenticated user (required).

    Raises:
        HTTPException: 401 if not authenticated.

    Returns:
        User object.
    """
    # Placeholder for future implementation
    # When implemented, this should:
    # 1. Extract token from Authorization header
    # 2. Validate and decode JWT token
    # 3. Fetch user from database
    # 4. Raise HTTPException(401) if invalid
    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUserOptional = Annotated[Any | None, Depends(get_current_user_optional)]
"""Type alias for optional current user dependency.

Usage:
    @router.get("/items")
    async def list_items(current_user: CurrentUserOptional):
        if current_user:
            # Show user-specific items
            pass
        else:
            # Show public items
            pass
"""

CurrentUser = Annotated[Any, Depends(get_current_user)]
"""Type alias for required current user dependency.

Usage:
    @router.post("/items")
    async def create_item(current_user: CurrentUser, item: ItemCreate):
        return await service.create_item(item, owner=current_user)
"""


# =============================================================================
# Combined Query Dependencies
# =============================================================================


class ListQueryParams(BaseModel):
    """Combined query parameters for list endpoints.

    Combines pagination and sorting in a single dependency.
    """

    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")

    @property
    def offset(self) -> int:
        """Alias for skip."""
        return self.skip

    @property
    def is_descending(self) -> bool:
        """Check if sort order is descending."""
        return self.sort_order == "desc"


def get_list_query_params(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Annotated[str | None, Query()] = None,
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
) -> ListQueryParams:
    """Get combined list query parameters.

    Args:
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        sort_by: Field to sort by.
        sort_order: Sort direction.

    Returns:
        ListQueryParams: Combined query configuration.
    """
    return ListQueryParams(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


ListQuery = Annotated[ListQueryParams, Depends(get_list_query_params)]
"""Type alias for combined list query dependency.

Usage:
    @router.get("/items")
    async def list_items(query: ListQuery):
        return await service.get_items(
            skip=query.skip,
            limit=query.limit,
            sort_by=query.sort_by,
            descending=query.is_descending
        )
"""


__all__ = [
    "CurrentUser",
    "CurrentUserOptional",
    "DBSession",
    "ListQuery",
    "ListQueryParams",
    "Pagination",
    "PaginationParams",
    "SortParams",
    "Sorting",
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "get_list_query_params",
    "get_pagination_params",
    "get_sort_params",
]
