from typing import Any, ClassVar

from arq.cron import cron

from erp_api.database import dispose_engine
from erp_api.workers.queue import redis_settings
from erp_api.workers.tasks import verificar_estoque_baixo


async def on_shutdown(ctx: dict[str, Any]) -> None:
    await dispose_engine()


class WorkerSettings:
    functions: ClassVar = [verificar_estoque_baixo]
    cron_jobs: ClassVar = [cron(verificar_estoque_baixo, minute=set(range(0, 60, 5)), unique=True)]
    redis_settings = redis_settings()
    on_shutdown = on_shutdown
    health_check_interval = 30
