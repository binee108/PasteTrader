# SPEC-001: Implementation Plan

## Tags

`[SPEC-001]` `[DATABASE]` `[FOUNDATION]` `[BACKEND]`

---

## Implementation Overview

This plan outlines the implementation approach for the Database Foundation Setup, establishing the core database infrastructure for PasteTrader.

---

## Milestones

### Milestone 1: Database Session Infrastructure (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/db/__init__.py` - Database module exports
- `backend/app/db/session.py` - Engine and session factory

**Tasks:**

1. Create database module structure
   - Create `backend/app/db/` directory
   - Initialize module with proper exports

2. Implement async engine creation
   - Configure connection pooling
   - Set up pool_pre_ping for health checks
   - Environment-based configuration (DEBUG mode echo)

3. Implement session factory
   - Create async_sessionmaker with proper settings
   - Configure expire_on_commit=False for detached instance support
   - Implement get_db dependency for FastAPI

4. Create session context manager
   - Async context manager for manual session control
   - Automatic rollback on exception
   - Proper cleanup on exit

**Dependencies:** app/core/config.py must have DATABASE_URL setting

---

### Milestone 2: Base Model and Mixins (Primary Goal)

**Priority:** High

**Deliverables:**
- `backend/app/models/__init__.py` - Model exports
- `backend/app/models/base.py` - Base model and mixins

**Tasks:**

1. Create TimestampMixin
   - `created_at` with server_default=func.now()
   - `updated_at` with onupdate=func.now()
   - Timezone-aware timestamps

2. Create SoftDeleteMixin
   - `deleted_at` nullable timestamp
   - `is_deleted` hybrid property
   - Query filter helper method

3. Create Base model class
   - UUID primary key with server-side default
   - Inherit from DeclarativeBase
   - Include both mixins
   - Configure naming conventions for constraints

**Technical Approach:**
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
```

---

### Milestone 3: Domain Enums (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/app/models/enums.py` - All domain enums

**Tasks:**

1. Define NodeType enum
   - Values: trigger, tool, agent, condition, adapter, parallel, aggregator

2. Define ToolType enum
   - Values: data_fetcher, technical_indicator, market_screener, code_analyzer, notification

3. Define ModelProvider enum
   - Values: anthropic, openai, glm

4. Define ExecutionStatus enum
   - Values: pending, running, completed, failed, skipped, cancelled

5. Define AuthMode enum
   - Values: oauth, standalone, sdk, glm

6. Define TriggerType enum
   - Values: schedule, event, manual

**Technical Approach:**
```python
from enum import Enum

class NodeType(str, Enum):
    TRIGGER = "trigger"
    TOOL = "tool"
    # ...
```

---

### Milestone 4: Alembic Migration Setup (Secondary Goal)

**Priority:** Medium

**Deliverables:**
- `backend/alembic.ini` - Alembic configuration
- `backend/alembic/env.py` - Async migration environment
- `backend/alembic/script.py.mako` - Migration template
- `backend/alembic/versions/` - Migrations directory

**Tasks:**

1. Initialize Alembic structure
   - Create alembic directory
   - Generate initial configuration

2. Configure async env.py
   - Import async engine from app
   - Configure target_metadata from Base
   - Implement run_migrations_offline
   - Implement run_migrations_online with async support

3. Create script template
   - Standard upgrade/downgrade functions
   - Proper docstring format
   - Import statements

4. Create initial migration
   - Empty migration to verify setup
   - Test autogenerate capability

**Technical Approach for async env.py:**
```python
from sqlalchemy.ext.asyncio import async_engine_from_config

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
```

---

### Milestone 5: Integration and Testing (Final Goal)

**Priority:** High

**Deliverables:**
- Test fixtures for database sessions
- Integration tests for session lifecycle

**Tasks:**

1. Create pytest fixtures
   - Test database URL configuration
   - Session fixture with rollback
   - Test database setup/teardown

2. Write unit tests
   - Engine creation tests
   - Session factory tests
   - Mixin behavior tests
   - Enum value tests

3. Write integration tests
   - Full session lifecycle test
   - Soft delete behavior test
   - Timestamp auto-update test

---

## Architecture Design

### Component Diagram

```
backend/
  app/
    core/
      config.py          # DATABASE_URL, settings
    db/
      __init__.py        # exports: engine, async_session, get_db
      session.py         # Engine, sessionmaker, dependency
    models/
      __init__.py        # exports: Base, all models
      base.py            # Base, TimestampMixin, SoftDeleteMixin
      enums.py           # NodeType, ToolType, etc.
  alembic/
    env.py               # Async migration runner
    script.py.mako       # Template
    versions/            # Migration files
  alembic.ini            # Configuration
```

### Dependency Flow

```
config.py
    |
    v
session.py (reads DATABASE_URL)
    |
    v
base.py (uses engine for metadata)
    |
    v
alembic/env.py (imports Base.metadata)
    |
    v
Migration files
```

---

## Technical Approach

### Session Management Pattern

Use FastAPI dependency injection for request-scoped sessions:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Soft Delete Query Pattern

Default queries filter deleted records:

```python
class SoftDeleteMixin:
    @classmethod
    def active(cls):
        return select(cls).where(cls.deleted_at.is_(None))
```

### Enum Storage Strategy

Store enums as VARCHAR for portability:

```python
class NodeType(str, Enum):
    TRIGGER = "trigger"

# In model:
node_type: Mapped[NodeType] = mapped_column(
    String(50),
    nullable=False
)
```

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Alembic async issues | Test migration workflow immediately after setup |
| Pool exhaustion | Configure monitoring, set reasonable pool limits |
| Migration conflicts | Use timestamp-based naming, document process |
| Test isolation | Use transaction rollback pattern in tests |

---

## Output Files Summary

| File Path | Purpose |
|-----------|---------|
| `backend/app/models/__init__.py` | Model module exports |
| `backend/app/models/base.py` | Base model, TimestampMixin, SoftDeleteMixin |
| `backend/app/models/enums.py` | Domain enum definitions |
| `backend/app/db/__init__.py` | Database module exports |
| `backend/app/db/session.py` | Engine, session factory, get_db dependency |
| `backend/alembic.ini` | Alembic main configuration |
| `backend/alembic/env.py` | Async migration environment |
| `backend/alembic/script.py.mako` | Migration script template |

---

## Definition of Done

- [ ] All output files created and properly structured
- [ ] Database engine connects successfully
- [ ] Session lifecycle works correctly (create, use, cleanup)
- [ ] Mixins apply timestamps correctly
- [ ] Soft delete filtering works
- [ ] All enums defined with correct values
- [ ] Alembic can generate and run migrations
- [ ] Unit tests pass with 85%+ coverage
- [ ] Integration tests verify full workflow
- [ ] Code passes ruff linting
- [ ] Type hints complete (mypy passes)

---

## Next Steps After Completion

1. **SPEC-002**: Create core domain models (Workflow, Tool, Agent, Execution)
2. **SPEC-003**: Implement repository pattern for data access
3. Update `backend/app/main.py` to include database lifespan events
