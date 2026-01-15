"""Redis-based caching layer for validation results.

TAG: [SPEC-010] [CACHING] [REDIS]
REQ: REQ-010-018 - Validation Caching (Optional)

This module provides Redis caching for workflow validation results.
Cache key format: "validation:{workflow_id}:{version}"
TTL: 5 minutes (300 seconds) by default, configurable via settings.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache key prefix
VALIDATION_CACHE_PREFIX = "validation"

# Default TTL: 5 minutes (from REQ-010-018)
DEFAULT_CACHE_TTL = 300


def _serialize_validation_result(result: dict[str, Any]) -> dict[str, Any]:
    """Serialize ValidationResult to dict for caching.

    Converts datetime to ISO format string.

    Args:
        result: ValidationResult as dict

    Returns:
        Serialized dict ready for JSON encoding
    """
    result_copy = result.copy()
    if "validated_at" in result_copy:
        validated_at = result_copy["validated_at"]
        if isinstance(validated_at, datetime):
            result_copy["validated_at"] = validated_at.isoformat()
    return result_copy


def _deserialize_validation_result(result: dict[str, Any]) -> dict[str, Any]:
    """Deserialize cached dict to ValidationResult format.

    Converts ISO format string back to datetime.

    Args:
        result: Cached dict from Redis

    Returns:
        Deserialized dict ready for ValidationResult
    """
    # Convert ISO format string back to datetime
    if isinstance(result.get("validated_at"), str):
        result["validated_at"] = datetime.fromisoformat(result["validated_at"])
    # Convert UUIDs back from strings (if they were serialized)
    if isinstance(result.get("workflow_id"), str):
        result["workflow_id"] = UUID(result["workflow_id"])
    return result


class ValidationCache:
    """Redis-based cache for workflow validation results.

    TAG: [SPEC-010] [CACHING] [REDIS]

    Features:
    - Cache key: workflow_id + version
    - TTL: 5 minutes (configurable)
    - Automatic cache invalidation on graph modifications
    - Graceful degradation when Redis is unavailable
    - In-memory fallback for testing
    """

    def __init__(self, redis_url: str | None = None, ttl: int = DEFAULT_CACHE_TTL):
        """Initialize the validation cache.

        Args:
            redis_url: Redis connection URL (from settings if None)
            ttl: Cache TTL in seconds (default: 300)
        """
        self.ttl = ttl
        self._pool: ConnectionPool | None = None
        self._redis: Redis | None = None
        self._in_memory_cache: dict[str, tuple[dict[str, Any], datetime]] = {}
        self._use_in_memory = False

        if redis_url:
            self._initialize_redis(redis_url)

        # If Redis unavailable, use in-memory cache
        if self._redis is None:
            self._use_in_memory = True
            logger.info("Using in-memory cache for validation results")

    def _initialize_redis(self, redis_url: str) -> None:
        """Initialize Redis connection pool.

        Args:
            redis_url: Redis connection URL
        """
        try:
            self._pool = ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
            )
            self._redis = Redis(connection_pool=self._pool)
            logger.info("Validation cache initialized with Redis")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
            self._pool = None
            self._redis = None

    @property
    def available(self) -> bool:
        """Check if cache is available (Redis or in-memory)."""
        return self._use_in_memory or self._redis is not None

    def _make_cache_key(self, workflow_id: UUID, version: int) -> str:
        """Generate cache key for validation result.

        TAG: [SPEC-010] [CACHING]

        Cache key format: validation:{workflow_id}:{version}

        Args:
            workflow_id: Workflow UUID
            version: Workflow version

        Returns:
            Cache key string
        """
        return f"{VALIDATION_CACHE_PREFIX}:{workflow_id}:{version}"

    async def get(self, workflow_id: UUID, version: int) -> dict[str, Any] | None:
        """Get cached validation result.

        Args:
            workflow_id: Workflow UUID
            version: Workflow version

        Returns:
            Cached validation result dict, or None if not found/expired
        """
        if not self.available:
            return None

        cache_key = self._make_cache_key(workflow_id, version)

        # Try in-memory cache first
        if self._use_in_memory:
            if cache_key in self._in_memory_cache:
                cached_data, expiry_time = self._in_memory_cache[cache_key]
                # Check if expired
                if datetime.now(UTC) < expiry_time:
                    logger.debug(f"In-memory cache HIT: {cache_key}")
                    return _deserialize_validation_result(cached_data)
                else:
                    # Remove expired entry
                    del self._in_memory_cache[cache_key]
                    logger.debug(f"In-memory cache expired: {cache_key}")
            logger.debug(f"In-memory cache MISS: {cache_key}")
            return None

        # Try Redis
        try:
            cached_data = await self._redis.get(cache_key)

            if cached_data:
                logger.debug(f"Redis cache HIT: {cache_key}")
                result = json.loads(cached_data)
                return _deserialize_validation_result(result)
            else:
                logger.debug(f"Redis cache MISS: {cache_key}")
                return None
        except RedisError as e:
            logger.warning(f"Redis get failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Cache deserialization failed: {e}")
            return None

    async def set(
        self, workflow_id: UUID, version: int, result: dict[str, Any]
    ) -> bool:
        """Cache validation result with TTL.

        Args:
            workflow_id: Workflow UUID
            version: Workflow version
            result: ValidationResult as dict

        Returns:
            True if successfully cached, False otherwise
        """
        if not self.available:
            return False

        cache_key = self._make_cache_key(workflow_id, version)

        # Serialize result
        serialized = _serialize_validation_result(result)

        # Try in-memory cache first
        if self._use_in_memory:
            expiry_time = datetime.now(UTC) + timedelta(seconds=self.ttl)
            self._in_memory_cache[cache_key] = (serialized, expiry_time)
            logger.debug(f"In-memory cached: {cache_key} (TTL: {self.ttl}s)")
            return True

        # Try Redis
        try:
            cached_data = json.dumps(serialized)

            # Set with expiration (TTL)
            await self._redis.setex(cache_key, self.ttl, cached_data)
            logger.debug(f"Redis cached: {cache_key} (TTL: {self.ttl}s)")
            return True
        except RedisError as e:
            logger.warning(f"Redis set failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Cache serialization failed: {e}")
            return False

    async def delete(self, workflow_id: UUID, version: int | None = None) -> bool:
        """Invalidate cache entry for a workflow.

        If version is None, deletes all versions of the workflow.

        Args:
            workflow_id: Workflow UUID
            version: Workflow version (None for all versions)

        Returns:
            True if deleted, False otherwise
        """
        if not self.available:
            return False

        # Try in-memory cache first
        if self._use_in_memory:
            if version is not None:
                # Delete specific version
                cache_key = self._make_cache_key(workflow_id, version)
                if cache_key in self._in_memory_cache:
                    del self._in_memory_cache[cache_key]
                    logger.debug(f"In-memory cache invalidated: {cache_key}")
            else:
                # Delete all versions
                pattern = f"{VALIDATION_CACHE_PREFIX}:{workflow_id}:"
                keys_to_delete = [
                    k for k in self._in_memory_cache.keys() if k.startswith(pattern)
                ]
                for key in keys_to_delete:
                    del self._in_memory_cache[key]
                logger.debug(
                    f"In-memory cache invalidated {len(keys_to_delete)} entries for workflow {workflow_id}"
                )
            return True

        # Try Redis
        try:
            if version is not None:
                # Delete specific version
                cache_key = self._make_cache_key(workflow_id, version)
                await self._redis.delete(cache_key)
                logger.debug(f"Redis cache invalidated: {cache_key}")
            else:
                # Delete all versions using pattern
                pattern = f"{VALIDATION_CACHE_PREFIX}:{workflow_id}:*"
                keys = await self._redis.keys(pattern)
                if keys:
                    await self._redis.delete(*keys)
                    logger.debug(
                        f"Invalidated {len(keys)} cache entries for workflow {workflow_id}"
                    )
            return True
        except RedisError as e:
            logger.warning(f"Redis delete failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Validation cache connection closed")


# Global cache instance (initialized from settings)
_global_cache: ValidationCache | None = None


def get_validation_cache() -> ValidationCache:
    """Get or create global validation cache instance.

    TAG: [SPEC-010] [CACHING]

    Returns:
        ValidationCache instance (may be unavailable if Redis not configured)
    """
    global _global_cache

    if _global_cache is None:
        redis_url = str(settings.REDIS_URL) if settings.REDIS_URL else None
        ttl = (
            settings.REDIS_CACHE_TTL
            if hasattr(settings, "REDIS_CACHE_TTL")
            else DEFAULT_CACHE_TTL
        )
        _global_cache = ValidationCache(redis_url=redis_url, ttl=ttl)

    return _global_cache


__all__ = ["ValidationCache", "get_validation_cache"]
