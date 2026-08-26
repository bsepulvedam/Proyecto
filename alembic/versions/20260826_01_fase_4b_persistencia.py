"""Fase 4B: persistencia de ordenes de trabajo.

Revision ID: 20260826_01
Revises:
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("numero_ot_seq", start=13)))
    op.create_table(
        "ordenes_trabajo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero_ot", sa.Integer(), nullable=False),
        sa.Column("comuna", sa.String(length=120), nullable=False),
        sa.Column("empresa_origen", sa.String(length=200)),
        sa.Column("recibe", sa.String(length=200)),
        sa.Column("fecha_pedido", sa.Date(), nullable=False),
        sa.Column("fecha_entrega", sa.Date(), nullable=False),
        sa.Column("fecha_finalizacion", sa.Date()),
        sa.Column("estado", sa.String(length=100)),
        sa.Column("cliente", sa.String(length=200)),
        sa.Column("telefono", sa.String(length=50)),
        sa.Column("correo", sa.String(length=320)),
        sa.Column("recibido_por", sa.String(length=200)),
        sa.Column("lugar_trabajo", sa.String(length=300)),
        sa.Column("estado_cliente", sa.String(length=100)),
        sa.Column("referencia_pedido", sa.String(length=200)),
        sa.Column("responsable_boliklor", sa.String(length=200)),
        sa.Column("observaciones", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("numero_ot", name="uq_ordenes_trabajo_numero_ot"),
    )
    op.create_table(
        "productos_ot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("orden_id", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("unidad", sa.String(length=100), nullable=False),
        sa.Column("cantidad", sa.Numeric(12, 3), nullable=False),
        sa.Column("medida_especifica", sa.String(length=200)),
        sa.CheckConstraint("cantidad > 0", name="ck_productos_ot_cantidad_positiva"),
        sa.ForeignKeyConstraint(
            ["orden_id"], ["ordenes_trabajo.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_productos_ot_orden_id", "productos_ot", ["orden_id"])


def downgrade() -> None:
    op.drop_index("ix_productos_ot_orden_id", table_name="productos_ot")
    op.drop_table("productos_ot")
    op.drop_table("ordenes_trabajo")
    op.execute(sa.schema.DropSequence(sa.Sequence("numero_ot_seq")))
