from typing import Awaitable, cast

from erp_api.caching import get_redis_async_client
from erp_api.services.alertas.schemas import AlertaEstoqueBaixo, VerificacaoEnfileirada
from erp_api.workers.queue import enqueue
from erp_api.workers.tasks import ALERTAS_KEY


async def listar_alertas(quantidade: int) -> list[AlertaEstoqueBaixo]:
    valores = await cast(
        "Awaitable[list[str]]",
        get_redis_async_client().lrange(ALERTAS_KEY, 0, quantidade - 1),
    )
    return [AlertaEstoqueBaixo.model_validate_json(v) for v in valores]


async def solicitar_verificacao() -> VerificacaoEnfileirada:
    job_id = await enqueue("verificar_estoque_baixo")
    return VerificacaoEnfileirada(job_id=job_id, enfileirado=job_id is not None)
