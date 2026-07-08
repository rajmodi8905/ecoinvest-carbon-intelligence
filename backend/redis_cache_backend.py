"""
Redis cache helper for Flask backend.

Provides a Redis-backed cache with JSON serialization.
Falls back gracefully to returning None on any error (no crash if Redis is down).

Usage:
    from redis_cache_backend import redis_cache_get, redis_cache_set

    # Get
    data = redis_cache_get("yfinance:TSLA")

    # Set with TTL
    redis_cache_set("yfinance:TSLA", {...}, ttl=86400)
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Lazy-initialize Redis connection
_redis_client = None


def _get_redis():
    """Get (or create) the Redis client. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        host = os.getenv("REDIS_HOST", "redis")
        port = int(os.getenv("REDIS_PORT", 6379))
        _redis_client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # Ping to verify connectivity
        _redis_client.ping()
        logger.info(f"✅ Redis connected: {host}:{port}")
        return _redis_client
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable: {e} — falling back to no-cache mode")
        _redis_client = None
        return None


def redis_cache_get(key: str):
    """
    Get a cached value by key. Returns the deserialized Python object or None.
    Never raises — safe to call unconditionally.
    """
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Redis GET error for key '{key}': {e}")
        return None


def redis_cache_set(key: str, value, ttl: int = 86400):
    """
    Set a cached value with TTL (seconds). Default TTL: 24 hours.
    Never raises — safe to call unconditionally.
    """
    r = _get_redis()
    if r is None:
        return
    try:
        r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.debug(f"Redis SET error for key '{key}': {e}")


def redis_cache_delete(key: str):
    """Delete a cached key. Never raises."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception as e:
        logger.debug(f"Redis DELETE error for key '{key}': {e}")
