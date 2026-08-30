from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from erp_api import config
from erp_api.authentication import get_current_user
from erp_api.caching import hit_rate_limit
from erp_api.services.alertas import controller
from erp_api.services.alertas.schemas import AlertaEstoqueBaixo, VerificacaoEnfileirada

settings = config.get_settings()

router = APIRouter(dependencies=[Depends(get_current_user)])


async def rate_limit_verificacao(user: Annotated[str, Depends(get_current_user)]) -> None:
    retry = await hit_rate_limit(
        f"verificar-estoque:{user}",
        settings.rate_limit_verificar_max,
        settings.rate_limit_verificar_janela,
    )
    if retry is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=[{"msg": f"Muitas verificações seguidas; tente de novo em {retry}s."}],
            headers={"Retry-After": str(retry)},
        )


@router.get("/estoque-baixo", response_model=list[AlertaEstoqueBaixo])
async def listar(quantidade: Annotated[int, Query(ge=1, le=100)] = 10) -> list[AlertaEstoqueBaixo]:
    return await controller.listar_alertas(quantidade)


@router.post(
    "/estoque-baixo/verificar",
    response_model=VerificacaoEnfileirada,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_verificacao)],
)
async def verificar() -> VerificacaoEnfileirada:
    return await controller.solicitar_verificacao()
