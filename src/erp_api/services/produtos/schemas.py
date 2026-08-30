from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProdutoBase(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    preco: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    quantidade_em_estoque: int = Field(ge=0, default=0)

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_numerico(cls, value: str) -> str:
        nome = value.strip()
        if not nome or nome.replace(".", "", 1).replace(",", "", 1).isdigit():
            msg = "nome não pode ser vazio ou apenas numérico"
            raise ValueError(msg)
        return nome


class ProdutoCreate(ProdutoBase): ...


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    preco: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quantidade_em_estoque: int | None = Field(default=None, ge=0)

    nome_nao_pode_ser_numerico = field_validator("nome")(
        ProdutoBase.nome_nao_pode_ser_numerico.__func__  # type: ignore[attr-defined]
    )


class ProdutoResponse(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_criacao: datetime
    data_atualizacao: datetime


class ProdutoFilters(BaseModel):
    nome: str | None = None
    preco_min: Decimal | None = Field(default=None, ge=0)
    preco_max: Decimal | None = Field(default=None, ge=0)
    estoque_abaixo_de: int | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class ProdutosPage(BaseModel):
    items: list[ProdutoResponse]
    total: int
    page: int
    size: int
