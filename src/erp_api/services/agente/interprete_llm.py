import json
import logging

import httpx

from erp_api import config
from erp_api.services.agente.ferramentas import FERRAMENTAS
from erp_api.services.agente.schemas import ChamadaFerramenta

settings = config.get_settings()

log = logging.getLogger(__name__)

# O modelo não devolve confiança calibrada; fica abaixo das regras exatas (0.9+) de propósito,
# pra ser visível na resposta qual caminho interpretou.
CONFIANCA_LLM = 0.85

PROMPT_SISTEMA = (
    "Você traduz perguntas sobre um ERP em chamadas de ferramenta. Ferramentas disponíveis "
    "(nome, descrição e parâmetros):\n{ferramentas}\n\n"
    'Responda SOMENTE com JSON no formato {{"ferramenta": "<nome>", "parametros": {{...}}}}. '
    'Se nenhuma ferramenta responder a pergunta, responda {{"ferramenta": null}}.'
)


def _spec_ferramentas() -> str:
    return json.dumps([spec.model_dump() for spec, _ in FERRAMENTAS.values()], ensure_ascii=False)


def parsear_chamada(conteudo: str) -> ChamadaFerramenta | None:
    """Valida a saída do modelo: ferramenta fora do registry ou JSON inválido viram None."""
    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError:
        return None
    if not isinstance(dados, dict):
        return None
    nome = dados.get("ferramenta")
    parametros = dados.get("parametros") or {}
    if nome not in FERRAMENTAS or not isinstance(parametros, dict):
        return None
    return ChamadaFerramenta(ferramenta=nome, parametros=parametros, confianca=CONFIANCA_LLM)


async def interpretar_llm(pergunta: str) -> ChamadaFerramenta | None:
    """Interpreta via LLM local (API do Ollama); qualquer falha vira None e o chamador degrada."""
    try:
        async with httpx.AsyncClient(timeout=settings.agente_llm_timeout) as client:
            resposta = await client.post(
                f"{settings.agente_llm_url}/api/chat",
                json={
                    "model": settings.agente_llm_modelo,
                    "messages": [
                        {
                            "role": "system",
                            "content": PROMPT_SISTEMA.format(ferramentas=_spec_ferramentas()),
                        },
                        {"role": "user", "content": pergunta},
                    ],
                    "stream": False,
                    "format": "json",
                },
            )
            resposta.raise_for_status()
            conteudo = resposta.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning(f"LLM local indisponível ({type(e).__name__}); degradando pras regras")
        return None
    return parsear_chamada(conteudo)
