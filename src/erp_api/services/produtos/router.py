from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api.authentication import get_current_user
from erp_api.database import get_session
from erp_api.services.produtos import controller
from erp_api.services.produtos.schemas import (
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
async def criar(session: Session, dados: ProdutoCreate) -> ProdutoResponse:
    return await controller.criar(session, dados)


@router.get("", response_model=ProdutosPage)
async def listar(session: Session, filtros: Filters) -> ProdutosPage:
    return await controller.listar(session, filtros)


@router.get("/{produto_id}", response_model=ProdutoResponse)
async def obter(session: Session, produto_id: int) -> ProdutoResponse:
    return await controller.obter(session, produto_id)


@router.patch("/{produto_id}", response_model=ProdutoResponse)
async def atualizar(session: Session, produto_id: int, dados: ProdutoUpdate) -> ProdutoResponse:
    return await controller.atualizar(session, produto_id, dados)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir(session: Session, produto_id: int) -> None:
    await controller.excluir(session, produto_id)
