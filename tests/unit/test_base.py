import pytest
from httpx import AsyncClient

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health_check")

    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}
