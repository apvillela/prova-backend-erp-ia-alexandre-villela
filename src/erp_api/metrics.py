from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from erp_api import config

settings = config.get_settings()


def setup_metrics(app: FastAPI) -> None:
    if not settings.metrics_enabled:
        return

    # Status code exato em vez de agrupado em 2xx/4xx: num ERP a diferença entre
    # 409 e 422, ou entre 500 e 503, muda a decisão de quem está de plantão.
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics"],
    )
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
