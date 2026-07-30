"""
Redis cache infrastructure.
Provides async Redis client and caching decorators.
"""

from redis.asyncio import Redis

from src.config.settings import get_settings

settings = get_settings()

redis_client = Redis.from_url(
    settings.redis.redis_url,
    decode_responses=True,
)


async def get_redis() -> Redis:
    """FastAPI dependency for Redis client."""
    return redis_client
