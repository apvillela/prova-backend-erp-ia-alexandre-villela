import logging

from sqlalchemy.ext.asyncio import AsyncSession

from erp_api import config
from erp_api.services.agente.ferramentas import FERRAMENTAS
from erp_api.services.agente.interprete import interpretar
from erp_api.services.agente.interprete_llm import interpretar_llm
from erp_api.services.agente.schemas import ChamadaFerramenta, RespostaAgente

settings = config.get_settings()

log = logging.getLogger(__name__)

MENSAGEM_NAO_ENTENDIDA = (
    "Não entendi a pergunta. Exemplos: 'quais produtos estão com estoque abaixo de 10 unidades?', "
    "'quantos produtos temos?', 'produtos entre 50 e 200 reais'."
)


async def _interpretar(pergunta: str) -> tuple[ChamadaFerramenta | None, str]:
    """LLM local primeiro (quando configurado), regras como fallback — nunca o contrário:
    se o LLM cair, o agente continua respondendo com o interpretador determinístico.
    """  # noqa: D205
    if settings.agente_llm_url:
        chamada = await interpretar_llm(pergunta)
        if chamada is not None:
            return chamada, "llm"
    chamada = interpretar(pergunta)
    return chamada, "regras" if chamada else "nenhum"


async def perguntar(session: AsyncSession, pergunta: str) -> RespostaAgente:
    chamada, interprete = await _interpretar(pergunta)

    if chamada is None:
        return RespostaAgente(
            pergunta=pergunta,
            ferramenta=None,
            parametros={},
            confianca=0.0,
            resultado=None,
            mensagem=MENSAGEM_NAO_ENTENDIDA,
            interprete=interprete,
        )

    _, executor = FERRAMENTAS[chamada.ferramenta]
    resultado = await executor(session, chamada.parametros)

    log.info(
        f"Agente: '{pergunta}' -> {chamada.ferramenta}({chamada.parametros}) "
        f"[confiança {chamada.confianca}, via {interprete}]"
    )

    return RespostaAgente(
        pergunta=pergunta,
        ferramenta=chamada.ferramenta,
        parametros=chamada.parametros,
        confianca=chamada.confianca,
        resultado=resultado,
        mensagem="ok",
        interprete=interprete,
    )
