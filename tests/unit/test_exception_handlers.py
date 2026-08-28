from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from erp_api.exceptions import ConflictError, NotFoundError, register_exception_handlers

pytest_plugins = ("pytest_asyncio",)


NAO_ENCONTRADO_MSG = "produto 1 não encontrado"
CONFLITO_MSG = "sku duplicado"
VALIDACAO_MSG = (
    "body.quantidade: Input should be a valid integer, unable to parse string as an integer"
)


class Payload(BaseModel):
    quantidade: int


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/echo")
    async def echo(payload: Payload) -> dict[str, int]:
        return {"quantidade": payload.quantidade}

    @app.get("/nao-encontrado")
    async def nao_encontrado() -> None:
        raise NotFoundError(NAO_ENCONTRADO_MSG)

    @app.get("/conflito")
    async def conflito() -> None:
        raise ConflictError(CONFLITO_MSG)

    @app.get("/proibido")
    async def proibido() -> None:
        raise HTTPException(status_code=403, detail="sem permissão")

    @app.get("/boom")
    async def boom() -> None:
        msg = "falha inesperada"
        raise RuntimeError(msg)

    return app


@pytest_asyncio.fixture
async def error_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=_build_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_erro_de_validacao_usa_contrato_padrao(error_client: AsyncClient) -> None:
    response = await error_client.post("/echo", json={"quantidade": "abc"})

    assert response.status_code == 422
    assert response.json() == {"detail": [{"msg": VALIDACAO_MSG}]}


@pytest.mark.asyncio
async def test_not_found_error_vira_404(error_client: AsyncClient) -> None:
    response = await error_client.get("/nao-encontrado")

    assert response.status_code == 404
    assert response.json() == {"detail": [{"msg": NAO_ENCONTRADO_MSG}]}


@pytest.mark.asyncio
async def test_conflict_error_vira_409(error_client: AsyncClient) -> None:
    response = await error_client.get("/conflito")

    assert response.status_code == 409
    assert response.json() == {"detail": [{"msg": CONFLITO_MSG}]}


@pytest.mark.asyncio
async def test_http_exception_mantem_status_e_formato(error_client: AsyncClient) -> None:
    response = await error_client.get("/proibido")

    assert response.status_code == 403
    assert response.json() == {"detail": [{"msg": "sem permissão"}]}


@pytest.mark.asyncio
async def test_erro_nao_tratado_nao_vaza_detalhe(error_client: AsyncClient) -> None:
    response = await error_client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": [{"msg": "Erro interno inesperado."}]}
