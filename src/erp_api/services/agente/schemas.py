from typing import Any

from pydantic import BaseModel, Field


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=500)


class ChamadaFerramenta(BaseModel):
    ferramenta: str
    parametros: dict[str, Any]
    confianca: float = Field(ge=0, le=1)


class RespostaAgente(BaseModel):
    pergunta: str
    ferramenta: str | None
    parametros: dict[str, Any]
    confianca: float
    resultado: Any
    mensagem: str
    interprete: str = "regras"  # llm | regras | nenhum
