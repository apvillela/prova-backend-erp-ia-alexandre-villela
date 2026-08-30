from typing import Any

import pytest
from httpx import AsyncClient

from erp_api import config

pytest_plugins = ("pytest_asyncio",)

settings = config.get_settings()


async def _criar_produto(client: AsyncClient, headers: dict[str, str], **campos: Any) -> int:
    response = await client.post("/produtos", json=campos, headers=headers)
    assert response.status_code == 201
    produto_id: int = response.json()["id"]
    return produto_id


@pytest.mark.asyncio
async def test_criacao_registra_entrada(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    produto_id = await _criar_produto(
        client, auth_headers, nome="Teclado", preco="100.00", quantidade_em_estoque=5
    )

    resposta = await client.get(f"/produtos/{produto_id}/movimentacoes", headers=auth_headers)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 1
    movimentacao = corpo["items"][0]
    assert movimentacao["tipo"] == "entrada"
    assert movimentacao["quantidade"] == 5
    assert movimentacao["quantidade_resultante"] == 5
    assert movimentacao["usuario"] == settings.auth_username


@pytest.mark.asyncio
async def test_atualizacao_de_quantidade_registra_saida(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    produto_id = await _criar_produto(
        client, auth_headers, nome="Mouse", preco="50.00", quantidade_em_estoque=10
    )

    resposta = await client.patch(
        f"/produtos/{produto_id}",
        json={"quantidade_em_estoque": 3},
        headers=auth_headers,
    )
    assert resposta.status_code == 200

    corpo = (await client.get(f"/produtos/{produto_id}/movimentacoes", headers=auth_headers)).json()
    assert corpo["total"] == 2
    saida = corpo["items"][0]  # mais recente primeiro
    assert saida["tipo"] == "saida"
    assert saida["quantidade"] == 7
    assert saida["quantidade_resultante"] == 3


@pytest.mark.asyncio
async def test_atualizacao_sem_mudar_quantidade_nao_registra(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    produto_id = await _criar_produto(
        client, auth_headers, nome="Monitor", preco="900.00", quantidade_em_estoque=4
    )

    resposta = await client.patch(
        f"/produtos/{produto_id}", json={"preco": "850.00"}, headers=auth_headers
    )
    assert resposta.status_code == 200

    corpo = (await client.get(f"/produtos/{produto_id}/movimentacoes", headers=auth_headers)).json()
    assert corpo["total"] == 1


@pytest.mark.asyncio
async def test_movimentacoes_de_produto_inexistente_retorna_404(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resposta = await client.get("/produtos/9999/movimentacoes", headers=auth_headers)
    assert resposta.status_code == 404


@pytest.mark.asyncio
async def test_agente_responde_historico(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar_produto(
        client, auth_headers, nome="Webcam", preco="200.00", quantidade_em_estoque=8
    )

    resposta = await client.post(
        "/agente/perguntar",
        json={"pergunta": "qual o histórico de movimentações da webcam?"},
        headers=auth_headers,
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ferramenta"] == "historico_movimentacoes"
    assert corpo["parametros"] == {"produto": "webcam"}
    assert corpo["resultado"]["movimentacoes"][0]["produto"] == "Webcam"
    assert corpo["resultado"]["movimentacoes"][0]["tipo"] == "entrada"
