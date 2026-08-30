import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import erp_api
from erp_api import api, config
from erp_api.exceptions import register_exception_handlers
from erp_api.lifespan import lifespan
from erp_api.metrics import setup_metrics
from erp_api.middlewares import RequestContextMiddleware

log = logging.getLogger(__name__)

settings = config.get_settings()


swagger_ui_parameters = {
    "displayRequestDuration": True,
    "filter": True,
    "syntaxHighlight.theme": "arta",
}

app = FastAPI(
    title=settings.app_title,
    description="",
    version=erp_api.__version__,
    swagger_ui_parameters=swagger_ui_parameters,
    lifespan=lifespan,
)

register_exception_handlers(app)
setup_metrics(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Último middleware adicionado = primeiro a rodar: todo request (inclusive os
# rejeitados por CORS) entra com request_id e sai registrado no access log.
app.add_middleware(RequestContextMiddleware)


@app.get("/health_check")
def health_check() -> dict[str, str]:
    """Liveness: responde sem tocar em dependência externa."""
    return {"ping": "pong"}


log.debug("Adicionando router da api ao app")
app.include_router(api.router)
