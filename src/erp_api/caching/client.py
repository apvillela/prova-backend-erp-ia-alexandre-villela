from functools import lru_cache

from redis.asyncio import Redis

from erp_api import config

settings = config.get_settings()


@lru_cache(1)
def get_redis_async_client() -> Redis:
    client: Redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return client


async def close_redis_async_client() -> None:
    await get_redis_async_client().aclose()
