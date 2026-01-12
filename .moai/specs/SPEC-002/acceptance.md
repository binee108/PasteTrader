# SPEC-002 Acceptance Criteria

## Metadata

| Field | Value |
|-------|-------|
| SPEC ID | SPEC-002 |
| Title | User Authentication Model Acceptance Criteria |
| Created | 2026-01-12 |
| Status | Ready for Testing |
| Priority | High (P0) |
| Phase | Phase 0 (Database Foundation) |

---

## Overview

This document defines the comprehensive acceptance criteria for SPEC-002 (User Authentication Model). All criteria are written in Gherkin format (Given-When-Then) to ensure clear, testable requirements that validate the User model implementation and future authentication features.

---

## Test Categories

### Category 1: User Model Structure
### Category 2: Password Hashing & Verification
### Category 3: Email Validation & Normalization
### Category 4: Account Status Management
### Category 5: User-Workflow Relationships
### Category 6: Soft Delete Behavior
### Category 7: Service Layer Operations
### Category 8: Security & Performance

---

## Category 1: User Model Structure

### AC-001: User Model with Required Fields

**Feature**: User Model Structure

**Scenario**: Create user with all required fields
```gherkin
GIVEN the User model is defined with UUIDMixin, TimestampMixin, and SoftDeleteMixin
WHEN a new User instance is created with email, hashed_password, and is_active
THEN the user should have a valid UUID primary key
AND the user should have created_at and updated_at timestamps
AND the user should have deleted_at set to None
AND the user should be saved successfully to the database
```

### AC-002: Email Uniqueness Constraint

**Feature**: Email Uniqueness

**Scenario**: Prevent duplicate email addresses
```gherkin
GIVEN a user exists with email "test@example.com"
WHEN attempting to create another user with email "test@example.com"
THEN the database should raise an IntegrityError
AND the second user should not be created
AND the error message should indicate a unique constraint violation
```

### AC-003: Email Field Indexing

**Feature**: Email Query Performance

**Scenario**: Fast email lookup with index
```gherkin
GIVEN the users table has 1,000,000 records
WHEN querying for a user by email
THEN the query should use the email index
AND the query execution time should be under 100ms
AND the query plan should show an index scan
```

---

## Category 2: Password Hashing & Verification

### AC-004: Password Hashing with Bcrypt

**Feature**: Password Hashing

**Scenario**: Hash password using bcrypt
```gherkin
GIVEN the hash_password function is configured with bcrypt
WHEN a plain password "SecurePass123!" is hashed
THEN the result should be a bcrypt hash string
AND the hash should start with "$2b$12$" prefix
AND the hash should be 60 characters long
AND the original password should not be stored
```

### AC-005: Password Verification

**Feature**: Password Verification

**Scenario**: Verify correct password
```gherkin
GIVEN a user exists with hashed password
WHEN verifying the correct plain password
THEN the verification should return True
AND the verification should use timing-safe comparison
AND the verification should complete within 500ms
```

### AC-006: Incorrect Password Verification

**Feature**: Password Verification

**Scenario**: Reject incorrect password
```gherkin
GIVEN a user exists with hashed password "SecurePass123!"
WHEN verifying an incorrect password "WrongPass456!"
THEN the verification should return False
AND the verification should not leak timing information
AND the verification should complete within 500ms
```

### AC-007: Password Hash Uniqueness

**Feature**: Password Hash Salting

**Scenario**: Same password produces different hashes
```gherkin
GIVEN the hash_password function uses bcrypt with automatic salt
WHEN the same password "SecurePass123!" is hashed twice
THEN the two resulting hashes should be different
AND both hashes should verify successfully against the password
```

---

## Category 3: Email Validation & Normalization

### AC-008: Email Normalization to Lowercase

**Feature**: Email Normalization

**Scenario**: Convert email to lowercase
```gherkin
GIVEN an email address "Test@Example.COM"
WHEN the email is normalized
THEN the result should be "test@example.com"
AND all uppercase letters should be converted to lowercase
```

### AC-009: Email Whitespace Trimming

**Feature**: Email Normalization

**Scenario**: Remove whitespace from email
```gherkin
GIVEN an email address "  test@example.com  "
WHEN the email is normalized
THEN the result should be "test@example.com"
AND leading and trailing whitespace should be removed
```

### AC-010: Invalid Email Format Detection

**Feature**: Email Validation

**Scenario**: Reject invalid email format
```gherkin
GIVEN an invalid email format "invalid-email"
WHEN the email is validated
THEN the validation should return False
AND a validation error should be raised
AND the error should indicate invalid email format
```

### AC-011: Valid Email Format Acceptance

**Feature**: Email Validation

**Scenario**: Accept valid email formats
```gherkin
GIVEN valid email formats:
  - "user@example.com"
  - "first.last@example.co.uk"
  - "user+tag@example.com"
WHEN each email is validated
THEN all validations should return True
AND all emails should be accepted
```

---

## Category 4: Account Status Management

### AC-012: Default Active Status

**Feature**: Account Status

**Scenario**: New user is active by default
```gherkin
GIVEN a new user is being created
WHEN the user is created without specifying is_active
THEN the user.is_active should be True
AND the database default should be True
AND the user should be able to authenticate
```

### AC-013: Inactive User Authentication Prevention

**Feature**: Account Status

**Scenario**: Inactive user cannot authenticate
```gherkin
GIVEN a user exists with is_active = False
WHEN attempting to authenticate with valid credentials
THEN the authentication should fail
AND an error message should indicate the account is inactive
AND the error should not reveal whether the password was correct
```

### AC-014: Account Activation

**Feature**: Account Status

**Scenario**: Activate inactive user account
```gherkin
GIVEN a user exists with is_active = False
WHEN the user.is_active is set to True
AND the user is updated in the database
THEN the user should be able to authenticate with valid credentials
AND the user's workflows should be accessible
```

---

## Category 5: User-Workflow Relationships

### AC-015: User Can Own Multiple Workflows

**Feature**: Workflow Ownership

**Scenario**: Create workflows for a user
```gherkin
GIVEN a user exists
WHEN three workflows are created with owner_id = user.id
THEN the user.workflows relationship should return 3 workflows
AND each workflow should have owner_id pointing to the user
AND all workflows should be accessible via user.workflows
```

### AC-016: Workflow Requires Owner

**Feature**: Workflow Ownership

**Scenario**: Workflow must have an owner
```gherkin
GIVEN a workflow is being created
WHEN the workflow is created without an owner_id
THEN the database should raise an IntegrityError
AND the workflow should not be created
AND the error should indicate a NOT NULL constraint violation
```

### AC-017: Cascade Soft Delete Handling

**Feature**: Soft Delete Integration

**Scenario**: Soft delete user should not cascade delete workflows
```gherkin
GIVEN a user exists with 3 workflows
WHEN the user is soft deleted (deleted_at is set)
THEN the user should not appear in default queries
AND the user's workflows should still exist
AND the workflows should still have owner_id pointing to the user
AND passive_deletes should be configured on the relationship
```

---

## Category 6: Soft Delete Behavior

### AC-018: Soft Delete User

**Feature**: Soft Delete

**Scenario**: Mark user as deleted
```gherkin
GIVEN a user exists with deleted_at = None
WHEN the user is soft deleted
THEN user.deleted_at should be set to a valid timestamp
AND user.is_deleted should return True
AND the user should not appear in default queries
```

### AC-019: Exclude Soft Deleted Users from Queries

**Feature**: Soft Delete Filtering

**Scenario**: Default query excludes deleted users
```gherkin
GIVEN 10 users exist in the database
AND 3 users are soft deleted
WHEN querying all users without explicit filter
THEN the query should return 7 active users
AND the 3 deleted users should not be included
```

### AC-020: Include Soft Deleted Users with Explicit Filter

**Feature**: Soft Delete Filtering

**Scenario**: Explicitly include deleted users
```gherkin
GIVEN 10 users exist in the database
AND 3 users are soft deleted
WHEN querying all users with include_deleted=True
THEN the query should return all 10 users
AND the 3 deleted users should have deleted_at set
```

### AC-021: Restore Soft Deleted User

**Feature**: Soft Delete Restoration

**Scenario**: Restore deleted user
```gherkin
GIVEN a soft deleted user exists
WHEN the user is restored (deleted_at set to None)
THEN user.deleted_at should be None
AND user.is_deleted should return False
AND the user should appear in default queries
```

---

## Category 7: Service Layer Operations

### AC-022: Create User with Password Hashing

**Feature**: User Creation

**Scenario**: Service layer hashes password automatically
```gherkin
GIVEN the UserService.create_user method
WHEN creating a user with UserCreate(email="test@example.com", password="PlainPass123!")
THEN the password should be hashed before storage
AND the plain password should not be stored
AND the user should be created successfully
AND user.hashed_password should be a valid bcrypt hash
```

### AC-023: Get User by ID

**Feature**: User Retrieval

**Scenario**: Retrieve user by ID
```gherkin
GIVEN a user exists with id = "user-uuid-123"
WHEN calling UserService.get_user_by_id("user-uuid-123")
THEN the user should be returned
AND the user's email should match
AND the user's hashed_password should not be exposed in responses
```

### AC-024: Get User by Email

**Feature**: User Retrieval

**Scenario**: Retrieve user by email
```gherkin
GIVEN a user exists with email "test@example.com"
WHEN calling UserService.get_user_by_email("test@example.com")
THEN the user should be returned
AND the email lookup should use the index
AND the query should complete within 100ms
```

### AC-025: Authenticate User with Valid Credentials

**Feature**: User Authentication

**Scenario**: Successful authentication
```gherkin
GIVEN a user exists with email "test@example.com" and password "SecurePass123!"
WHEN calling UserService.authenticate_user("test@example.com", "SecurePass123!")
THEN the user should be returned
AND the user.is_active should be True
AND the authentication should succeed
```

### AC-026: Authenticate User with Invalid Password

**Feature**: User Authentication

**Scenario**: Failed authentication with wrong password
```gherkin
GIVEN a user exists with email "test@example.com" and password "SecurePass123!"
WHEN calling UserService.authenticate_user("test@example.com", "WrongPass456!")
THEN the service should return None
AND no user should be returned
AND the failure should not be distinguishable from non-existent user
```

### AC-027: Authenticate Inactive User

**Feature**: User Authentication

**Scenario**: Failed authentication for inactive user
```gherkin
GIVEN a user exists with email "test@example.com" and is_active = False
WHEN calling UserService.authenticate_user("test@example.com", "correct_password")
THEN the service should return None
AND no user should be returned
AND the failure should not reveal the account status
```

### AC-028: Authenticate Non-existent User

**Feature**: User Authentication

**Scenario**: Failed authentication for non-existent user
```gherkin
GIVEN no user exists with email "nonexistent@example.com"
WHEN calling UserService.authenticate_user("nonexistent@example.com", "any_password")
THEN the service should return None
AND the failure should be consistent with other authentication failures
AND timing should be similar to failed authentication for existing users
```

---

## Category 8: Security & Performance

### AC-029: Password Not Logged

**Feature**: Security Logging

**Scenario**: Passwords should not appear in logs
```gherkin
GIVEN logging is configured for the application
WHEN a user is created with password "SensitivePass123!"
AND user creation is logged
THEN the log should not contain the plain password
AND the log should not contain the hashed password
AND the log should only contain the user ID and email
```

### AC-030: Timing-Safe Password Comparison

**Feature**: Security

**Scenario**: Prevent timing attacks on password verification
```gherkin
GIVEN a user exists with a stored password hash
WHEN verifying passwords multiple times with both correct and incorrect passwords
THEN the verification time should be consistent (within 50ms variance)
AND no significant timing differences should be observable
AND timing-based side channel attacks should be prevented
```

### AC-031: Password Hashing Performance

**Feature**: Performance

**Scenario**: Password hashing completes within acceptable time
```gherkin
GIVEN the bcrypt cost factor is set to 12
WHEN hashing a password "TestPassword123!"
THEN the hashing should complete within 500ms
AND the verification should complete within 500ms
AND the performance should be consistent across multiple operations
```

### AC-032: Email Lookup Performance

**Feature**: Performance

**Scenario**: Fast email lookup with index
```gherkin
GIVEN the users table has 100,000 records
AND an index exists on the email column
WHEN querying for a user by email
THEN the query should complete within 100ms
AND the query plan should use the email index
AND the query should not perform a full table scan
```

### AC-033: User Creation Performance

**Feature**: Performance

**Scenario**: User creation completes within acceptable time
```gherkin
GIVEN the database connection is healthy
WHEN creating a new user with email and password
THEN the user creation should complete within 1 second
AND the password hashing should account for most of the time
AND the database insert should complete within 100ms
```

---

## Quality Gates

### TRUST 5 Validation

**Test-first Pillar**:
- [ ] All acceptance criteria have corresponding tests
- [ ] Test coverage >= 85% for User model and service layer
- [ ] All tests pass consistently

**Readable Pillar**:
- [ ] Clear function names (hash_password, verify_password)
- [ ] Comprehensive docstrings on all public methods
- [ ] Type hints on all function signatures

**Unified Pillar**:
- [ ] Black formatting applied to all code
- [ ] Ruff linting passes with no errors
- [ ] Import ordering is consistent

**Secured Pillar**:
- [ ] Passwords never logged or exposed
- [ ] Bcrypt cost factor >= 12
- [ ] Timing-safe password comparison
- [ ] Email normalization prevents case collision

**Trackable Pillar**:
- [ ] All code includes TAG/REQ references
- [ ] Clear commit messages for changes
- [ ] Migration scripts documented
- [ ] Test failures include context

---

## Test Execution Order

### Phase 1: Model Tests (AC-001 to AC-003)
```bash
pytest tests/models/test_user.py -v
```

### Phase 2: Password Tests (AC-004 to AC-007)
```bash
pytest tests/core/test_security.py -v
```

### Phase 3: Email Tests (AC-008 to AC-011)
```bash
pytest tests/utils/test_email.py -v
```

### Phase 4: Service Tests (AC-022 to AC-028)
```bash
pytest tests/services/test_user_service.py -v
```

### Phase 5: Integration Tests (AC-012 to AC-021)
```bash
pytest tests/integration/test_user_workflows.py -v
```

### Phase 6: Security & Performance Tests (AC-029 to AC-033)
```bash
pytest tests/security/test_password_security.py -v
pytest tests/performance/test_user_performance.py -v
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | >= 85% | pytest --cov=app.models.user |
| Acceptance Criteria Pass Rate | 100% | All AC scenarios pass |
| Password Hash Time | < 500ms | Benchmark tests |
| Email Lookup Time | < 100ms | Database query tests |
| User Creation Time | < 1s | API latency tests |

---

## Definition of Done

SPEC-002 is considered complete when:

1. **All Acceptance Criteria Pass**: 100% of AC scenarios pass
2. **Test Coverage Met**: >= 85% code coverage
3. **Documentation Complete**: All functions documented with docstrings
4. **Quality Gates Passed**: TRUST 5 compliance verified
5. **Performance Benchmarks Met**: All performance ACs pass
6. **Security Validated**: No security vulnerabilities identified
7. **Code Review Approved**: At least one reviewer approval

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-12 | workflow-spec | Initial acceptance criteria creation |
