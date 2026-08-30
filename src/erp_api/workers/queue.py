import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from redis.exceptions import RedisError

from erp_api import config

settings = config.get_settings()

log = logging.getLogger(__name__)

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def get_queue_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def close_queue_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
    _pool = None


async def enqueue(task_name: str, **kwargs: Any) -> str | None:
    """Enfileira sem derrubar o request: fila fora do ar não pode travar a escrita no banco."""
    try:
        pool = await get_queue_pool()
        job = await pool.enqueue_job(task_name, **kwargs)
    except (RedisError, OSError) as e:
        log.warning(f"Fila indisponível ({type(e).__name__}); job {task_name} não enfileirado")
        return None
    return job.job_id if job else None
