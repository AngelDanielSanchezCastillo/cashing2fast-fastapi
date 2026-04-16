from redis.asyncio import Redis
from ..settings import settings

# Global redis pool
_redis_client: Redis | None = None

def get_redis_client() -> Redis:
    """Get or initialize the Redis client from settings."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password.get_secret_value() if settings.redis.password else None,
            decode_responses=settings.redis.decode_responses,
        )
    return _redis_client

async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
