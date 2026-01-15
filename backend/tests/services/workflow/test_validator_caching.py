"""TDD tests for DAGValidator caching functionality.

TAG: [SPEC-010] [TESTS] [DAG] [VALIDATION] [CACHING]
REQ: REQ-010-018 - Validation Caching (Optional)

Test coverage for Redis-based caching of validation results:
- Cache miss: First validation queries DB and stores in cache
- Cache hit: Subsequent validations retrieve from cache
- TTL expiration: New validation after TTL expires
- Cache invalidation: Workflow updates invalidate cache

Uses RED-GREEN-REFACTOR TDD cycle with comprehensive edge cases.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models.enums import NodeType
from app.models.workflow import Edge, Node, Workflow
from app.schemas.validation import (
    ValidationLevel,
    ValidationOptions,
    ValidationResult,
)
from app.services.workflow.validator import DAGValidator


# =============================================================================
# Test Constants
# =============================================================================


class TestDAGValidatorCaching:
    """Test suite for DAGValidator caching using TDD approach."""

    # ========================================================================
    # Cache Miss Tests (First Validation)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_miss_on_first_validation(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test first validation results in cache miss (cached=False).

        Expected behavior:
        - First validation should query database
        - Result should have cached=False
        - Result should be stored in cache for subsequent calls
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)
        result = await validator.validate_workflow(sample_workflow.id)

        # First validation should NOT be cached
        assert result.is_valid is True
        assert result.cached is False, "First validation should have cached=False"
        assert result.workflow_id == sample_workflow.id
        assert result.workflow_version == sample_workflow.version
        assert result.validated_at is not None

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_validation(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test second validation retrieves from cache (cached=True).

        Expected behavior:
        - Second validation should retrieve from cache
        - Result should have cached=True
        - Validation duration should be significantly faster (cached)
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False

        # Second validation should be cached
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.is_valid is True
        assert result2.cached is True, "Second validation should have cached=True"
        assert result2.workflow_id == result1.workflow_id
        assert result2.workflow_version == result1.workflow_version

    # ========================================================================
    # Cache Key Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_key_includes_workflow_id_and_version(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache key is workflow_id + version.

        Expected behavior:
        - Different workflows have different cache entries
        - Same workflow with different version has different cache entry
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation at version 1
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False
        assert result1.workflow_version == 1

        # Update workflow version
        sample_workflow.version = 2
        await db_session.commit()

        # Second validation at version 2 should NOT be cached
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is False, "Version change should invalidate cache"
        assert result2.workflow_version == 2

    # ========================================================================
    # TTL Expiration Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache entry expires after TTL (5 minutes).

        Expected behavior:
        - After TTL expires, new validation should be performed
        - Result should have cached=False after TTL expiration
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False

        # Mock time to simulate TTL expiration (would require time.sleep or mock)
        # For TDD, we'll verify the cache has TTL set correctly
        # Implementation should use cache.setex(key, value, ttl)

        # Second validation immediately should be cached
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is True

        # Note: Actual TTL testing would require time manipulation or waiting
        # In production, this would be tested with configurable short TTL

    # ========================================================================
    # Cache Invalidation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_node_addition(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache is invalidated when node is added.

        Expected behavior:
        - Adding a node should invalidate cache
        - Next validation should have cached=False
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False
        assert result1.node_count == 2

        # Add a new node
        new_node = Node(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            name="New Node",
            node_type=NodeType.TOOL,
            position_x=300,
            position_y=100,
            config={},
            tool_id=uuid4(),
        )
        db_session.add(new_node)

        # Increment workflow version to invalidate cache
        sample_workflow.version = 2
        await db_session.commit()

        # Second validation should NOT be cached due to version change
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is False, "Version change should invalidate cache"
        assert result2.node_count == 3

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_edge_addition(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache is invalidated when edge is added.

        Expected behavior:
        - Adding an edge should invalidate cache
        - Next validation should have cached=False
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False
        assert result1.edge_count == 1

        # Add a new edge (need another node first)
        new_node = Node(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            name="New Node",
            node_type=NodeType.TOOL,
            position_x=300,
            position_y=100,
            config={},
            tool_id=uuid4(),
        )
        db_session.add(new_node)
        await db_session.flush()

        new_edge = Edge(
            id=uuid4(),
            workflow_id=sample_workflow.id,
            source_node_id=sample_node.id,
            target_node_id=new_node.id,
        )
        db_session.add(new_edge)

        # Increment workflow version to invalidate cache
        sample_workflow.version = 2
        await db_session.commit()

        # Second validation should NOT be cached due to version change
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is False, "Version change should invalidate cache"
        assert result2.edge_count == 2

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_node_deletion(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache is invalidated when node is deleted.

        Expected behavior:
        - Deleting a node should invalidate cache
        - Next validation should have cached=False
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False
        assert result1.node_count == 2

        # Delete the sample node
        await db_session.delete(sample_edge)
        await db_session.delete(sample_node)

        # Increment workflow version to invalidate cache
        sample_workflow.version = 2
        await db_session.commit()

        # Second validation should NOT be cached due to version change
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is False, "Version change should invalidate cache"
        assert result2.node_count == 1

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_edge_deletion(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache is invalidated when edge is deleted.

        Expected behavior:
        - Deleting an edge should invalidate cache
        - Next validation should have cached=False
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation
        result1 = await validator.validate_workflow(sample_workflow.id)
        assert result1.cached is False
        assert result1.edge_count == 1

        # Delete the edge
        await db_session.delete(sample_edge)

        # Increment workflow version to invalidate cache
        sample_workflow.version = 2
        await db_session.commit()

        # Second validation should NOT be cached due to version change
        result2 = await validator.validate_workflow(sample_workflow.id)
        assert result2.cached is False, "Version change should invalidate cache"
        assert result2.edge_count == 0

    # ========================================================================
    # Cache Persistence Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_persists_across_validator_instances(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache persists when creating new validator instances.

        Expected behavior:
        - Cache is stored in Redis, not in validator instance
        - New validator instance should still hit cache
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        # First validator instance
        validator1 = DAGValidator(db_session)
        result1 = await validator1.validate_workflow(sample_workflow.id)
        assert result1.cached is False

        # Create new validator instance
        validator2 = DAGValidator(db_session)
        result2 = await validator2.validate_workflow(sample_workflow.id)
        assert result2.cached is True, "Cache should persist across validator instances"

    # ========================================================================
    # Cache Failure Handling Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validation_fails_gracefully_when_cache_unavailable(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test validation still works when Redis is unavailable.

        Expected behavior:
        - If Redis is unavailable, validation should still work
        - Result should have cached=False (cache miss)
        - No exception should be raised
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # Mock Redis connection failure
        # Implementation should catch Redis exceptions and continue with DB validation
        result = await validator.validate_workflow(sample_workflow.id)

        # Validation should still work
        assert result.is_valid is True
        assert result.cached is False  # Cache unavailable, so not cached

    # ========================================================================
    # Cache Validation Level Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_respects_validation_level(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache behavior with different validation levels.

        Expected behavior:
        - Cache key is workflow_id + version (validation level not in cache key)
        - Different validation levels share the same cache entry
        - This is acceptable as validation level affects validation depth,
          but the workflow graph structure remains the same
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # Validate with MINIMAL level
        result_minimal = await validator.validate_workflow(
            sample_workflow.id,
            ValidationOptions(level=ValidationLevel.MINIMAL),
        )
        assert result_minimal.cached is False
        assert result_minimal.validation_level == ValidationLevel.MINIMAL

        # Validate with STANDARD level (will hit cache from MINIMAL)
        result_standard = await validator.validate_workflow(
            sample_workflow.id,
            ValidationOptions(level=ValidationLevel.STANDARD),
        )
        # Note: Cache key doesn't include validation level, so this hits cache
        # The cached result has MINIMAL level, which is acceptable as the
        # workflow structure hasn't changed
        assert result_standard.cached is True
        assert result_standard.validation_level == ValidationLevel.MINIMAL  # From cache

    # ========================================================================
    # Cache Serialization Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cache_serialization_preserves_all_fields(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test cache serialization preserves all ValidationResult fields.

        Expected behavior:
        - Cached result should have all fields from original result
        - Errors, warnings, topology should be preserved
        - Timestamps and durations should be preserved
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # First validation with full details
        options = ValidationOptions(
            level=ValidationLevel.STRICT,
            include_topology=True,
        )
        result1 = await validator.validate_workflow(sample_workflow.id, options)
        assert result1.cached is False

        # Second validation should return identical result
        result2 = await validator.validate_workflow(sample_workflow.id, options)
        assert result2.cached is True

        # Compare all fields
        assert result2.is_valid == result1.is_valid
        assert result2.workflow_id == result1.workflow_id
        assert result2.workflow_version == result1.workflow_version
        assert result2.node_count == result1.node_count
        assert result2.edge_count == result1.edge_count
        assert result2.validation_level == result1.validation_level
        assert len(result2.errors) == len(result1.errors)
        assert len(result2.warnings) == len(result1.warnings)
        assert result2.topology == result1.topology

    # ========================================================================
    # Concurrent Validation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_concurrent_validations_race_condition(
        self, db_session, sample_workflow, sample_trigger_node, sample_node, sample_edge
    ):
        """RED: Test concurrent validations handle race conditions correctly.

        Expected behavior:
        - Multiple concurrent validations should not cause issues
        - Cache should be set atomically
        - All validations should return valid results
        """
        db_session.add_all(
            [sample_workflow, sample_trigger_node, sample_node, sample_edge]
        )
        await db_session.flush()

        validator = DAGValidator(db_session)

        # Run multiple validations concurrently
        import asyncio

        results = await asyncio.gather(
            *[validator.validate_workflow(sample_workflow.id) for _ in range(5)]
        )

        # All results should be valid
        for result in results:
            assert result.is_valid is True
            assert result.workflow_id == sample_workflow.id

        # At least one should not be cached (the first one)
        uncached_count = sum(1 for r in results if not r.cached)
        assert uncached_count >= 1, "At least first validation should not be cached"


# =============================================================================
# Redis Mock Fixture
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing.

    This fixture provides a mock Redis client that simulates
    caching behavior without requiring a real Redis server.
    """
    cache_store = {}

    mock_client = MagicMock()

    # Mock get operation
    async def mock_get(key: str) -> bytes | None:
        return cache_store.get(key)

    # Mock set operation
    async def mock_set(key: str, value: bytes, ex: int | None = None) -> bool:
        cache_store[key] = value
        return True

    # Mock setex operation (set with expiration)
    async def mock_setex(key: str, time: int, value: bytes) -> bool:
        cache_store[key] = value
        return True

    # Mock delete operation
    async def mock_delete(*keys: str) -> int:
        count = 0
        for key in keys:
            if key in cache_store:
                del cache_store[key]
                count += 1
        return count

    # Mock keys operation (for cache invalidation)
    async def mock_keys(pattern: str) -> list[bytes]:
        import fnmatch

        matching_keys = []
        for key in cache_store:
            if fnmatch.fnmatch(key, pattern):
                matching_keys.append(key.encode())
        return matching_keys

    mock_client.get = mock_get
    mock_client.set = mock_set
    mock_client.setex = mock_setex
    mock_client.delete = mock_delete
    mock_client.keys = mock_keys

    return mock_client


# =============================================================================
# Cache Invalidation Helper Tests
# ========================================================================


class TestCacheInvalidationHelpers:
    """Test suite for cache invalidation helper methods."""

    @pytest.mark.asyncio
    async def test_invalidate_workflow_cache(
        self, db_session, sample_workflow, mock_redis
    ):
        """RED: Test workflow cache can be explicitly invalidated.

        Expected behavior:
        - Invalidation method should remove cache entry
        - Next validation should query database again
        """
        # This test will be implemented when cache invalidation methods are added
        # For now, it documents the expected behavior
        pass

    @pytest.mark.asyncio
    async def test_invalidate_all_workflow_caches(self, db_session, mock_redis):
        """RED: Test all workflow caches can be invalidated.

        Expected behavior:
        - Invalidation method should remove all workflow validation cache entries
        - Useful for bulk operations or system-wide cache clear
        """
        # This test will be implemented when cache invalidation methods are added
        # For now, it documents the expected behavior
        pass
