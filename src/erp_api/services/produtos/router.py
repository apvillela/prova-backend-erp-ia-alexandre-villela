from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api.authentication import CurrentUser, get_current_user
from erp_api.database import get_session
from erp_api.services.produtos import controller
from erp_api.services.produtos.schemas import (
    MovimentacoesPage,
    ProdutoCreate,
    ProdutoFilters,
    ProdutoResponse,
    ProdutosPage,
    ProdutoUpdate,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]
Filters = Annotated[ProdutoFilters, Query()]


@router.post("", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
async def criar(session: Session, dados: ProdutoCreate, usuario: CurrentUser) -> ProdutoResponse:
    return await controller.criar(session, dados, usuario)


@router.get("", response_model=ProdutosPage)
async def listar(session: Session, filtros: Filters) -> ProdutosPage:
    return await controller.listar(session, filtros)


@router.get("/{produto_id}", response_model=ProdutoResponse)
async def obter(session: Session, produto_id: int) -> ProdutoResponse:
    return await controller.obter(session, produto_id)


@router.patch("/{produto_id}", response_model=ProdutoResponse)
async def atualizar(
    session: Session, produto_id: int, dados: ProdutoUpdate, usuario: CurrentUser
) -> ProdutoResponse:
    return await controller.atualizar(session, produto_id, dados, usuario)


@router.get("/{produto_id}/movimentacoes", response_model=MovimentacoesPage)
async def listar_movimentacoes(
    session: Session,
    produto_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MovimentacoesPage:
    return await controller.listar_movimentacoes(session, produto_id, page, size)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir(session: Session, produto_id: int) -> None:
    await controller.excluir(session, produto_id)
