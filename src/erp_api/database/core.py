import logging
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from erp_api import config

settings = config.get_settings()

log = logging.getLogger(__name__)


@lru_cache(1)
def get_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.postgres_echo,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_pre_ping=True,
    )


@lru_cache(1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def check_connection() -> None:
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    await get_engine().dispose()
