from fastapi import APIRouter, Depends

from erp_api.authentication import get_current_user
from erp_api.services.resumo import controller
from erp_api.services.resumo.schemas import ResumoResponse

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{cliente_id}", response_model=ResumoResponse)
async def resumir(cliente_id: int, produto_id: int) -> ResumoResponse:
    return await controller.resumir(cliente_id, produto_id)
