from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture

load_dotenv("./tests/.env.test", override=True)


def pytest_configure(config: pytest.Config) -> None:
    from erp_api import config as api_config

    settings = api_config.get_settings()

    if settings.app_env != "TEST":
        reason = "Failed to load test environment config"
        pytest.exit(reason)


@pytest.fixture(autouse=True)
def avoid_request_communication(mocker: MockerFixture) -> None:
    """Rede de segurança: qualquer request HTTP real não mockado falha o teste."""

    def fail(*args: Any, **kwargs: Any) -> None:
        msg = "Communication disabled for tests"
        raise RuntimeError(msg)

    async def async_fail(*args: Any, **kwargs: Any) -> None:
        msg = "Communication disabled for tests"
        raise RuntimeError(msg)

    mocker.patch("httpx.Client.send", new=fail)
    mocker.patch("httpx.AsyncHTTPTransport.__aenter__", new=async_fail)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from erp_api.authentication import create_access_token

    return {"Authorization": f"Bearer {create_access_token('tester')}"}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client ASGI da aplicação (não sobe o lifespan, então não toca Postgres/Redis)."""
    from erp_api import main

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
