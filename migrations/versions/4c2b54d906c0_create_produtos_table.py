"""create produtos table

Revision ID: 4c2b54d906c0
Revises:
Create Date: 2026-08-30 00:24:31.753044

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4c2b54d906c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "produtos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("preco", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantidade_em_estoque", sa.Integer(), nullable=False),
        sa.Column(
            "data_criacao",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "data_atualizacao",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("preco >= 0", name="ck_produtos_preco_nao_negativo"),
        sa.CheckConstraint(
            "quantidade_em_estoque >= 0", name="ck_produtos_quantidade_nao_negativa"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_produtos_nome"), "produtos", ["nome"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_produtos_nome"), table_name="produtos")
    op.drop_table("produtos")
