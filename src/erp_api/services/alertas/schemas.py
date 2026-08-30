from datetime import datetime

from pydantic import BaseModel


class ProdutoEmAlerta(BaseModel):
    id: int
    nome: str
    quantidade_em_estoque: int


class AlertaEstoqueBaixo(BaseModel):
    verificado_em: datetime
    limite: int
    produtos: list[ProdutoEmAlerta]


class VerificacaoEnfileirada(BaseModel):
    job_id: str | None
    enfileirado: bool
