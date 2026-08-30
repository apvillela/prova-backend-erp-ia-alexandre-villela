import logging

from sqlalchemy.ext.asyncio import AsyncSession

from erp_api.services.agente.ferramentas import FERRAMENTAS
from erp_api.services.agente.interprete import interpretar
from erp_api.services.agente.schemas import RespostaAgente

log = logging.getLogger(__name__)

MENSAGEM_NAO_ENTENDIDA = (
    "Não entendi a pergunta. Exemplos: 'quais produtos estão com estoque abaixo de 10 unidades?', "
    "'quantos produtos temos?', 'produtos entre 50 e 200 reais'."
)


async def perguntar(session: AsyncSession, pergunta: str) -> RespostaAgente:
    chamada = interpretar(pergunta)

    if chamada is None:
        return RespostaAgente(
            pergunta=pergunta,
            ferramenta=None,
            parametros={},
            confianca=0.0,
            resultado=None,
            mensagem=MENSAGEM_NAO_ENTENDIDA,
        )

    _, executor = FERRAMENTAS[chamada.ferramenta]
    resultado = await executor(session, chamada.parametros)

    log.info(
        f"Agente: '{pergunta}' -> {chamada.ferramenta}({chamada.parametros}) "
        f"[confiança {chamada.confianca}]"
    )

    return RespostaAgente(
        pergunta=pergunta,
        ferramenta=chamada.ferramenta,
        parametros=chamada.parametros,
        confianca=chamada.confianca,
        resultado=resultado,
        mensagem="ok",
    )
