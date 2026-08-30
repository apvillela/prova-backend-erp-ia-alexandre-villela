import pytest
from httpx import AsyncClient

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.asyncio
async def test_metrics_expoe_formato_prometheus(client: AsyncClient) -> None:
    await client.get("/health_check")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
