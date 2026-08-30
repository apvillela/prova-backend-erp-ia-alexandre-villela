from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from pytest_mock import MockerFixture
from redis.exceptions import ConnectionError as RedisConnectionError

from erp_api import caching

pytest_plugins = ("pytest_asyncio",)

PRODUTO = {"nome": "Cadeira", "preco": "800.00", "quantidade_em_estoque": 4}


@pytest_asyncio.fixture
async def cache() -> AsyncIterator[None]:
    client = caching.get_redis_async_client()
    try:
        await client.ping()
    except (RedisConnectionError, OSError):
        pytest.skip("redis indisponível")

    await client.flushdb()
    yield


async def _entry_keys(redis: Any) -> list[str]:
    keys: list[str] = await redis.keys("cache:produtos:v*")
    return sorted(k for k in keys if not k.endswith(":versao"))


async def _criar(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.post("/produtos", json=PRODUTO, headers=headers)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.asyncio
async def test_leitura_popula_cache_e_escrita_invalida(
    database: None, cache: None, client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    criado = await _criar(client, auth_headers)
    redis = caching.get_redis_async_client()

    await client.get(f"/produtos/{criado['id']}", headers=auth_headers)
    keys_antes = await _entry_keys(redis)
    assert len(keys_antes) == 1

    resposta = await client.patch(
        f"/produtos/{criado['id']}", json={"preco": "700.00"}, headers=auth_headers
    )
    assert resposta.status_code == 200

    resposta = await client.get(f"/produtos/{criado['id']}", headers=auth_headers)
    assert resposta.json()["preco"] == "700.00"

    keys_depois = await _entry_keys(redis)
    assert keys_depois != keys_antes


@pytest.mark.asyncio
async def test_leitura_funciona_com_redis_fora(
    database: None,
    client: AsyncClient,
    auth_headers: dict[str, str],
    mocker: MockerFixture,
) -> None:
    criado = await _criar(client, auth_headers)

    quebrado = mocker.AsyncMock()
    quebrado.get.side_effect = RedisConnectionError
    quebrado.set.side_effect = RedisConnectionError
    quebrado.incr.side_effect = RedisConnectionError
    mocker.patch("erp_api.caching.functions.get_redis_async_client", return_value=quebrado)

    resposta = await client.get(f"/produtos/{criado['id']}", headers=auth_headers)

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Cadeira"
