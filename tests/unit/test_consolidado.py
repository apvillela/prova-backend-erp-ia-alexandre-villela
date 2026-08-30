import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from erp_api.services.consolidado import controller, fontes

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_consolida_as_tres_fontes(
    client: AsyncClient, auth_headers: dict[str, str], mocker: MockerFixture
) -> None:
    mocker.patch.object(controller.settings, "consolidado_latencia_simulada", (0.0, 0.0))

    resposta = await client.get("/consolidado/1", params={"produto_id": 2}, headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["completo"] is True
    assert corpo["estoque"]["dados"]["produto_id"] == 2
    assert corpo["financeiro"]["dados"]["cliente_id"] == 1
    assert corpo["cliente"]["dados"]["nome"] == "Cliente 1"


@pytest.mark.asyncio
async def test_fonte_com_timeout_degrada_sem_derrubar_resposta(
    client: AsyncClient, auth_headers: dict[str, str], mocker: MockerFixture
) -> None:
    async def lenta(produto_id: int) -> dict[str, Any]:
        await asyncio.sleep(10)
        return {}

    mocker.patch.object(controller.settings, "consolidado_latencia_simulada", (0.0, 0.0))
    mocker.patch.object(controller.settings, "consolidado_timeout", 0.05)
    mocker.patch.object(fontes, "estoque_service", lenta)

    resposta = await client.get("/consolidado/1", params={"produto_id": 2}, headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["completo"] is False
    assert corpo["estoque"]["disponivel"] is False
    assert corpo["estoque"]["tentativas"] == 2
    assert "Timeout" in corpo["estoque"]["erro"]
    assert corpo["financeiro"]["disponivel"] is True


@pytest.mark.asyncio
async def test_retry_recupera_falha_intermitente(mocker: MockerFixture) -> None:
    chamadas = {"n": 0}

    async def instavel() -> dict[str, Any]:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            msg = "conexão recusada"
            raise ConnectionError(msg)
        return {"ok": True}

    resultado = await controller._consultar_fonte("instavel", instavel)

    assert resultado.disponivel is True
    assert resultado.tentativas == 2
    assert resultado.dados == {"ok": True}


@pytest.mark.asyncio
async def test_chamadas_rodam_em_paralelo(mocker: MockerFixture) -> None:
    mocker.patch.object(controller.settings, "consolidado_latencia_simulada", (0.2, 0.2))

    inicio = asyncio.get_event_loop().time()
    await controller.consolidar(cliente_id=1, produto_id=1)
    duracao = asyncio.get_event_loop().time() - inicio

    assert duracao < 0.5
