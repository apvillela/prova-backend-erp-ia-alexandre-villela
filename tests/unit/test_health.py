import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_readiness_com_dependencias_ok(client: AsyncClient, mocker: MockerFixture) -> None:
    mocker.patch("erp_api.services.health.controller.database.check_connection")
    mocker.patch(
        "erp_api.services.health.controller.get_redis_async_client",
        return_value=mocker.AsyncMock(),
    )

    response = await client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "postgres": {"healthy": True, "detail": None},
        "redis": {"healthy": True, "detail": None},
    }


@pytest.mark.asyncio
async def test_readiness_retorna_503_com_banco_fora(
    client: AsyncClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "erp_api.services.health.controller.database.check_connection",
        side_effect=ConnectionRefusedError,
    )
    mocker.patch(
        "erp_api.services.health.controller.get_redis_async_client",
        return_value=mocker.AsyncMock(),
    )

    response = await client.get("/health/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["postgres"] == {"healthy": False, "detail": "ConnectionRefusedError"}
