"""Servidor MCP do ERP: fachada fina sobre a API REST.

Cada tool consome os mesmos endpoints HTTP (com o mesmo login JWT) que qualquer
cliente — nenhum acesso direto a banco, então autorização, rate limit e auditoria
da API valem também pro agente. Roda por stdio:

    uv run python bin/mcp_server.py

Config via env: ERP_API_URL, ERP_API_USER, ERP_API_PASS (defaults do .env.example).
"""

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

API_URL = os.environ.get("ERP_API_URL", "http://localhost:8000")
API_USER = os.environ.get("ERP_API_USER", "lidertecnica")
API_PASS = os.environ.get("ERP_API_PASS", "password123!")

mcp = MCPServer("erp-produtos-estoque")


def _headers(client: httpx.Client) -> dict[str, str]:
    # Login a cada chamada: sessões MCP são curtas e isso dispensa lidar com expiração.
    resposta = client.post(
        f"{API_URL}/auth/login", json={"username": API_USER, "password": API_PASS}
    )
    resposta.raise_for_status()
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def _get(caminho: str, params: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=10) as client:
        resposta = client.get(f"{API_URL}{caminho}", params=params, headers=_headers(client))
        resposta.raise_for_status()
        return resposta.json()


@mcp.tool()
def consultar_estoque_baixo(limite: int = 10) -> Any:
    """Lista produtos com estoque abaixo de um limite de unidades."""
    return _get(
        "/produtos",
        {"estoque_abaixo_de": limite, "ordenar_por": "quantidade_em_estoque", "ordem": "asc"},
    )


@mcp.tool()
def buscar_produtos(
    nome: str | None = None, preco_min: float | None = None, preco_max: float | None = None
) -> Any:
    """Busca produtos por nome e/ou faixa de preço."""
    params = {"nome": nome, "preco_min": preco_min, "preco_max": preco_max}
    return _get("/produtos", {k: v for k, v in params.items() if v is not None})


@mcp.tool()
def contar_produtos() -> Any:
    """Retorna o total de produtos cadastrados."""
    return {"total": _get("/produtos", {"size": 1})["total"]}


@mcp.tool()
def historico_movimentacoes(produto_id: int) -> Any:
    """Lista o histórico de movimentações de estoque (entradas e saídas) de um produto."""
    return _get(f"/produtos/{produto_id}/movimentacoes")


@mcp.tool()
def perguntar(pergunta: str) -> Any:
    """Faz uma pergunta em linguagem natural pro agente do ERP."""
    with httpx.Client(timeout=15) as client:
        resposta = client.post(
            f"{API_URL}/agente/perguntar",
            json={"pergunta": pergunta},
            headers=_headers(client),
        )
        resposta.raise_for_status()
        return resposta.json()


if __name__ == "__main__":
    mcp.run()
