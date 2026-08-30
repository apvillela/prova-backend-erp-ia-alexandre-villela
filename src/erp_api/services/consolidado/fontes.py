import asyncio
import random
from decimal import Decimal
from typing import Any

from erp_api import config

settings = config.get_settings()


async def _latencia() -> None:
    await asyncio.sleep(random.uniform(*settings.consolidado_latencia_simulada))  # noqa: S311


async def estoque_service(produto_id: int) -> dict[str, Any]:
    await _latencia()
    return {
        "produto_id": produto_id,
        "quantidade_disponivel": random.randint(0, 200),  # noqa: S311
        "quantidade_reservada": random.randint(0, 20),  # noqa: S311
    }


async def financeiro_service(cliente_id: int) -> dict[str, Any]:
    await _latencia()
    return {
        "cliente_id": cliente_id,
        "limite_credito": str(Decimal("5000.00")),
        "titulos_em_aberto": random.randint(0, 5),  # noqa: S311
        "inadimplente": random.random() < 0.1,  # noqa: S311
    }


async def cliente_service(cliente_id: int) -> dict[str, Any]:
    await _latencia()
    return {
        "cliente_id": cliente_id,
        "nome": f"Cliente {cliente_id}",
        "segmento": random.choice(["varejo", "atacado", "industria"]),  # noqa: S311
        "ativo": True,
    }
