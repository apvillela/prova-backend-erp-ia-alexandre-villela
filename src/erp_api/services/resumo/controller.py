import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from erp_api import config
from erp_api.services.resumo import fontes
from erp_api.services.resumo.schemas import FonteResultado, ResumoResponse

settings = config.get_settings()

log = logging.getLogger(__name__)


async def _consultar_fonte(
    nome: str, consulta: Callable[[], Awaitable[dict[str, Any]]]
) -> FonteResultado:
    """Timeout e retry por fonte: uma fonte lenta ou fora do ar degrada só o próprio campo."""
    tentativas = settings.resumo_tentativas
    for tentativa in range(1, tentativas + 1):
        try:
            dados = await asyncio.wait_for(consulta(), timeout=settings.resumo_timeout)
        except TimeoutError:
            log.warning(f"Timeout na fonte {nome} (tentativa {tentativa}/{tentativas})")
            erro = f"Timeout após {settings.resumo_timeout}s"
        except Exception as e:
            log.warning(f"Erro na fonte {nome} (tentativa {tentativa}/{tentativas}): {e}")
            erro = type(e).__name__
        else:
            return FonteResultado(disponivel=True, tentativas=tentativa, dados=dados)

    return FonteResultado(disponivel=False, tentativas=tentativas, erro=erro)


async def resumir(cliente_id: int, produto_id: int) -> ResumoResponse:
    estoque, financeiro, cliente = await asyncio.gather(
        _consultar_fonte("estoque", lambda: fontes.estoque_service(produto_id)),
        _consultar_fonte("financeiro", lambda: fontes.financeiro_service(cliente_id)),
        _consultar_fonte("cliente", lambda: fontes.cliente_service(cliente_id)),
    )

    return ResumoResponse(
        completo=all(f.disponivel for f in (estoque, financeiro, cliente)),
        estoque=estoque,
        financeiro=financeiro,
        cliente=cliente,
    )
