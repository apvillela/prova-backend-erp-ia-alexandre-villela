import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, cast

from sqlalchemy import select

from erp_api import config
from erp_api.caching import get_redis_async_client
from erp_api.database import get_session_factory
from erp_api.services.produtos.models import Produto

settings = config.get_settings()

log = logging.getLogger(__name__)

ALERTAS_KEY = "alertas:estoque_baixo"
ALERTAS_MAX = 100


async def verificar_estoque_baixo(ctx: dict[str, Any], limite: int | None = None) -> dict[str, Any]:
    limite = limite if limite is not None else settings.estoque_baixo_limite

    async with get_session_factory()() as session:
        query = (
            select(Produto)
            .where(Produto.quantidade_em_estoque < limite)
            .order_by(Produto.quantidade_em_estoque)
        )
        produtos = (await session.scalars(query)).all()

    alerta = {
        "verificado_em": datetime.now(timezone.utc).isoformat(),
        "limite": limite,
        "produtos": [
            {"id": p.id, "nome": p.nome, "quantidade_em_estoque": p.quantidade_em_estoque}
            for p in produtos
        ],
    }

    redis = get_redis_async_client()
    # redis-py tipa comandos como Awaitable|valor por causa do client síncrono; os casts
    # fixam a variante async.
    await cast(Awaitable[int], redis.lpush(ALERTAS_KEY, json.dumps(alerta)))
    await cast(Awaitable[str], redis.ltrim(ALERTAS_KEY, 0, ALERTAS_MAX - 1))

    log.info(f"Verificação de estoque baixo: {len(produtos)} produto(s) abaixo de {limite}")
    return alerta
