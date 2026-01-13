# SPEC-001: Acceptance Criteria

## Tags

`[SPEC-001]` `[DATABASE]` `[FOUNDATION]` `[BACKEND]`

---

## Acceptance Criteria Overview

This document defines the acceptance criteria for Database Foundation Setup using Given-When-Then (Gherkin) format.

---

## Feature: Database Session Management

### AC-001: Async Engine Creation

```gherkin
Feature: Async Database Engine

  Scenario: Create async engine with valid configuration
    Given a valid DATABASE_URL environment variable
    When the application initializes the database engine
    Then an async engine should be created
    And connection pooling should be configured
    And pool_pre_ping should be enabled

  Scenario: Engine configuration from settings
    Given DEBUG mode is enabled in settings
    When the engine is created
    Then SQL echo should be enabled
    And query logging should output to console

  Scenario: Engine fails with invalid URL
    Given an invalid DATABASE_URL format
    When the application attempts to create the engine
    Then an appropriate error should be raised
    And the error message should indicate URL format issue
```

### AC-002: Session Factory

```gherkin
Feature: Async Session Factory

  Scenario: Create session factory
    Given a configured async engine
    When the session factory is initialized
    Then it should use AsyncSession class
    And expire_on_commit should be False
    And autoflush should be False

  Scenario: Session from factory
    Given an initialized session factory
    When a new session is requested
    Then a valid AsyncSession should be returned
    And the session should be bound to the engine
```

### AC-003: FastAPI Dependency

```gherkin
Feature: Database Dependency Injection

  Scenario: Get database session in request
    Given a FastAPI application with database dependency
    When an API endpoint requires database access
    Then a session should be provided via Depends(get_db)
    And the session should be request-scoped

  Scenario: Session cleanup on success
    Given an active database session in a request
    When the request completes successfully
    Then the session should be committed
    And the session should be closed

  Scenario: Session rollback on exception
    Given an active database session in a request
    When an exception occurs during request processing
    Then the session should be rolled back
    And the exception should be propagated
    And the session should be closed
```

---

## Feature: Base Model and Mixins

### AC-004: TimestampMixin

```gherkin
Feature: Timestamp Mixin

  Scenario: Auto-set created_at on insert
    Given a model using TimestampMixin
    When a new record is inserted
    Then created_at should be set to current timestamp
    And created_at should include timezone information

  Scenario: Auto-update updated_at on modification
    Given an existing record with TimestampMixin
    When the record is modified and saved
    Then updated_at should be updated to current timestamp
    And created_at should remain unchanged

  Scenario: Timestamps are timezone-aware
    Given a model with timestamp fields
    When timestamps are retrieved from database
    Then they should include timezone information (UTC)
```

### AC-005: SoftDeleteMixin

```gherkin
Feature: Soft Delete Mixin

  Scenario: Soft delete a record
    Given an existing record with SoftDeleteMixin
    When soft_delete() is called on the record
    Then deleted_at should be set to current timestamp
    And is_deleted property should return True

  Scenario: Query excludes soft-deleted records by default
    Given a table with both active and soft-deleted records
    When a standard query is executed
    Then only records with deleted_at IS NULL should be returned

  Scenario: Query includes soft-deleted records explicitly
    Given a table with both active and soft-deleted records
    When a query explicitly includes deleted records
    Then all records should be returned regardless of deleted_at

  Scenario: Restore soft-deleted record
    Given a soft-deleted record
    When restore() is called on the record
    Then deleted_at should be set to NULL
    And is_deleted property should return False
```

### AC-006: Base Model UUID Primary Key

```gherkin
Feature: Base Model UUID Primary Key

  Scenario: UUID generated on insert
    Given a model inheriting from Base
    When a new record is created without specifying id
    Then a UUID should be automatically generated
    And the UUID should be a valid UUID v4 format

  Scenario: UUID uniqueness
    Given multiple records of the same model
    When records are created
    Then each record should have a unique UUID

  Scenario: UUID is server-side generated
    Given a model with UUID primary key
    When inspecting the column definition
    Then server_default should use PostgreSQL gen_random_uuid()
```

---

## Feature: Domain Enums

### AC-007: Enum Definitions

```gherkin
Feature: Domain Enum Definitions

  Scenario Outline: Enum has required values
    Given the <enum_name> enum
    Then it should contain the value <value>
    And the value should be a string type

    Examples: NodeType
      | enum_name | value      |
      | NodeType  | trigger    |
      | NodeType  | tool       |
      | NodeType  | agent      |
      | NodeType  | condition  |
      | NodeType  | adapter    |
      | NodeType  | parallel   |
      | NodeType  | aggregator |

    Examples: ToolType
      | enum_name | value              |
      | ToolType  | data_fetcher       |
      | ToolType  | technical_indicator|
      | ToolType  | market_screener    |
      | ToolType  | code_analyzer      |
      | ToolType  | notification       |

    Examples: ModelProvider
      | enum_name      | value     |
      | ModelProvider  | anthropic |
      | ModelProvider  | openai    |
      | ModelProvider  | glm       |

    Examples: ExecutionStatus
      | enum_name       | value     |
      | ExecutionStatus | pending   |
      | ExecutionStatus | running   |
      | ExecutionStatus | completed |
      | ExecutionStatus | failed    |
      | ExecutionStatus | skipped   |
      | ExecutionStatus | cancelled |

    Examples: AuthMode
      | enum_name | value      |
      | AuthMode  | oauth      |
      | AuthMode  | standalone |
      | AuthMode  | sdk        |
      | AuthMode  | glm        |

    Examples: TriggerType
      | enum_name   | value    |
      | TriggerType | schedule |
      | TriggerType | event    |
      | TriggerType | manual   |

  Scenario: Enum values are string-compatible
    Given any domain enum
    When used in string context
    Then it should serialize to its string value
    And it should deserialize from its string value
```

---

## Feature: Alembic Migration Setup

### AC-008: Alembic Configuration

```gherkin
Feature: Alembic Configuration

  Scenario: alembic.ini exists with correct settings
    Given the backend directory
    When checking for alembic.ini
    Then the file should exist
    And script_location should point to alembic directory
    And sqlalchemy.url should reference environment variable

  Scenario: Alembic directory structure
    Given the alembic directory
    Then env.py should exist
    And script.py.mako should exist
    And versions directory should exist
```

### AC-009: Async Migration Environment

```gherkin
Feature: Async Migration Environment

  Scenario: env.py supports async migrations
    Given the alembic/env.py file
    When inspecting the configuration
    Then it should import async engine utilities
    And it should use asyncio.run for online migrations

  Scenario: Autogenerate detects model changes
    Given a model change in app/models
    When running alembic revision --autogenerate
    Then a new migration file should be created
    And it should contain the detected changes

  Scenario: Migration runs successfully
    Given a pending migration
    When running alembic upgrade head
    Then the migration should complete without errors
    And the database schema should be updated
```

---

## Feature: Integration Tests

### AC-010: Full Session Lifecycle

```gherkin
Feature: Database Session Lifecycle

  Scenario: Complete CRUD operation
    Given an initialized database with Base models
    When creating, reading, updating, and deleting a record
    Then all operations should complete successfully
    And timestamps should be updated appropriately
    And soft delete should work as expected

  Scenario: Transaction isolation
    Given two concurrent sessions
    When one session modifies data within a transaction
    Then the other session should not see uncommitted changes
    And after commit, changes should be visible
```

### AC-011: Connection Pool Behavior

```gherkin
Feature: Connection Pool Management

  Scenario: Pool handles concurrent requests
    Given a configured connection pool
    When 10 concurrent database operations are executed
    Then all operations should complete successfully
    And connection count should not exceed pool_size + max_overflow

  Scenario: Pool recovers from connection failure
    Given an active connection pool
    When a connection becomes stale
    Then pool_pre_ping should detect the issue
    And a new connection should be established
```

---

## Quality Gate Criteria

### Code Quality

| Criterion | Requirement |
|-----------|-------------|
| Test Coverage | >= 85% line coverage |
| Linting | Zero ruff errors |
| Type Hints | Complete type annotations |
| Documentation | All public functions documented |

### Functional Requirements

| Requirement | Verification Method |
|-------------|---------------------|
| REQ-001: Session Management | AC-001, AC-002, AC-003 |
| REQ-002: Alembic Setup | AC-008, AC-009 |
| REQ-003: Base Model/Mixins | AC-004, AC-005, AC-006 |
| REQ-004: Domain Enums | AC-007 |
| REQ-005: Connection Dependency | AC-001, AC-010 |
| REQ-006: Session Lifecycle | AC-003, AC-010 |
| REQ-007: Migration Safety | AC-009 |
| REQ-008: Soft Delete Filtering | AC-005 |

### Performance Requirements

| Metric | Target |
|--------|--------|
| Session creation time | < 1ms |
| Connection establishment | < 100ms |
| Pool checkout time | < 10ms |

---

## Test Scenarios

### Unit Tests

```python
# tests/unit/test_models/test_base.py
class TestTimestampMixin:
    def test_created_at_auto_set(self): ...
    def test_updated_at_auto_update(self): ...
    def test_timestamps_are_timezone_aware(self): ...

class TestSoftDeleteMixin:
    def test_soft_delete_sets_deleted_at(self): ...
    def test_is_deleted_property(self): ...
    def test_restore_clears_deleted_at(self): ...

class TestBaseModel:
    def test_uuid_auto_generated(self): ...
    def test_uuid_is_valid_format(self): ...

# tests/unit/test_models/test_enums.py
class TestNodeType:
    def test_all_values_exist(self): ...
    def test_string_serialization(self): ...

# Similar for other enums...

# tests/unit/test_db/test_session.py
class TestEngineCreation:
    def test_engine_created_with_valid_url(self): ...
    def test_pool_pre_ping_enabled(self): ...

class TestSessionFactory:
    def test_session_factory_configuration(self): ...
    def test_session_creation(self): ...
```

### Integration Tests

```python
# tests/integration/test_db/test_session_lifecycle.py
class TestSessionLifecycle:
    async def test_commit_on_success(self): ...
    async def test_rollback_on_exception(self): ...
    async def test_session_cleanup(self): ...

class TestCRUDOperations:
    async def test_create_read_update_delete(self): ...
    async def test_soft_delete_workflow(self): ...

# tests/integration/test_alembic/test_migrations.py
class TestMigrations:
    def test_migration_upgrade(self): ...
    def test_migration_downgrade(self): ...
    def test_autogenerate_detects_changes(self): ...
```

---

## Verification Methods

| Method | Tool | Description |
|--------|------|-------------|
| Unit Testing | pytest | Isolated component tests |
| Integration Testing | pytest-asyncio | Full workflow tests |
| Coverage Analysis | pytest-cov | Line coverage measurement |
| Linting | ruff | Code style and quality |
| Type Checking | mypy | Static type analysis |
| Migration Testing | alembic | Migration up/down verification |

---

## Definition of Done Checklist

- [ ] All acceptance criteria scenarios pass
- [ ] Unit test coverage >= 85%
- [ ] Integration tests pass
- [ ] Zero ruff linting errors
- [ ] All type hints present and mypy passes
- [ ] Documentation complete for public APIs
- [ ] Alembic migrations work (upgrade and downgrade)
- [ ] Code reviewed and approved
- [ ] No security vulnerabilities detected
