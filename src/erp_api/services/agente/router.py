from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from erp_api.authentication import get_current_user
from erp_api.database import get_session
from erp_api.services.agente import controller
from erp_api.services.agente.ferramentas import FERRAMENTAS, Ferramenta
from erp_api.services.agente.schemas import Pergunta, RespostaAgente

router = APIRouter(dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/perguntar", response_model=RespostaAgente)
async def perguntar(session: Session, corpo: Pergunta) -> RespostaAgente:
    return await controller.perguntar(session, corpo.pergunta)


@router.get("/ferramentas", response_model=list[Ferramenta])
def ferramentas() -> list[Ferramenta]:
    return [spec for spec, _ in FERRAMENTAS.values()]
