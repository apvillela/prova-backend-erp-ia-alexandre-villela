import logging

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api.exceptions import ConflictError, NotFoundError
from erp_api.services.produtos.models import Produto
from erp_api.services.produtos.schemas import (
    ProdutoCreate,
    ProdutoFilters,
    ProdutoResponse,
    ProdutosPage,
    ProdutoUpdate,
)

log = logging.getLogger(__name__)

PRODUTO_NAO_ENCONTRADO = "Produto não encontrado."
NOME_JA_EXISTE = "Já existe um produto com esse nome."


async def criar(session: AsyncSession, dados: ProdutoCreate) -> ProdutoResponse:
    produto = Produto(**dados.model_dump())
    session.add(produto)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(NOME_JA_EXISTE) from e
    await session.refresh(produto)
    return ProdutoResponse.model_validate(produto)


async def obter(session: AsyncSession, produto_id: int) -> ProdutoResponse:
    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)
    return ProdutoResponse.model_validate(produto)


def _aplicar_filtros(
    query: Select[tuple[Produto]], filtros: ProdutoFilters
) -> Select[tuple[Produto]]:
    if filtros.nome:
        query = query.where(Produto.nome.ilike(f"%{filtros.nome}%"))
    if filtros.preco_min is not None:
        query = query.where(Produto.preco >= filtros.preco_min)
    if filtros.preco_max is not None:
        query = query.where(Produto.preco <= filtros.preco_max)
    if filtros.estoque_abaixo_de is not None:
        query = query.where(Produto.quantidade_em_estoque < filtros.estoque_abaixo_de)
    return query


async def listar(session: AsyncSession, filtros: ProdutoFilters) -> ProdutosPage:
    query = _aplicar_filtros(select(Produto), filtros)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0

    query = query.order_by(Produto.id).offset((filtros.page - 1) * filtros.size).limit(filtros.size)
    produtos = (await session.scalars(query)).all()

    return ProdutosPage(
        items=[ProdutoResponse.model_validate(p) for p in produtos],
        total=total,
        page=filtros.page,
        size=filtros.size,
    )


async def atualizar(
    session: AsyncSession, produto_id: int, dados: ProdutoUpdate
) -> ProdutoResponse:
    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(NOME_JA_EXISTE) from e
    await session.refresh(produto)
    return ProdutoResponse.model_validate(produto)


async def excluir(session: AsyncSession, produto_id: int) -> None:
    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)
    await session.delete(produto)
    await session.commit()
