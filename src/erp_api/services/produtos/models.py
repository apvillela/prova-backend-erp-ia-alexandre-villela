from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from erp_api.database import Base


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_produtos_preco_nao_negativo"),
        CheckConstraint("quantidade_em_estoque >= 0", name="ck_produtos_quantidade_nao_negativa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantidade_em_estoque: Mapped[int] = mapped_column(default=0)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
