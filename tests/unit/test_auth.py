import pytest
from httpx import AsyncClient

from erp_api.authentication import create_access_token, decode_access_token

pytest_plugins = ("pytest_asyncio",)


def test_token_roundtrip() -> None:
    token = create_access_token(subject="tester")

    assert decode_access_token(token) == "tester"


@pytest.mark.asyncio
async def test_login_com_credenciais_validas(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login", json={"username": "tester", "password": "tester-pass"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"  # noqa: S105
    assert decode_access_token(body["access_token"]) == "tester"


@pytest.mark.asyncio
async def test_login_com_senha_errada(client: AsyncClient) -> None:
    response = await client.post("/auth/login", json={"username": "tester", "password": "errada"})

    assert response.status_code == 401
    assert response.json() == {"detail": [{"msg": "Credenciais inválidas."}]}
