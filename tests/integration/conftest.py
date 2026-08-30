from typing import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio

from erp_api import config
from erp_api import database as db
from erp_api.database import Base
from erp_api.services.produtos import models

settings = config.get_settings()

assert models.Produto.__tablename__ == "produtos"


@pytest_asyncio.fixture
async def database() -> AsyncIterator[None]:
    """Cria o banco de teste se preciso e recria as tabelas; pula o teste sem Postgres de pé."""
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_pass.get_secret_value(),
            database="postgres",
            timeout=2,
        )
    except OSError:
        pytest.skip("postgres indisponível")

    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", settings.postgres_db
    )
    if not exists:
        await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    await conn.close()

    engine = db.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    # O engine é cacheado por processo, mas as conexões asyncpg ficam presas ao event
    # loop do teste que as criou; descartar aqui evita vazamento entre loops.
    await db.dispose_engine()
    db.get_engine.cache_clear()
    db.get_session_factory.cache_clear()
