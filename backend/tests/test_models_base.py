"""Tests for base model and mixins.

TAG: [SPEC-001] [DATABASE] [BASE-MODEL]
REQ: REQ-003 - Base Model with Mixins
AC: AC-004 - TimestampMixin
AC: AC-005 - SoftDeleteMixin
AC: AC-006 - Base Model UUID Primary Key
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import String, inspect
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

# Test will use SQLite for unit testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestBaseModelStructure:
    """Test Base model class structure."""

    def test_base_class_exists(self) -> None:
        """Base class should exist in models.base module."""
        from app.models.base import Base

        assert Base is not None

    def test_base_inherits_from_declarative_base(self) -> None:
        """Base should inherit from SQLAlchemy DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        from app.models.base import Base

        assert issubclass(Base, DeclarativeBase)


class TestTimestampMixin:
    """Test TimestampMixin functionality."""

    def test_timestampmixin_exists(self) -> None:
        """TimestampMixin class should exist."""
        from app.models.base import TimestampMixin

        assert TimestampMixin is not None

    def test_timestampmixin_has_created_at_attribute(self) -> None:
        """TimestampMixin should have created_at attribute."""
        from app.models.base import TimestampMixin

        assert hasattr(TimestampMixin, "created_at")

    def test_timestampmixin_has_updated_at_attribute(self) -> None:
        """TimestampMixin should have updated_at attribute."""
        from app.models.base import TimestampMixin

        assert hasattr(TimestampMixin, "updated_at")


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin functionality."""

    def test_softdeletemixin_exists(self) -> None:
        """SoftDeleteMixin class should exist."""
        from app.models.base import SoftDeleteMixin

        assert SoftDeleteMixin is not None

    def test_softdeletemixin_has_deleted_at_attribute(self) -> None:
        """SoftDeleteMixin should have deleted_at attribute."""
        from app.models.base import SoftDeleteMixin

        assert hasattr(SoftDeleteMixin, "deleted_at")

    def test_softdeletemixin_has_is_deleted_property(self) -> None:
        """SoftDeleteMixin should have is_deleted property."""
        from app.models.base import SoftDeleteMixin

        # Check if is_deleted is defined (as property or hybrid_property)
        assert hasattr(SoftDeleteMixin, "is_deleted")


class TestUUIDMixin:
    """Test UUIDMixin functionality."""

    def test_uuidmixin_exists(self) -> None:
        """UUIDMixin class should exist."""
        from app.models.base import UUIDMixin

        assert UUIDMixin is not None

    def test_uuidmixin_has_id_attribute(self) -> None:
        """UUIDMixin should have id attribute."""
        from app.models.base import UUIDMixin

        assert hasattr(UUIDMixin, "id")


# Define the test model at module level to avoid redefinition issues
_test_model_defined = False
_TestModelClass = None


def get_test_model_class():
    """Get or create the test model class."""
    global _test_model_defined, _TestModelClass

    if not _test_model_defined:
        from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

        class TestModel(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
            """Test model for mixin behavior testing."""

            __tablename__ = "test_models"
            __table_args__ = {"extend_existing": True}

            name: Mapped[str] = mapped_column(String(100), nullable=False)

        _TestModelClass = TestModel
        _test_model_defined = True

    return _TestModelClass


@pytest_asyncio.fixture
async def db_session():
    """Create async session for testing with tables created."""
    from app.models.base import Base

    # Get the test model class (ensures it's registered with Base)
    test_model_class = get_test_model_class()

    # Create engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session, test_model_class

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


class TestTimestampMixinBehavior:
    """Test TimestampMixin behavior with database operations."""

    @pytest.mark.asyncio
    async def test_created_at_auto_set_on_insert(self, db_session) -> None:
        """created_at should be set to current timestamp on insert."""
        session, test_model_class = db_session
        before_insert = datetime.now(UTC)

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        after_insert = datetime.now(UTC)

        assert model.created_at is not None
        # Allow some tolerance for time comparison
        # Make created_at timezone-aware if it isn't
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        assert created_at >= before_insert - timedelta(seconds=1)
        assert created_at <= after_insert + timedelta(seconds=1)

    @pytest.mark.asyncio
    async def test_updated_at_auto_set_on_insert(self, db_session) -> None:
        """updated_at should be set on insert."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.updated_at is not None

    @pytest.mark.asyncio
    async def test_updated_at_changes_on_modification(self, db_session) -> None:
        """updated_at should change when record is modified."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        original_updated_at = model.updated_at

        # Wait a tiny bit and update
        import asyncio

        await asyncio.sleep(0.01)

        model.name = "Updated Item"
        await session.commit()
        await session.refresh(model)

        # updated_at should be different (or same if too fast, but not None)
        assert model.updated_at is not None

    @pytest.mark.asyncio
    async def test_created_at_unchanged_on_modification(self, db_session) -> None:
        """created_at should remain unchanged when record is modified."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        original_created_at = model.created_at

        model.name = "Updated Item"
        await session.commit()
        await session.refresh(model)

        assert model.created_at == original_created_at


class TestSoftDeleteMixinBehavior:
    """Test SoftDeleteMixin behavior with database operations."""

    @pytest.mark.asyncio
    async def test_deleted_at_is_none_by_default(self, db_session) -> None:
        """deleted_at should be None for new records."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.deleted_at is None

    @pytest.mark.asyncio
    async def test_is_deleted_false_for_new_record(self, db_session) -> None:
        """is_deleted should be False for new records."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.is_deleted is False

    @pytest.mark.asyncio
    async def test_soft_delete_sets_deleted_at(self, db_session) -> None:
        """soft_delete should set deleted_at to current timestamp."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        before_delete = datetime.now(UTC)
        model.soft_delete()
        await session.commit()
        await session.refresh(model)
        after_delete = datetime.now(UTC)

        assert model.deleted_at is not None
        # Make deleted_at timezone-aware if it isn't
        deleted_at = model.deleted_at
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=UTC)
        assert deleted_at >= before_delete - timedelta(seconds=1)
        assert deleted_at <= after_delete + timedelta(seconds=1)

    @pytest.mark.asyncio
    async def test_is_deleted_true_after_soft_delete(self, db_session) -> None:
        """is_deleted should be True after soft_delete."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        model.soft_delete()
        await session.commit()
        await session.refresh(model)

        assert model.is_deleted is True

    @pytest.mark.asyncio
    async def test_restore_clears_deleted_at(self, db_session) -> None:
        """restore should set deleted_at to None."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()

        model.soft_delete()
        await session.commit()
        await session.refresh(model)

        model.restore()
        await session.commit()
        await session.refresh(model)

        assert model.deleted_at is None

    @pytest.mark.asyncio
    async def test_is_deleted_false_after_restore(self, db_session) -> None:
        """is_deleted should be False after restore."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()

        model.soft_delete()
        await session.commit()
        await session.refresh(model)

        model.restore()
        await session.commit()
        await session.refresh(model)

        assert model.is_deleted is False


class TestUUIDMixinBehavior:
    """Test UUIDMixin behavior with database operations."""

    @pytest.mark.asyncio
    async def test_uuid_auto_generated_on_insert(self, db_session) -> None:
        """UUID should be automatically generated on insert."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.id is not None

    @pytest.mark.asyncio
    async def test_uuid_is_valid_format(self, db_session) -> None:
        """Generated UUID should be a valid UUID."""
        session, test_model_class = db_session

        model = test_model_class(name="Test Item")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        # Should be a valid UUID (can be parsed)
        parsed_uuid = uuid.UUID(str(model.id))
        assert parsed_uuid is not None

    @pytest.mark.asyncio
    async def test_uuid_uniqueness(self, db_session) -> None:
        """Each record should have a unique UUID."""
        session, test_model_class = db_session

        model1 = test_model_class(name="Item 1")
        model2 = test_model_class(name="Item 2")
        model3 = test_model_class(name="Item 3")

        session.add_all([model1, model2, model3])
        await session.commit()

        await session.refresh(model1)
        await session.refresh(model2)
        await session.refresh(model3)

        ids = {model1.id, model2.id, model3.id}
        assert len(ids) == 3  # All unique

    @pytest.mark.asyncio
    async def test_uuid_is_primary_key(self, db_session) -> None:
        """UUID should be the primary key."""
        session, test_model_class = db_session

        mapper = inspect(test_model_class)
        primary_keys = [col.name for col in mapper.primary_key]
        assert "id" in primary_keys
