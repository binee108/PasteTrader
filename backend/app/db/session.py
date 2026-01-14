"""Database session management.

TAG: [SPEC-001] [DATABASE] [SESSION]
REQ: REQ-001 - Database Engine and Session Management
REQ: REQ-005 - Database Connection Dependency
REQ: REQ-006 - Session Lifecycle Management

This module provides async database engine and session management
using SQLAlchemy 2.0 async patterns.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Build database URL from settings
# Handle case where DATABASE_URL might be None (for testing without DB)
_database_url = str(settings.DATABASE_URL) if settings.DATABASE_URL else None

# Create async engine with connection pooling
# Engine is created even if URL is None to allow import, but will fail on use
if _database_url:
    engine = create_async_engine(
        _database_url,
        pool_pre_ping=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
    )
else:
    # Create a placeholder engine for testing imports
    # This will raise an error if actually used without proper configuration
    engine = create_async_engine(
        "postgresql+asyncpg://user:pass@localhost/test",
        pool_pre_ping=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
    )

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency for FastAPI.

    Yields an async session and ensures proper cleanup after request.
    Commits on success, rolls back on exception.

    Yields:
        AsyncSession: The database session for the request.

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "async_session",
    "engine",
    "get_db",
]
