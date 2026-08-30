from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

pytest_plugins = ("pytest_asyncio",)

PRODUTO = {"nome": "Teclado mecânico", "preco": "199.90", "quantidade_em_estoque": 10}


async def _criar(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post("/produtos", json={**PRODUTO, **overrides}, headers=headers)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.asyncio
async def test_crud_completo(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    criado = await _criar(client, auth_headers)
    assert criado["nome"] == PRODUTO["nome"]
    assert Decimal(criado["preco"]) == Decimal("199.90")
    assert criado["data_criacao"]

    resposta = await client.get(f"/produtos/{criado['id']}", headers=auth_headers)
    assert resposta.status_code == 200

    resposta = await client.patch(
        f"/produtos/{criado['id']}", json={"preco": "149.90"}, headers=auth_headers
    )
    assert resposta.status_code == 200
    assert Decimal(resposta.json()["preco"]) == Decimal("149.90")

    resposta = await client.delete(f"/produtos/{criado['id']}", headers=auth_headers)
    assert resposta.status_code == 204

    resposta = await client.get(f"/produtos/{criado['id']}", headers=auth_headers)
    assert resposta.status_code == 404


@pytest.mark.asyncio
async def test_listagem_com_filtros_e_paginacao(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar(client, auth_headers, nome="Mouse", preco="50.00", quantidade_em_estoque=3)
    await _criar(client, auth_headers, nome="Monitor", preco="900.00", quantidade_em_estoque=20)
    await _criar(client, auth_headers, nome="Mousepad", preco="30.00", quantidade_em_estoque=5)

    resposta = await client.get("/produtos", params={"nome": "mouse"}, headers=auth_headers)
    assert resposta.status_code == 200
    assert {p["nome"] for p in resposta.json()["items"]} == {"Mouse", "Mousepad"}

    resposta = await client.get(
        "/produtos", params={"preco_min": "40", "preco_max": "100"}, headers=auth_headers
    )
    assert [p["nome"] for p in resposta.json()["items"]] == ["Mouse"]

    resposta = await client.get("/produtos", params={"estoque_abaixo_de": 10}, headers=auth_headers)
    assert {p["nome"] for p in resposta.json()["items"]} == {"Mouse", "Mousepad"}

    resposta = await client.get("/produtos", params={"page": 2, "size": 2}, headers=auth_headers)
    body = resposta.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_nome_duplicado_retorna_409(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _criar(client, auth_headers)

    resposta = await client.post("/produtos", json=PRODUTO, headers=auth_headers)

    assert resposta.status_code == 409


@pytest.mark.asyncio
async def test_validacao_de_payload(
    database: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    invalidos = [
        {**PRODUTO, "nome": "123"},
        {**PRODUTO, "preco": "-1"},
        {**PRODUTO, "quantidade_em_estoque": -5},
    ]
    for payload in invalidos:
        resposta = await client.post("/produtos", json=payload, headers=auth_headers)
        assert resposta.status_code == 422


@pytest.mark.asyncio
async def test_sem_token_retorna_401(client: AsyncClient) -> None:
    resposta = await client.get("/produtos")

    assert resposta.status_code == 401
