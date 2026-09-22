"""API del bot: tabla de claves Idempotency-Key ya procesadas.

Revision ID: 20260922_11
Revises: 20260921_10
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260922_11"
down_revision: str | None = "20260921_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claves_idempotencia_bot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clave", sa.String(length=200), nullable=False),
        sa.Column("movimiento_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["movimiento_id"], ["movimientos_inventario.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("clave", name="uq_claves_idempotencia_bot_clave"),
    )
    op.create_index(
        "ix_claves_idempotencia_bot_movimiento_id",
        "claves_idempotencia_bot",
        ["movimiento_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()

    claves_existentes = connection.scalar(
        sa.text("SELECT count(*) FROM claves_idempotencia_bot")
    )
    if claves_existentes:
        raise RuntimeError(
            "No es seguro bajar 20260922_11: existen claves Idempotency-Key ya "
            "registradas; bajar la migración las eliminaría y un reintento de "
            "N8N podría duplicar un movimiento ya procesado."
        )

    op.drop_index("ix_claves_idempotencia_bot_movimiento_id", table_name="claves_idempotencia_bot")
    op.drop_table("claves_idempotencia_bot")
