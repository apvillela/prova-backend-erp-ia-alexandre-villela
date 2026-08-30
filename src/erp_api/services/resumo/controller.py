import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

from erp_api import config
from erp_api.services.resumo import fontes
from erp_api.services.resumo.fontes import FonteError
from erp_api.services.resumo.schemas import FonteResultado, ResumoResponse

settings = config.get_settings()

log = logging.getLogger(__name__)

# Erros transitórios valem nova tentativa; os demais 4xx são erro do chamador e
# repetir a mesma chamada só repetiria a recusa.
STATUS_RETENTAVEIS = {408, 425, 429, 500, 502, 503, 504}


def _espera_backoff(tentativa: int, retry_after: float | None) -> float:
    exponencial = min(
        settings.resumo_backoff_base * 2 ** (tentativa - 1), settings.resumo_backoff_teto
    )
    jitter = random.uniform(0, settings.resumo_backoff_base / 2)  # noqa: S311
    com_jitter: float = exponencial + jitter
    if retry_after is not None:
        return max(com_jitter, retry_after)
    return com_jitter


async def _consultar_fonte(
    nome: str, consulta: Callable[[], Awaitable[dict[str, Any]]]
) -> FonteResultado:
    """Timeout e retry por fonte: uma fonte lenta ou fora do ar degrada só o próprio campo."""
    tentativas = settings.resumo_tentativas
    for tentativa in range(1, tentativas + 1):
        retry_after: float | None = None
        try:
            dados = await asyncio.wait_for(consulta(), timeout=settings.resumo_timeout)
        except TimeoutError:
            erro = f"Timeout após {settings.resumo_timeout}s"
        except FonteError as e:
            if e.status_code not in STATUS_RETENTAVEIS:
                log.warning(f"Fonte {nome} recusou com HTTP {e.status_code}; sem retry")
                return FonteResultado(
                    disponivel=False,
                    tentativas=tentativa,
                    erro=f"HTTP {e.status_code} (não retentável)",
                )
            erro = f"HTTP {e.status_code}"
            retry_after = e.retry_after
        except (ConnectionError, OSError) as e:
            erro = type(e).__name__
        else:
            return FonteResultado(disponivel=True, tentativas=tentativa, dados=dados)

        log.warning(f"Falha na fonte {nome} (tentativa {tentativa}/{tentativas}): {erro}")
        if tentativa < tentativas:
            await asyncio.sleep(_espera_backoff(tentativa, retry_after))

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
