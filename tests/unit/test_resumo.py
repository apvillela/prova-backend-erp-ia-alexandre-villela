import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from erp_api.services.resumo import controller, fontes
from erp_api.services.resumo.fontes import FonteError

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_resume_as_tres_fontes(
    client: AsyncClient, auth_headers: dict[str, str], mocker: MockerFixture
) -> None:
    mocker.patch.object(controller.settings, "resumo_latencia_simulada", (0.0, 0.0))

    resposta = await client.get("/resumo/1", params={"produto_id": 2}, headers=auth_headers)

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

    mocker.patch.object(controller.settings, "resumo_latencia_simulada", (0.0, 0.0))
    mocker.patch.object(controller.settings, "resumo_timeout", 0.05)
    mocker.patch.object(fontes, "estoque_service", lenta)

    resposta = await client.get("/resumo/1", params={"produto_id": 2}, headers=auth_headers)

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
    mocker.patch.object(controller.settings, "resumo_latencia_simulada", (0.2, 0.2))

    inicio = asyncio.get_event_loop().time()
    await controller.resumir(cliente_id=1, produto_id=1)
    duracao = asyncio.get_event_loop().time() - inicio

    assert duracao < 0.5


@pytest.mark.asyncio
async def test_erro_nao_retentavel_aborta_na_primeira_tentativa(
    mocker: MockerFixture,
) -> None:
    chamadas = {"n": 0}

    async def nao_autorizado() -> dict[str, Any]:
        chamadas["n"] += 1
        raise FonteError(401)

    dormir = mocker.patch.object(asyncio, "sleep")

    resultado = await controller._consultar_fonte("financeiro", nao_autorizado)

    assert resultado.disponivel is False
    assert resultado.tentativas == 1
    assert resultado.erro == "HTTP 401 (não retentável)"
    assert chamadas["n"] == 1
    dormir.assert_not_called()


@pytest.mark.asyncio
async def test_429_espera_o_retry_after_antes_de_tentar_de_novo(
    mocker: MockerFixture,
) -> None:
    chamadas = {"n": 0}

    async def limitado() -> dict[str, Any]:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise FonteError(429, retry_after=5.0)
        return {"ok": True}

    dormir = mocker.patch.object(asyncio, "sleep")

    resultado = await controller._consultar_fonte("estoque", limitado)

    assert resultado.disponivel is True
    assert resultado.tentativas == 2
    assert dormir.call_args[0][0] >= 5.0


@pytest.mark.asyncio
async def test_backoff_cresce_exponencialmente(mocker: MockerFixture) -> None:
    async def indisponivel() -> dict[str, Any]:
        raise FonteError(503)

    mocker.patch.object(controller.settings, "resumo_tentativas", 3)
    dormir = mocker.patch.object(asyncio, "sleep")

    resultado = await controller._consultar_fonte("cliente", indisponivel)

    assert resultado.disponivel is False
    assert resultado.tentativas == 3
    esperas = [chamada.args[0] for chamada in dormir.call_args_list]
    assert len(esperas) == 2
    assert esperas[1] > esperas[0]
    assert (
        esperas[1]
        <= controller.settings.resumo_backoff_teto + controller.settings.resumo_backoff_base
    )
