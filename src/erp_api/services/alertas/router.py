from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from erp_api.authentication import get_current_user
from erp_api.services.alertas import controller
from erp_api.services.alertas.schemas import AlertaEstoqueBaixo, VerificacaoEnfileirada

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/estoque-baixo", response_model=list[AlertaEstoqueBaixo])
async def listar(quantidade: Annotated[int, Query(ge=1, le=100)] = 10) -> list[AlertaEstoqueBaixo]:
    return await controller.listar_alertas(quantidade)


@router.post(
    "/estoque-baixo/verificar",
    response_model=VerificacaoEnfileirada,
    status_code=status.HTTP_202_ACCEPTED,
)
async def verificar() -> VerificacaoEnfileirada:
    return await controller.solicitar_verificacao()
