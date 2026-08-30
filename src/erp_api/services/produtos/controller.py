import logging

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api import config
from erp_api.caching import get_cached, invalidate_namespace, set_cached
from erp_api.exceptions import ConflictError, NotFoundError
from erp_api.services.produtos.models import MovimentacaoEstoque, Produto
from erp_api.services.produtos.schemas import (
    MovimentacaoResponse,
    MovimentacoesPage,
    ProdutoCreate,
    ProdutoFilters,
    ProdutoResponse,
    ProdutosPage,
    ProdutoUpdate,
)

settings = config.get_settings()

log = logging.getLogger(__name__)

CACHE_NAMESPACE = "produtos"

PRODUTO_NAO_ENCONTRADO = "Produto não encontrado."
NOME_JA_EXISTE = "Já existe um produto com esse nome."


def _registrar_movimentacao(
    session: AsyncSession, produto: Produto, delta: int, usuario: str
) -> None:
    """Entra na mesma transação da mudança de estoque: ou grava os dois, ou nenhum."""
    session.add(
        MovimentacaoEstoque(
            produto_id=produto.id,
            tipo="entrada" if delta > 0 else "saida",
            quantidade=abs(delta),
            quantidade_resultante=produto.quantidade_em_estoque,
            usuario=usuario,
        )
    )


async def criar(session: AsyncSession, dados: ProdutoCreate, usuario: str) -> ProdutoResponse:
    produto = Produto(**dados.model_dump())
    session.add(produto)
    try:
        await session.flush()
        if produto.quantidade_em_estoque > 0:
            _registrar_movimentacao(session, produto, produto.quantidade_em_estoque, usuario)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(NOME_JA_EXISTE) from e
    await session.refresh(produto)
    await invalidate_namespace(CACHE_NAMESPACE)
    return ProdutoResponse.model_validate(produto)


async def obter(session: AsyncSession, produto_id: int) -> ProdutoResponse:
    cache_key = f"id:{produto_id}"
    if cached := await get_cached(CACHE_NAMESPACE, cache_key):
        return ProdutoResponse.model_validate_json(cached)

    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)

    resposta = ProdutoResponse.model_validate(produto)
    await set_cached(
        CACHE_NAMESPACE, cache_key, resposta.model_dump_json(), settings.cache_ttl_produtos
    )
    return resposta


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
    cache_key = f"listagem:{filtros.model_dump_json()}"
    if cached := await get_cached(CACHE_NAMESPACE, cache_key):
        return ProdutosPage.model_validate_json(cached)

    query = _aplicar_filtros(select(Produto), filtros)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0

    if filtros.ordenar_por is not None:
        coluna = getattr(Produto, filtros.ordenar_por.value)
        query = query.order_by(coluna.desc() if filtros.ordem == "desc" else coluna.asc())
    query = query.order_by(Produto.id).offset((filtros.page - 1) * filtros.size).limit(filtros.size)
    produtos = (await session.scalars(query)).all()

    pagina = ProdutosPage(
        items=[ProdutoResponse.model_validate(p) for p in produtos],
        total=total,
        page=filtros.page,
        size=filtros.size,
    )
    await set_cached(
        CACHE_NAMESPACE, cache_key, pagina.model_dump_json(), settings.cache_ttl_produtos
    )
    return pagina


async def atualizar(
    session: AsyncSession, produto_id: int, dados: ProdutoUpdate, usuario: str
) -> ProdutoResponse:
    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)

    quantidade_anterior = produto.quantidade_em_estoque
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)

    delta = produto.quantidade_em_estoque - quantidade_anterior
    if delta != 0:
        _registrar_movimentacao(session, produto, delta, usuario)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(NOME_JA_EXISTE) from e
    await session.refresh(produto)
    await invalidate_namespace(CACHE_NAMESPACE)
    return ProdutoResponse.model_validate(produto)


async def excluir(session: AsyncSession, produto_id: int) -> None:
    produto = await session.get(Produto, produto_id)
    if produto is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)
    await session.delete(produto)
    await session.commit()
    await invalidate_namespace(CACHE_NAMESPACE)


async def listar_movimentacoes(
    session: AsyncSession, produto_id: int, page: int, size: int
) -> MovimentacoesPage:
    if await session.get(Produto, produto_id) is None:
        raise NotFoundError(PRODUTO_NAO_ENCONTRADO)

    base = select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == produto_id)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    query = base.order_by(MovimentacaoEstoque.id.desc()).offset((page - 1) * size).limit(size)
    movimentacoes = (await session.scalars(query)).all()

    return MovimentacoesPage(
        items=[MovimentacaoResponse.model_validate(m) for m in movimentacoes],
        total=total,
        page=page,
        size=size,
    )
