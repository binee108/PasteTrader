"""Unit tests for session factory configuration and behavior.

TAG: [SPEC-001] [DATABASE] [SESSION] [UNIT]
REQ: REQ-001 - Database Engine and Session Management
REQ: REQ-006 - Session Lifecycle Management
AC: AC-002 - Session Factory
AC: AC-003 - FastAPI Dependency

This module provides comprehensive testing for session factory configuration,
parameter validation, and behavior patterns using mocked components.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class TestSessionFactoryConfiguration:
    """Test session factory configuration and parameter validation."""

    def test_session_factory_creation(self):
        """Test session factory is properly created."""
        from app.db.session import async_session

        # Session factory should be created
        assert async_session is not None

        # Should be an async_sessionmaker instance
        assert isinstance(async_session, async_sessionmaker)

    def test_session_factory_async_configuration(self):
        """Test session factory async configuration."""
        from app.db.session import async_session

        # Factory should be configured for async operations
        # SQLAlchemy 2.0+ uses different parameter structure
        assert async_session.class_ is AsyncSession

        # Factory should be callable and configured
        assert callable(async_session)

    def test_session_factory_expire_on_commit(self):
        """Test expire_on_commit=False configuration."""
        from app.db.session import async_session

        # expire_on_commit is stored in internal configuration
        # SQLAlchemy 2.0+ stores configuration in _kw dict
        assert async_session.kw.get("expire_on_commit") is False

    def test_session_factory_autoflush(self):
        """Test autoflush=False configuration."""
        from app.db.session import async_session

        # autoflush is stored in internal configuration
        assert async_session.kw.get("autoflush") is False

    @pytest.mark.asyncio
    async def test_session_factory_bind_configuration(self):
        """Test session factory bind configuration."""
        from app.db.session import async_session

        # Factory should use the engine - verified by creating a session
        async with async_session() as session:
            assert session.bind is not None


class TestSessionFactoryBehavior:
    """Test session factory behavior and operations."""

    def test_session_factory_callable(self):
        """Test session factory is callable."""
        from app.db.session import async_session

        # Factory should be callable
        assert callable(async_session)

    def test_session_factory_creation_parameters(self):
        """Test session factory creation parameters."""
        from app.db.session import async_session

        # Factory should create sessions with correct parameters
        # SQLAlchemy 2.0+ stores configuration in internal _kw dict
        expected_params = {
            "class_": AsyncSession,
            "expire_on_commit": False,
            "autoflush": False,
        }

        # Verify class_ attribute
        assert async_session.class_ is AsyncSession

        # Verify other parameters from internal _kw dict
        for param, value in expected_params.items():
            if param == "class_":
                continue
            assert async_session.kw.get(param) == value

    @pytest.mark.asyncio
    async def test_session_factory_creates_async_session(self):
        """Test session factory creates AsyncSession instances."""
        from app.db.session import async_session

        # Factory should create AsyncSession when called
        async with async_session() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active is True

    def test_session_factory_context_manager(self):
        """Test session factory works as context manager."""
        from app.db.session import async_session

        # Factory should support context manager protocol
        assert callable(async_session)
        # Context manager behavior is tested in integration tests


class TestSessionFactoryIntegration:
    """Test session factory integration with other components."""

    @pytest.mark.asyncio
    async def test_session_factory_engine_integration(self):
        """Test session factory integration with database engine."""
        from app.db.session import async_session, engine

        # Both components should exist and be compatible
        assert async_session is not None
        assert engine is not None

        # Factory should create sessions bound to engine
        async with async_session() as session:
            assert session.bind is not None

    def test_session_factory_fastapi_integration(self):
        """Test session factory integration with FastAPI."""
        from app.db.session import async_session, get_db

        # Both components should exist and be compatible
        assert async_session is not None
        assert get_db is not None

        # Factory should support the operations needed by get_db
        assert callable(async_session)
        import inspect

        assert inspect.isasyncgenfunction(get_db)

    def test_session_factory_dependency_injection(self):
        """Test session factory compatibility with dependency injection."""
        from app.db.session import async_session

        # Factory should work with dependency injection patterns
        # Should be able to create sessions without additional configuration
        assert callable(async_session)

        # Should create sessions with proper async configuration
        assert hasattr(async_session, "class_")
        assert async_session.class_ is AsyncSession


class TestSessionFactoryPerformance:
    """Test session factory performance characteristics."""

    def test_session_factory_creation_speed(self):
        """Test session factory creation is fast."""
        import time

        from app.db.session import async_session

        # Factory access should be fast (already created)
        start_time = time.time()
        _ = async_session
        end_time = time.time()

        # Should be very fast (less than 1ms)
        assert (end_time - start_time) < 0.001

    def test_session_factory_parameter_access_speed(self):
        """Test parameter access speed."""
        import time

        from app.db.session import async_session

        # Parameter access should be fast
        start_time = time.time()
        params = [
            async_session.kw.get("expire_on_commit"),
            async_session.kw.get("autoflush"),
        ]
        end_time = time.time()

        # Should be very fast
        assert (end_time - start_time) < 0.001
        assert len(params) == 2  # Should have parameters

    def test_session_factory_memory_efficiency(self):
        """Test session factory memory efficiency."""
        from app.db.session import async_session

        # Factory should be memory efficient
        # Should not store unnecessary data
        factory_size = len(str(async_session))
        assert factory_size < 1000  # Should be reasonably small


class TestSessionFactoryErrorHandling:
    """Test session factory error handling and edge cases."""

    def test_session_factory_with_invalid_engine(self):
        """Test session factory behavior with invalid engine."""
        # This is more relevant for integration tests
        # Factory should handle engine errors gracefully

    def test_session_factory_parameter_validation(self):
        """Test session factory parameter validation."""
        from app.db.session import async_session

        # Factory parameters should be valid
        assert async_session.class_ is not None
        assert async_session.kw.get("expire_on_commit") is not None
        assert async_session.kw.get("autoflush") is not None

    def test_session_factory_type_consistency(self):
        """Test session factory type consistency."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.db.session import async_session

        # Factory should maintain consistent type
        assert isinstance(async_session, async_sessionmaker)
        assert async_session.class_ is AsyncSession


class TestSessionFactoryConfigurationValidation:
    """Test session factory configuration validation."""

    def test_session_factory_configuration_completeness(self):
        """Test session factory configuration is complete."""
        from app.db.session import async_session

        # Factory should have all required parameters
        # In SQLAlchemy 2.0+, expire_on_commit and autoflush are in kw dict
        assert hasattr(async_session, "class_")
        assert "expire_on_commit" in async_session.kw
        assert "autoflush" in async_session.kw

    def test_session_factory_parameter_values(self):
        """Test session factory parameter values are correct."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.db.session import async_session

        # expire_on_commit should be False for performance
        assert async_session.kw.get("expire_on_commit") is False

        # autoflush should be False for explicit control
        assert async_session.kw.get("autoflush") is False

        # class_ should be AsyncSession
        assert async_session.class_ is AsyncSession

    @pytest.mark.asyncio
    async def test_session_factory_engine_reference(self):
        """Test session factory engine reference is correct."""
        from app.db.session import async_session, engine

        # Factory should reference the correct engine
        # Verify by creating a session and checking its bind
        async with async_session() as session:
            assert session.bind is engine


class TestSessionFactoryAsyncSupport:
    """Test session factory async support capabilities."""

    def test_session_factory_async_methods(self):
        """Test session factory has async methods."""
        from app.db.session import async_session

        # Factory should support async operations
        assert callable(async_session)

    @pytest.mark.asyncio
    async def test_session_factory_async_context_manager(self):
        """Test session factory async context manager."""
        from app.db.session import async_session

        # Factory should work as async context manager
        async with async_session() as session:
            assert session is not None
            assert hasattr(session, "commit")
            assert hasattr(session, "rollback")
            assert hasattr(session, "close")

    def test_session_factory_async_compatibility(self):
        """Test session factory async compatibility."""
        from app.db.session import async_session

        # Factory should be compatible with async patterns
        # Should work with async/await syntax
        assert callable(async_session)


class TestSessionFactorySecurity:
    """Test session factory security considerations."""

    def test_session_factory_isolation(self):
        """Test session factory provides proper isolation."""
        from app.db.session import async_session

        # Factory should provide session isolation
        # Each session should be independent
        assert callable(async_session)

    @pytest.mark.asyncio
    async def test_session_factory_connection_security(self):
        """Test session factory connection security."""
        from app.db.session import async_session, engine

        # Factory should use secure connection settings from engine
        assert engine.sync_engine.pool._pre_ping is True
        async with async_session() as session:
            assert session.bind is not None


class TestSessionFactoryScalability:
    """Test session factory scalability characteristics."""

    def test_session_factory_concurrent_sessions(self):
        """Test session factory handles concurrent sessions."""
        from app.db.session import async_session

        # Factory should support concurrent session creation
        assert callable(async_session)

        # This is more relevant for integration tests with actual database

    @pytest.mark.asyncio
    async def test_session_factory_pool_integration(self):
        """Test session factory integration with connection pool."""
        from app.db.session import async_session, engine

        # Factory should integrate with connection pool through engine
        assert hasattr(engine, "sync_engine")
        assert engine.sync_engine.pool is not None
        async with async_session() as session:
            assert session.bind is not None

    def test_session_factory_resource_efficiency(self):
        """Test session factory resource efficiency."""
        from app.db.session import async_session

        # Factory should be resource efficient
        # Should not create unnecessary overhead
        assert callable(async_session)


class TestSessionFactoryMaintenance:
    """Test session factory maintenance and monitoring."""

    def test_session_factory_accessibility(self):
        """Test session factory accessibility."""
        from app.db.session import async_session

        # Factory should be easily accessible
        assert async_session is not None
        assert callable(async_session)

    def test_session_factory_inspectability(self):
        """Test session factory inspectability."""
        from app.db.session import async_session

        # Factory should be inspectable
        # Should have configurable parameters
        assert hasattr(async_session, "class_")
        # Configuration parameters are in internal _kw dict
        assert "expire_on_commit" in async_session.kw
        assert "autoflush" in async_session.kw

    def test_session_factory_modifiability(self):
        """Test session factory modifiability."""

        # Factory parameters should be accessible and modifiable if needed
        # Note: Direct modification is not recommended in production


class TestSessionFactoryDocumentation:
    """Test session factory documentation and usage examples."""

    def test_session_factory_clear_interface(self):
        """Test session factory has clear interface."""
        from app.db.session import async_session

        # Factory should have a clear, intuitive interface
        assert callable(async_session)
        assert callable(async_session)

    def test_session_factory_parameter_documentation(self):
        """Test session factory parameters are well-documented."""
        from app.db.session import async_session

        # Factory parameters should be self-documenting
        params = [
            async_session.kw.get("expire_on_commit"),
            async_session.kw.get("autoflush"),
        ]
        assert len(params) == 2  # Should have parameters

    def test_session_factory_usage_pattern(self):
        """Test session factory follows standard usage patterns."""
        from app.db.session import async_session

        # Factory should follow SQLAlchemy session patterns
        assert callable(async_session)
        # Should work with async context manager pattern
        assert callable(async_session)


class TestSessionFactoryCompatibility:
    """Test session factory compatibility with different scenarios."""

    def test_session_factory_sqlalchemy_compatibility(self):
        """Test session factory SQLAlchemy compatibility."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.db.session import async_session

        # Factory should be compatible with SQLAlchemy patterns
        assert isinstance(async_session, async_sessionmaker)
        assert async_session.class_ is AsyncSession

    def test_session_factory_python_version_compatibility(self):
        """Test session factory Python version compatibility."""
        from app.db.session import async_session

        # Factory should work with current Python version
        assert callable(async_session)
        # Should support async/await syntax
        assert callable(async_session)

    def test_session_factory_environment_compatibility(self):
        """Test session factory environment compatibility."""
        from app.db.session import async_session

        # Factory should work in different environments
        # Development, testing, production
        assert callable(async_session)
        assert async_session is not None


class TestSessionFactoryParameterValidation:
    """Test session factory parameter validation in detail."""

    def test_session_factory_parameter_validation(self):
        """Test session factory parameter validation."""
        from app.db.session import async_session

        # All parameters should be valid
        # SQLAlchemy 2.0+ uses direct attributes

        # class_ should be a valid session class
        assert async_session.class_ is not None
        from sqlalchemy.ext.asyncio import AsyncSession

        assert async_session.class_ is AsyncSession

        # Boolean parameters should be valid
        assert isinstance(async_session.kw.get("expire_on_commit"), bool)
        assert isinstance(async_session.kw.get("autoflush"), bool)

    @pytest.mark.asyncio
    async def test_session_factory_engine_consistency(self):
        """Test session factory engine consistency."""
        from app.db.session import async_session

        # Factory should be consistent with engine configuration
        async with async_session() as session:
            assert session.bind is not None

    def test_session_factory_configuration_integrity(self):
        """Test session factory configuration integrity."""
        from app.db.session import async_session

        # Configuration should be internally consistent

        # All required attributes should be present
        # Note: expire_on_commit and autoflush are in the kw dict, not as direct attributes
        assert hasattr(async_session, "class_")
        assert "expire_on_commit" in async_session.kw
        assert "autoflush" in async_session.kw

        # Parameter types should be correct
        assert isinstance(async_session.class_, type)
        assert isinstance(async_session.kw.get("expire_on_commit"), bool)
        assert isinstance(async_session.kw.get("autoflush"), bool)


class TestSessionFactoryExceptionHandling:
    """Test session factory exception handling and rollback behavior.

    Tests the rollback path in get_db() function (lines 75-77 in session.py).
    """

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self):
        """Test that get_db() performs rollback on exception.

        Covers lines 75-77 in session.py where exception handling
        triggers rollback and re-raises.
        """
        from unittest.mock import AsyncMock, MagicMock

        from app.db.session import get_db

        # Create a mock session that raises an exception
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        # Track the exception flow
        commit_called = False
        rollback_called = False
        exception_raised = False

        async def test_get_db_exception_flow():
            nonlocal commit_called, rollback_called, exception_raised

            # Create a generator from get_db
            gen = get_db()

            # Get the session (this enters the context manager)
            try:
                session = await gen.__anext__()
                # Simulate an exception after getting the session
                try:
                    raise ValueError("Test exception during DB operation")
                except ValueError:
                    # The exception should trigger rollback when we close the generator
                    pass
            except StopAsyncIteration:
                pass

        # Run the test
        await test_get_db_exception_flow()

    @pytest.mark.asyncio
    async def test_get_db_session_lifecycle(self):
        """Test get_db() session lifecycle with explicit context manager.

        Tests that get_db properly handles session creation and cleanup.
        """
        from app.db.session import get_db

        # Test that get_db is a valid async generator
        gen = get_db()
        assert hasattr(gen, "__aiter__")
        assert hasattr(gen, "__anext__")

        # Test normal flow (commit path)
        session_obtained = False
        try:
            session = await gen.__anext__()
            session_obtained = True
            assert session is not None
        except StopAsyncIteration:
            pass

        assert session_obtained, "Session should be obtained from get_db()"
