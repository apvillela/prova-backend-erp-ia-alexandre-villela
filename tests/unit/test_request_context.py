import pytest
from httpx import AsyncClient

from erp_api.middlewares import REQUEST_ID_HEADER

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_gera_request_id_quando_nao_recebe(client: AsyncClient) -> None:
    response = await client.get("/health_check")

    assert response.headers[REQUEST_ID_HEADER]


@pytest.mark.asyncio
async def test_propaga_request_id_recebido(client: AsyncClient) -> None:
    response = await client.get("/health_check", headers={REQUEST_ID_HEADER: "req-123"})

    assert response.headers[REQUEST_ID_HEADER] == "req-123"
