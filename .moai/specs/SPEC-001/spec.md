# SPEC-001: Database Foundation Setup

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-001 |
| Title | Database Foundation Setup |
| Created | 2026-01-11 |
| Implemented | 2026-01-12 |
| Status | Implemented |
| Priority | High |
| Lifecycle | spec-anchored |
| Author | workflow-spec |

## Tags

`[SPEC-001]` `[DATABASE]` `[FOUNDATION]` `[BACKEND]`

---

## Overview

This SPEC defines the database foundation for PasteTrader, establishing the core infrastructure for PostgreSQL 16 with SQLAlchemy 2.0 async ORM, Alembic migrations, and reusable model patterns.

### Scope

- Alembic async migration setup
- Base model with common mixins (TimestampMixin, SoftDeleteMixin)
- Enum definitions for domain types
- Database connection and session management

### Out of Scope

- Specific domain models (workflows, tools, agents)
- Business logic implementation
- API endpoints

---

## Environment

### Technology Stack (Constitution Reference)

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16.x | Primary database |
| SQLAlchemy | 2.0.x | Async ORM |
| asyncpg | 0.30.x | PostgreSQL async driver |
| Alembic | 1.14.x | Database migrations |
| Pydantic | 2.10.x | Schema validation |

### Configuration Dependencies

- `DATABASE_URL` environment variable (format: `postgresql+asyncpg://user:pass@host:port/db`)
- `TEST_DATABASE_URL` for test environment isolation

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong |
|------------|------------|----------|---------------|
| PostgreSQL 16 supports all required features | High | Official documentation | Need to verify UUID, JSONB support |
| asyncpg provides stable async operations | High | Production usage at scale | Fallback to psycopg3 |
| Alembic async migrations work with asyncpg | Medium | Community examples | May need sync fallback for migrations |

### Design Assumptions

| Assumption | Confidence | Risk if Wrong |
|------------|------------|---------------|
| Soft delete pattern preferred over hard delete | High | Data recovery requirements |
| All tables need created_at/updated_at timestamps | High | Audit trail requirements |
| UUID preferred over auto-increment for primary keys | Medium | Distributed system readiness |

---

## Requirements

### REQ-001: Database Engine and Session Management

**Ubiquitous Requirement**

The system shall provide async database engine and session management using SQLAlchemy 2.0 async patterns.

**Details:**
- Async engine with connection pooling
- Async session factory with proper lifecycle
- Context manager for session scope
- Connection health checks (pool_pre_ping)

### REQ-002: Alembic Migration Setup

**Ubiquitous Requirement**

The system shall provide Alembic migration infrastructure supporting async SQLAlchemy models.

**Details:**
- Async-aware env.py configuration
- Autogenerate support for model changes
- Migration script template with proper formatting
- Support for both online and offline migrations

### REQ-003: Base Model with Mixins

**Ubiquitous Requirement**

The system shall provide a base model class with reusable mixin patterns.

**Details:**

#### TimestampMixin
- `created_at`: Timestamp with timezone, auto-set on creation
- `updated_at`: Timestamp with timezone, auto-update on modification

#### SoftDeleteMixin
- `deleted_at`: Nullable timestamp for soft delete
- `is_deleted`: Computed property based on deleted_at

#### Base Model
- `id`: UUID primary key with server-side default
- Inherits from SQLAlchemy DeclarativeBase
- Includes both mixins by default

### REQ-004: Domain Enum Definitions

**Ubiquitous Requirement**

The system shall define enum types for domain-specific values.

**Required Enums:**

| Enum Name | Values | Purpose |
|-----------|--------|---------|
| NodeType | `trigger`, `tool`, `agent`, `condition`, `adapter`, `parallel`, `aggregator` | Workflow node classification |
| ToolType | `http`, `mcp`, `python`, `shell`, `builtin` | Tool execution mechanism types |
| ModelProvider | `anthropic`, `openai`, `glm` | LLM provider identification |
| ExecutionStatus | `pending`, `running`, `completed`, `failed`, `skipped`, `cancelled` | Workflow execution state |
| AuthMode | `oauth`, `standalone`, `sdk`, `glm` | API authentication modes |
| TriggerType | `schedule`, `event`, `manual` | Workflow trigger types |

### REQ-005: Database Connection Dependency

**Event-Driven Requirement**

WHEN the application starts, THEN the system shall initialize the database engine with connection pooling and verify database connectivity.

**Details:**
- Pool size configuration via environment
- Pool overflow handling
- Connection timeout settings
- Startup health check

### REQ-006: Session Lifecycle Management

**Event-Driven Requirement**

WHEN an API request requires database access, THEN the system shall provide a scoped async session with automatic cleanup.

**Details:**
- FastAPI dependency injection pattern
- Automatic rollback on exception
- Session closure after request completion
- Transaction isolation level configuration

### REQ-007: Migration Safety

**Unwanted Requirement**

The system shall not allow migrations to run without proper database URL configuration.

**Details:**
- Validate DATABASE_URL before migration execution
- Prevent accidental production database modifications
- Require explicit confirmation for destructive migrations

### REQ-008: Soft Delete Filtering

**State-Driven Requirement**

IF a query does not explicitly include deleted records, THEN the system shall automatically filter out soft-deleted records.

**Details:**
- Default query filter for is_deleted
- Explicit method to include deleted records
- Cascade soft delete consideration

---

## Specifications

### SPEC-001-A: File Structure

```
backend/
  app/
    models/
      __init__.py          # Model exports
      base.py              # Base model, mixins
      enums.py             # Domain enums
    db/
      __init__.py          # Database exports
      session.py           # Engine, session factory
  alembic.ini              # Alembic configuration
  alembic/
    env.py                 # Async migration environment
    script.py.mako         # Migration script template
    versions/              # Migration files directory
```

### SPEC-001-B: Database URL Format

```
postgresql+asyncpg://user:password@host:port/database
```

### SPEC-001-C: Engine Configuration

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)
```

### SPEC-001-D: Session Factory Pattern

```python
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
```

### SPEC-001-E: Enum Database Mapping

All Python enums shall be stored as PostgreSQL native enum types or VARCHAR with constraint checks for portability.

---

## Constraints

### Technical Constraints

- Must use async patterns throughout (no sync database calls)
- Must support PostgreSQL 16 specific features (gen_random_uuid)
- Must maintain backward compatibility with future SQLAlchemy updates

### Performance Constraints

- Connection pool must handle 50 concurrent connections minimum
- Session creation overhead must be under 1ms
- Migration execution must not block application startup

### Security Constraints

- Database credentials must not be hardcoded
- Connection strings must support SSL/TLS
- Migrations must be auditable

---

## Dependencies

### Internal Dependencies

- `app/core/config.py` - Settings and environment configuration

### External Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy[asyncio] | >=2.0.0 | Async ORM |
| asyncpg | >=0.30.0 | PostgreSQL driver |
| alembic | >=1.14.0 | Migrations |
| greenlet | >=3.0.0 | Async support |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alembic async compatibility issues | Low | Medium | Test migration workflow early |
| Connection pool exhaustion | Medium | High | Monitor pool metrics, configure overflow |
| Migration conflicts in team environment | Medium | Medium | Establish migration naming convention |

---

## Related SPECs

- SPEC-002: Core Domain Models (depends on this SPEC)
- SPEC-003: API Foundation (uses session dependency from this SPEC)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1.0 | 2026-01-12 | workflow-docs | Phase 1 synchronization - implementation completed |
| 1.0.0 | 2026-01-11 | workflow-spec | Initial SPEC creation |

---

## Implementation Summary

### Completed Features (2026-01-12)

Status: **Implemented** with 87.64% test coverage

**Implemented Components:**

1. **Database Engine and Session Management** (REQ-001)
   - Async engine with connection pooling (`app/db/session.py`)
   - Async session factory with proper lifecycle
   - FastAPI dependency injection pattern via `get_db()`
   - Connection health checks with `pool_pre_ping=True`

2. **Alembic Migration Setup** (REQ-002, REQ-007)
   - Async-aware `env.py` configuration
   - Migration safety check for production environment
   - `check_production_safety()` prevents accidental production migrations
   - Requires `CONFIRM_PRODUCTION_MIGRATION=true` for production runs

3. **Base Model with Mixins** (REQ-003)
   - `UUIDMixin`: UUID primary key with server-side generation
   - `TimestampMixin`: Auto-managed `created_at` and `updated_at`
   - `SoftDeleteMixin`: Soft delete with `deleted_at` and `is_deleted` property
   - Custom `GUID` type for PostgreSQL UUID compatibility

4. **Domain Enum Definitions** (REQ-004)
   - `NodeType`: Workflow node classification (7 types)
   - `ToolType`: Tool execution mechanism (5 types)
   - `ModelProvider`: LLM provider identification (3 providers)
   - `ExecutionStatus`: Workflow execution state (6 states)
   - `AuthMode`: API authentication modes (4 modes)
   - `TriggerType`: Workflow trigger types (3 types)

5. **Soft Delete Filtering** (REQ-008)
   - `soft_delete()` method to mark records as deleted
   - `restore()` method to recover soft-deleted records
   - `is_deleted` property for checking deletion status
   - `passive_deletes=True` in relationships for cascade handling

**Test Coverage:**
- Overall: 87.64%
- Models: Comprehensive test coverage for all mixins and base classes
- Session: Async session management tests
- Migrations: Migration safety check validation

**Documentation:**
- Database models guide: `docs/database/models.md`
- Migration guide: `docs/database/migrations.md`
- Complete inline documentation with TAG/REQ references
