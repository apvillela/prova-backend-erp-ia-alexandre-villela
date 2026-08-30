from decimal import Decimal
from typing import Any, Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api import config
from erp_api.services.produtos.models import Produto

settings = config.get_settings()

Executor = Callable[[AsyncSession, dict[str, Any]], Awaitable[Any]]


class Ferramenta(BaseModel):
    """Contrato no formato de function calling: o mesmo spec serve para um LLM real no futuro."""

    nome: str
    descricao: str
    parametros: dict[str, Any]

    model_config = {"frozen": True}


def _produto_para_dict(produto: Produto) -> dict[str, Any]:
    return {
        "id": produto.id,
        "nome": produto.nome,
        "preco": str(produto.preco),
        "quantidade_em_estoque": produto.quantidade_em_estoque,
    }


async def _consultar_estoque_baixo(session: AsyncSession, params: dict[str, Any]) -> Any:
    limite = int(params.get("limite") or settings.estoque_baixo_limite)
    query = (
        select(Produto)
        .where(Produto.quantidade_em_estoque < limite)
        .order_by(Produto.quantidade_em_estoque)
    )
    produtos = (await session.scalars(query)).all()
    return {"limite": limite, "produtos": [_produto_para_dict(p) for p in produtos]}


async def _buscar_produtos(session: AsyncSession, params: dict[str, Any]) -> Any:
    query = select(Produto).order_by(Produto.nome)
    if nome := params.get("nome"):
        query = query.where(Produto.nome.ilike(f"%{nome}%"))
    if (preco_min := params.get("preco_min")) is not None:
        query = query.where(Produto.preco >= Decimal(str(preco_min)))
    if (preco_max := params.get("preco_max")) is not None:
        query = query.where(Produto.preco <= Decimal(str(preco_max)))
    produtos = (await session.scalars(query.limit(50))).all()
    return {"produtos": [_produto_para_dict(p) for p in produtos]}


async def _contar_produtos(session: AsyncSession, params: dict[str, Any]) -> Any:
    total = await session.scalar(select(func.count()).select_from(Produto)) or 0
    return {"total": total}


FERRAMENTAS: dict[str, tuple[Ferramenta, Executor]] = {
    "consultar_estoque_baixo": (
        Ferramenta(
            nome="consultar_estoque_baixo",
            descricao="Lista produtos com estoque abaixo de um limite de unidades",
            parametros={"limite": {"type": "integer", "required": False}},
        ),
        _consultar_estoque_baixo,
    ),
    "buscar_produtos": (
        Ferramenta(
            nome="buscar_produtos",
            descricao="Busca produtos por nome e/ou faixa de preço",
            parametros={
                "nome": {"type": "string", "required": False},
                "preco_min": {"type": "number", "required": False},
                "preco_max": {"type": "number", "required": False},
            },
        ),
        _buscar_produtos,
    ),
    "contar_produtos": (
        Ferramenta(
            nome="contar_produtos",
            descricao="Retorna o total de produtos cadastrados",
            parametros={},
        ),
        _contar_produtos,
    ),
}
