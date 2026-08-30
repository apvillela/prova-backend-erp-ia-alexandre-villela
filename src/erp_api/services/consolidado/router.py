from fastapi import APIRouter, Depends

from erp_api.authentication import get_current_user
from erp_api.services.consolidado import controller
from erp_api.services.consolidado.schemas import ConsolidadoResponse

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{cliente_id}", response_model=ConsolidadoResponse)
async def consolidar(cliente_id: int, produto_id: int) -> ConsolidadoResponse:
    return await controller.consolidar(cliente_id, produto_id)
