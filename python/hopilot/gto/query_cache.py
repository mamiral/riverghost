#!/usr/bin/env python3
"""
Query Result Cache for analytical queries.

Provides caching for frequently accessed analytical query results
to improve performance and reduce database load.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple
from functools import wraps

from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class QueryResultCache:
    """
    Simple in-memory cache for analytical query results.

    Provides TTL-based caching with automatic cleanup of expired entries.
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of cached results
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)

    def _generate_key(self, func_name: str, args: Tuple, kwargs: Dict) -> str:
        """Generate a cache key from function name and arguments."""
        # Create a deterministic string representation
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }

        # Sort kwargs for consistency
        if 'kwargs' in key_data:
            key_data['kwargs'] = dict(sorted(key_data['kwargs'].items()))

        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if it exists and hasn't expired."""
        if key in self.cache:
            value, expiry_time = self.cache[key]
            if time.time() < expiry_time:
                logger.debug(f"Cache hit for key: {key}")
                return value
            else:
                # Expired, remove it
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL."""
        expiry_time = time.time() + (ttl or self.default_ttl)

        # Clean up expired entries if we're at max size
        if len(self.cache) >= self.max_size:
            self._cleanup_expired()

        # If still at max size after cleanup, remove oldest entry
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (value, expiry_time)
        logger.debug(f"Cached result for key: {key}, expires at: {expiry_time}")

    def _cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        current_time = time.time()
        expired_keys = [k for k, (_, expiry) in self.cache.items() if current_time >= expiry]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        self._cleanup_expired()  # Clean up before reporting size
        return len(self.cache)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'default_ttl': self.default_ttl
        }


# Global cache instance
_query_cache = QueryResultCache()


def cached_query(ttl: Optional[int] = None):
    """
    Decorator to cache analytical query results.

    Args:
        ttl: Time-to-live in seconds (uses cache default if None)

    Returns:
        Decorated function that caches results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _query_cache._generate_key(func.__name__, args, kwargs)

            # Try to get from cache first
            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Not in cache, execute function
            result = func(*args, **kwargs)

            # Cache the result
            _query_cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, Any]:
    """Get current cache statistics."""
    return _query_cache.stats()


def clear_query_cache() -> None:
    """Clear all cached query results."""
    _query_cache.clear()