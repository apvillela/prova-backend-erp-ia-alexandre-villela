import re
import unicodedata

from erp_api.services.agente.schemas import ChamadaFerramenta

_NUMERO = r"(\d+(?:[.,]\d+)?)"


def _normalizar(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acentos.lower().strip()


def _numero(valor: str) -> float:
    return float(valor.replace(",", "."))


def _interpretar_historico(texto: str) -> ChamadaFerramenta:
    """Após a palavra-chave, descarta ligações ("de movimentações", "de estoque"); o que
    sobrar depois de "do/da/dos/das" é o nome do produto.
    """  # noqa: D205
    resto = re.sub(r"^.*?(?:historico|movimentac\w+)\s*", "", texto)
    resto = re.sub(r"^(?:(?:de\s+)?(?:movimentac\w+|estoque)\s*)*", "", resto)
    termo = ""
    if m := re.match(r"d[oea]s?\s+(.+)", resto):
        termo = m.group(1).strip(" ?!.")
    return ChamadaFerramenta(
        ferramenta="historico_movimentacoes",
        parametros={"produto": termo} if termo else {},
        confianca=0.9,
    )


def interpretar(pergunta: str) -> ChamadaFerramenta | None:
    """NLU determinístico por regras; num LLM real, esta é a única camada substituída."""
    texto = _normalizar(pergunta)

    if m := re.search(rf"estoque\s+(?:abaixo|menor)\s+(?:de|que)\s+{_NUMERO}", texto):
        return ChamadaFerramenta(
            ferramenta="consultar_estoque_baixo",
            parametros={"limite": int(_numero(m.group(1)))},
            confianca=0.95,
        )

    if m := re.search(rf"menos\s+(?:de|que)\s+{_NUMERO}\s+unidades?", texto):
        return ChamadaFerramenta(
            ferramenta="consultar_estoque_baixo",
            parametros={"limite": int(_numero(m.group(1)))},
            confianca=0.9,
        )

    if re.search(r"estoque\s+baixo|acabando|repor", texto):
        return ChamadaFerramenta(ferramenta="consultar_estoque_baixo", parametros={}, confianca=0.8)

    if re.search(r"quantos\s+produtos|total\s+de\s+produtos", texto):
        return ChamadaFerramenta(ferramenta="contar_produtos", parametros={}, confianca=0.95)

    if re.search(r"historico|movimentac", texto):
        return _interpretar_historico(texto)

    if m := re.search(rf"entre\s+{_NUMERO}\s+e\s+{_NUMERO}", texto):
        return ChamadaFerramenta(
            ferramenta="buscar_produtos",
            parametros={"preco_min": _numero(m.group(1)), "preco_max": _numero(m.group(2))},
            confianca=0.9,
        )

    if m := re.search(rf"(?:mais\s+barat\w+|abaixo)\s+(?:de|que)\s+(?:r\$\s*)?{_NUMERO}", texto):
        return ChamadaFerramenta(
            ferramenta="buscar_produtos",
            parametros={"preco_max": _numero(m.group(1))},
            confianca=0.85,
        )

    if m := re.search(rf"(?:mais\s+car\w+|acima)\s+(?:de|que)\s+(?:r\$\s*)?{_NUMERO}", texto):
        return ChamadaFerramenta(
            ferramenta="buscar_produtos",
            parametros={"preco_min": _numero(m.group(1))},
            confianca=0.85,
        )

    return _interpretar_busca_por_nome(texto)


def _interpretar_busca_por_nome(texto: str) -> ChamadaFerramenta | None:
    m = re.search(
        r"(?:preco\s+d[oea]s?|quanto\s+custa[m]?|busca?r?|procur\w+|listar?)\s+(?:o\s|a\s|os\s|as\s)?(.+)",
        texto,
    )
    if m is None:
        return None
    termo = m.group(1).strip(" ?!.")
    termo = re.sub(r"^produtos?\s*", "", termo).strip()
    if not termo:
        return None
    return ChamadaFerramenta(
        ferramenta="buscar_produtos", parametros={"nome": termo}, confianca=0.7
    )
