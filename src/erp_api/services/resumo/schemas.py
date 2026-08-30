from typing import Any

from pydantic import BaseModel


class FonteResultado(BaseModel):
    disponivel: bool
    tentativas: int
    dados: dict[str, Any] | None = None
    erro: str | None = None


class ResumoResponse(BaseModel):
    completo: bool
    estoque: FonteResultado
    financeiro: FonteResultado
    cliente: FonteResultado
