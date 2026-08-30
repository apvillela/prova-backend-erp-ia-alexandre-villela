from typing import Any, Awaitable, cast

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from erp_api import caching
from erp_api.workers.tasks import ALERTAS_KEY, verificar_estoque_baixo

pytest_plugins = ("pytest_asyncio",)


async def _criar_produto(client: AsyncClient, headers: dict[str, str], **campos: Any) -> None:
    response = await client.post("/produtos", json=campos, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_task_registra_alerta_de_estoque_baixo(
    database: None, cache: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar_produto(
        client, auth_headers, nome="Parafuso", preco="1.00", quantidade_em_estoque=2
    )
    await _criar_produto(
        client, auth_headers, nome="Martelo", preco="35.00", quantidade_em_estoque=50
    )

    alerta = await verificar_estoque_baixo({}, limite=10)

    assert [p["nome"] for p in alerta["produtos"]] == ["Parafuso"]
    assert await cast(Awaitable[int], caching.get_redis_async_client().llen(ALERTAS_KEY)) == 1


@pytest.mark.asyncio
async def test_endpoint_lista_alertas(
    database: None, cache: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar_produto(client, auth_headers, nome="Prego", preco="0.50", quantidade_em_estoque=1)
    await verificar_estoque_baixo({}, limite=10)

    resposta = await client.get("/alertas/estoque-baixo", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 1
    assert corpo[0]["produtos"][0]["nome"] == "Prego"


@pytest.mark.asyncio
async def test_endpoint_enfileira_verificacao(
    client: AsyncClient, auth_headers: dict[str, str], mocker: MockerFixture
) -> None:
    mocker.patch("erp_api.services.alertas.controller.enqueue", return_value="job-123")

    resposta = await client.post("/alertas/estoque-baixo/verificar", headers=auth_headers)

    assert resposta.status_code == 202
    assert resposta.json() == {"job_id": "job-123", "enfileirado": True}
