"""create movimentacoes_estoque table

Revision ID: 9f3d2b71c4e8
Revises: 4c2b54d906c0
Create Date: 2026-08-30 21:10:12.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9f3d2b71c4e8"
down_revision: Union[str, Sequence[str], None] = "4c2b54d906c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "movimentacoes_estoque",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("quantidade_resultante", sa.Integer(), nullable=False),
        sa.Column("usuario", sa.String(length=120), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_movimentacoes_estoque_produto_id"),
        "movimentacoes_estoque",
        ["produto_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_movimentacoes_estoque_produto_id"), table_name="movimentacoes_estoque")
    op.drop_table("movimentacoes_estoque")
