from typing import Any

import pytest
from httpx import AsyncClient

pytest_plugins = ("pytest_asyncio",)


async def _criar_produto(client: AsyncClient, headers: dict[str, str], **campos: Any) -> None:
    response = await client.post("/produtos", json=campos, headers=headers)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_pergunta_de_estoque_baixo(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar_produto(
        client, auth_headers, nome="Cabo HDMI", preco="25.00", quantidade_em_estoque=2
    )
    await _criar_produto(
        client, auth_headers, nome="Notebook", preco="4500.00", quantidade_em_estoque=30
    )

    resposta = await client.post(
        "/agente/perguntar",
        json={"pergunta": "quais produtos estão com estoque abaixo de 10 unidades?"},
        headers=auth_headers,
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ferramenta"] == "consultar_estoque_baixo"
    assert corpo["parametros"] == {"limite": 10}
    assert [p["nome"] for p in corpo["resultado"]["produtos"]] == ["Cabo HDMI"]


@pytest.mark.asyncio
async def test_pergunta_nao_entendida(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resposta = await client.post(
        "/agente/perguntar",
        json={"pergunta": "xyz abc 123?"},
        headers=auth_headers,
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["ferramenta"] is None
    assert corpo["confianca"] == 0.0
    assert "Não entendi" in corpo["mensagem"]


@pytest.mark.asyncio
async def test_lista_ferramentas_expostas(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resposta = await client.get("/agente/ferramentas", headers=auth_headers)

    assert resposta.status_code == 200
    nomes = {f["nome"] for f in resposta.json()}
    assert nomes == {
        "consultar_estoque_baixo",
        "buscar_produtos",
        "contar_produtos",
        "historico_movimentacoes",
    }
