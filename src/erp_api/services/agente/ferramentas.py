from decimal import Decimal
from typing import Any, Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api import config
from erp_api.services.produtos.models import MovimentacaoEstoque, Produto

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


async def _historico_movimentacoes(session: AsyncSession, params: dict[str, Any]) -> Any:
    query = select(MovimentacaoEstoque, Produto.nome).join(Produto)
    if nome := params.get("produto"):
        query = query.where(Produto.nome.ilike(f"%{nome}%"))
    query = query.order_by(MovimentacaoEstoque.id.desc()).limit(20)
    linhas = (await session.execute(query)).all()
    return {
        "movimentacoes": [
            {
                "produto": nome_produto,
                "tipo": m.tipo,
                "quantidade": m.quantidade,
                "quantidade_resultante": m.quantidade_resultante,
                "usuario": m.usuario,
                "criado_em": m.criado_em.isoformat(),
            }
            for m, nome_produto in linhas
        ]
    }


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
    "historico_movimentacoes": (
        Ferramenta(
            nome="historico_movimentacoes",
            descricao="Lista as últimas movimentações de estoque (entradas e saídas), "
            "opcionalmente filtradas por nome de produto",
            parametros={"produto": {"type": "string", "required": False}},
        ),
        _historico_movimentacoes,
    ),
}
