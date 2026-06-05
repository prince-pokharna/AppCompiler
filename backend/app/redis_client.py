"""Async Redis client for caching and job state management."""

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the Redis connection pool singleton, falling back to FakeRedis if unreachable."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        try:
            client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            # Try a quick ping with a short timeout to check connection
            await asyncio.wait_for(client.ping(), timeout=2.0)
            _redis_pool = client
        except Exception as exc:
            import logging
            logger = logging.getLogger("appcompiler.redis")
            logger.warning(
                f"Failed to connect to Redis at {settings.redis_url} ({exc}). "
                "Falling back to in-memory FakeRedis."
            )
            import fakeredis.aioredis
            _redis_pool = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


async def set_job_state(job_id: str, state: dict[str, Any], ttl: int = 3600) -> None:
    """Store job state as JSON in Redis with TTL."""
    r = await get_redis()
    await r.set(f"job:{job_id}", json.dumps(state, default=str), ex=ttl)


async def get_job_state(job_id: str) -> dict[str, Any] | None:
    """Retrieve job state from Redis."""
    r = await get_redis()
    data = await r.get(f"job:{job_id}")
    if data is None:
        return None
    return json.loads(data)


async def publish_event(job_id: str, event: dict[str, Any]) -> None:
    """Publish a pipeline event to the job's Redis channel."""
    r = await get_redis()
    await r.publish(f"job:{job_id}:events", json.dumps(event, default=str))


async def append_event(job_id: str, event: dict[str, Any]) -> None:
    """Append an event to the job's event list for late subscribers."""
    r = await get_redis()
    await r.rpush(f"job:{job_id}:event_log", json.dumps(event, default=str))
    await r.expire(f"job:{job_id}:event_log", 3600)


async def get_event_log(job_id: str) -> list[dict[str, Any]]:
    """Get all events for a job (for late subscribers to catch up)."""
    r = await get_redis()
    events = await r.lrange(f"job:{job_id}:event_log", 0, -1)
    return [json.loads(e) for e in events]
