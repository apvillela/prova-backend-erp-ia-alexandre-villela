import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import anyio
from fastapi import FastAPI

from erp_api import config, database
from erp_api.caching import close_redis_async_client, get_redis_async_client

settings = config.get_settings()

log = logging.getLogger(__name__)


async def _check_connection_database() -> None:
    log.debug("Verificando conexão com o PostgreSQL")
    await database.check_connection()


async def _check_connection_cache_server() -> None:
    log.debug("Verificando conexão com o Redis")
    await get_redis_async_client().ping()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    anyio.to_thread.current_default_thread_limiter().total_tokens = settings.worker_thread_pool_size

    await _check_connection_database()
    await _check_connection_cache_server()

    yield

    # Shutdown
    await database.dispose_engine()
    await close_redis_async_client()
