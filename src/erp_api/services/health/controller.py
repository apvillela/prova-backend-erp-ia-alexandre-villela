import logging

from arq.constants import default_queue_name, health_check_key_suffix

from erp_api import database
from erp_api.caching import get_redis_async_client
from erp_api.services.health.schemas import ComponentStatus, ReadinessStatus

log = logging.getLogger(__name__)


async def _check_database() -> ComponentStatus:
    try:
        await database.check_connection()
    except Exception as e:
        log.warning(f"PostgreSQL indisponível: {e}")
        return ComponentStatus(healthy=False, detail=type(e).__name__)
    return ComponentStatus(healthy=True)


async def _check_cache() -> ComponentStatus:
    try:
        await get_redis_async_client().ping()
    except Exception as e:
        log.warning(f"Redis indisponível: {e}")
        return ComponentStatus(healthy=False, detail=type(e).__name__)
    return ComponentStatus(healthy=True)


async def _check_worker() -> ComponentStatus:
    try:
        heartbeat = await get_redis_async_client().get(
            default_queue_name + health_check_key_suffix
        )
    except Exception as e:
        log.warning(f"Redis indisponível para checar worker: {e}")
        return ComponentStatus(healthy=False, detail=type(e).__name__)
    if heartbeat is None:
        return ComponentStatus(healthy=False, detail="sem heartbeat recente")
    return ComponentStatus(healthy=True)


async def readiness() -> ReadinessStatus:
    postgres = await _check_database()
    redis = await _check_cache()
    worker = await _check_worker()

    return ReadinessStatus(
        ready=postgres.healthy and redis.healthy,
        postgres=postgres,
        redis=redis,
        worker=worker,
    )
