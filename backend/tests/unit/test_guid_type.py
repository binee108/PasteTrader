"""Tests for GUID type decorator - RED Phase tests.

TAG: [SPEC-001] [DATABASE] [GUID] [TEST]
REQ: REQ-003 - Base Model with Mixins

Additional tests to improve coverage for GUID.process_bind_param function.
Targets lines 32, 42, 56 in base.py.
"""

import uuid

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.base import GUID


class Base(DeclarativeBase):
    """Test base class."""


class TestGUIDProcessBindParam:
    """Test GUID.process_bind_param method.

    These tests target lines 32, 42, 56 in base.py which had missing coverage.
    """

    def test_process_bind_param_with_postgresql_dialect(self):
        """Test process_bind_param returns None for PostgreSQL.

        PostgreSQL handles UUID natively, so returns None.
        Targets line 32: return None
        """
        from sqlalchemy.dialects import postgresql

        guid_type = GUID()
        dialect = postgresql.dialect()

        result = guid_type.process_bind_param(uuid.uuid4(), dialect)

        # PostgreSQL handles UUID natively, returns None
        assert result is None

    def test_process_bind_param_with_uuid_object_sqlite(self):
        """Test process_bind_param with UUID object for non-PostgreSQL.

        Should convert UUID to string.
        Targets line 42: return str(value)
        """
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()
        test_uuid = uuid.uuid4()

        result = guid_type.process_bind_param(test_uuid, dialect)

        assert result == str(test_uuid)
        assert isinstance(result, str)

    def test_process_bind_param_with_uuid_string_sqlite(self):
        """Test process_bind_param with UUID string for non-PostgreSQL.

        Should convert string back to UUID then to string again.
        Targets line 56: return str(uuid.UUID(value))
        """
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()
        uuid_string = "550e8400-e29b-41d4-a716-446655440000"

        result = guid_type.process_bind_param(uuid_string, dialect)

        assert result == uuid_string
        assert isinstance(result, str)

    def test_process_bind_param_with_none_returns_none(self):
        """Test process_bind_param with None returns None."""
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()

        result = guid_type.process_bind_param(None, dialect)

        assert result is None

    def test_process_bind_param_with_invalid_uuid_string(self):
        """Test process_bind_param with invalid UUID string raises error."""
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()

        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            guid_type.process_bind_param("invalid-uuid", dialect)


class TestGUIDProcessResultValue:
    """Test GUID.process_result_value method."""

    def test_process_result_value_with_none(self):
        """Test process_result_value with None returns None."""
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()

        result = guid_type.process_result_value(None, dialect)

        assert result is None

    def test_process_result_value_with_uuid_string(self):
        """Test process_result_value converts string to UUID."""
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()
        uuid_string = "550e8400-e29b-41d4-a716-446655440000"

        result = guid_type.process_result_value(uuid_string, dialect)

        assert isinstance(result, uuid.UUID)
        assert str(result) == uuid_string

    def test_process_result_value_with_uuid_object(self):
        """Test process_result_value with UUID object returns as-is."""
        from sqlalchemy.dialects import sqlite

        guid_type = GUID()
        dialect = sqlite.dialect()
        test_uuid = uuid.uuid4()

        result = guid_type.process_result_value(test_uuid, dialect)

        assert isinstance(result, uuid.UUID)
        assert result == test_uuid


class TestGUIDIntegration:
    """Integration tests for GUID with actual table."""

    def test_guid_column_with_sqlite(self):
        """Test GUID column works with SQLite."""

        engine = create_engine("sqlite:///:memory:")

        class TestModel(Base):
            __tablename__ = "test_guid"

            id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True)
            name: Mapped[str] = mapped_column(String(50))

        Base.metadata.create_all(engine)

        # Insert a record
        test_uuid = uuid.uuid4()
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            model = TestModel(id=test_uuid, name="Test")
            session.add(model)
            session.commit()

            # Query back
            retrieved = session.query(TestModel).first()
            assert retrieved.id == test_uuid
            assert isinstance(retrieved.id, uuid.UUID)
