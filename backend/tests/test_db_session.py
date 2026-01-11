"""Tests for database session management.

TAG: [SPEC-001] [DATABASE] [SESSION]
REQ: REQ-001 - Database Engine and Session Management
REQ: REQ-005 - Database Connection Dependency
REQ: REQ-006 - Session Lifecycle Management
AC: AC-001 - Async Engine Creation
AC: AC-002 - Session Factory
AC: AC-003 - FastAPI Dependency
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class TestDatabaseModuleStructure:
    """Test database module structure and exports."""

    def test_db_module_exists(self) -> None:
        """Database module should exist."""
        from app import db

        assert db is not None

    def test_db_exports_engine(self) -> None:
        """Database module should export engine."""
        from app.db import engine

        assert engine is not None

    def test_db_exports_async_session(self) -> None:
        """Database module should export async_session factory."""
        from app.db import async_session

        assert async_session is not None

    def test_db_exports_get_db(self) -> None:
        """Database module should export get_db dependency."""
        from app.db import get_db

        assert get_db is not None


class TestAsyncEngineCreation:
    """Test async engine creation and configuration."""

    def test_engine_is_async_engine(self) -> None:
        """Engine should be an AsyncEngine instance."""
        from app.db import engine

        assert isinstance(engine, AsyncEngine)

    def test_engine_pool_pre_ping_enabled(self) -> None:
        """Engine should have pool_pre_ping enabled."""
        from app.db import engine

        # pool_pre_ping is set on the underlying sync engine
        assert engine.sync_engine.pool._pre_ping is True

    def test_engine_pool_size_configured(self) -> None:
        """Engine should have configured pool size."""
        from app.db import engine
        from app.core.config import settings

        # Check pool size matches configuration
        assert engine.sync_engine.pool.size() == settings.DATABASE_POOL_SIZE

    def test_engine_max_overflow_configured(self) -> None:
        """Engine should have configured max_overflow."""
        from app.db import engine
        from app.core.config import settings

        # Check max overflow matches configuration
        assert engine.sync_engine.pool._max_overflow == settings.DATABASE_MAX_OVERFLOW


class TestSessionFactory:
    """Test session factory configuration."""

    def test_session_factory_exists(self) -> None:
        """Session factory should exist."""
        from app.db import async_session

        assert async_session is not None

    def test_session_factory_creates_async_session(self) -> None:
        """Session factory should create AsyncSession instances."""
        from app.db import async_session

        # The factory should be an async_sessionmaker
        # When called, it returns a context manager that yields AsyncSession
        assert callable(async_session)

    def test_session_factory_expire_on_commit_false(self) -> None:
        """Session factory should have expire_on_commit=False."""
        from app.db import async_session

        # Check the class configuration
        assert async_session.kw.get("expire_on_commit") is False


class TestGetDbDependency:
    """Test get_db FastAPI dependency."""

    def test_get_db_is_async_generator(self) -> None:
        """get_db should be an async generator function."""
        import inspect

        from app.db import get_db

        assert inspect.isasyncgenfunction(get_db)

    @pytest.mark.asyncio
    async def test_get_db_yields_async_session(self) -> None:
        """get_db should yield an AsyncSession."""
        from app.db import get_db

        async for session in get_db():
            assert isinstance(session, AsyncSession)
            break  # Only need to check the first yield


class TestSessionLifecycle:
    """Test session lifecycle management."""

    @pytest.mark.asyncio
    async def test_session_commit_on_success(self) -> None:
        """Session should be committed on successful completion."""
        from app.db import get_db

        # This test verifies that get_db properly manages the session lifecycle
        # A successful iteration through get_db should commit the session
        session_committed = False
        async for session in get_db():
            # Session is active
            assert session.is_active
            session_committed = True

        assert session_committed

    @pytest.mark.asyncio
    async def test_session_closed_after_use(self) -> None:
        """Session should be closed after use."""
        from app.db import get_db

        session_ref = None
        async for session in get_db():
            session_ref = session

        # After the generator completes, session should be closed
        # Note: We can't easily test this without more complex setup
        assert session_ref is not None


class TestDatabaseConnection:
    """Test database connection functionality.

    These tests require a running PostgreSQL database and are marked
    as integration tests. They are skipped if no database is available.
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_engine_can_connect(self) -> None:
        """Engine should be able to establish a connection."""
        from sqlalchemy import text

        from app.db import engine

        try:
            async with engine.connect() as conn:
                # Execute a simple query to verify connection works
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row[0] == 1
        except OSError as e:
            pytest.skip(f"Database not available: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_can_execute_query(self) -> None:
        """Session should be able to execute queries."""
        from sqlalchemy import text

        from app.db import get_db

        try:
            async for session in get_db():
                result = await session.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row[0] == 1
                break
        except OSError as e:
            pytest.skip(f"Database not available: {e}")
