"""Fase 7: motor transaccional de inventario.

Revision ID: 20260827_03
Revises: 20260826_02
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_03"
down_revision: str | None = "20260826_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("movimiento_inventario_seq", start=1)))
    op.create_table(
        "movimientos_inventario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("numero_documento", sa.String(30), nullable=False),
        sa.Column("guia_despacho", sa.String(120)),
        sa.Column("referencia", sa.String(200)),
        sa.Column("entregado_a", sa.String(200)),
        sa.Column("comuna", sa.String(120)),
        sa.Column("observaciones", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo IN ('RECEPCION','DESPACHO','DEVOLUCION','AJUSTE_INICIAL','AJUSTE_POSITIVO','AJUSTE_NEGATIVO')", name="ck_movimientos_inventario_tipo"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("numero_documento", name="uq_movimientos_inventario_numero_documento"),
    )
    op.create_index("ix_movimientos_inventario_tipo", "movimientos_inventario", ["tipo"])
    op.create_index("ix_movimientos_inventario_empresa_id", "movimientos_inventario", ["empresa_id"])
    op.create_index("ix_movimientos_inventario_fecha", "movimientos_inventario", ["fecha"])
    op.create_table(
        "detalle_movimientos_inventario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movimiento_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("cantidad_presentaciones", sa.Numeric(14, 3), nullable=False),
        sa.Column("unidad_presentacion_snapshot", sa.String(30), nullable=False),
        sa.Column("factor_conversion_snapshot", sa.Numeric(14, 4), nullable=False),
        sa.Column("unidad_contenido_snapshot", sa.String(30)),
        sa.Column("unidad_costo_snapshot", sa.String(30)),
        sa.Column("costo_unitario", sa.Numeric(18, 4)),
        sa.Column("costo_presentacion", sa.Numeric(18, 4)),
        sa.Column("valor_total", sa.Numeric(18, 2)),
        sa.Column("observacion_linea", sa.Text()),
        sa.CheckConstraint("cantidad_presentaciones > 0", name="ck_detalle_movimientos_cantidad_positiva"),
        sa.CheckConstraint("factor_conversion_snapshot > 0", name="ck_detalle_movimientos_factor_positivo"),
        sa.ForeignKeyConstraint(["movimiento_id"], ["movimientos_inventario.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_detalle_movimientos_movimiento_id", "detalle_movimientos_inventario", ["movimiento_id"])
    op.create_index("ix_detalle_movimientos_producto_id", "detalle_movimientos_inventario", ["producto_id"])


def downgrade() -> None:
    op.drop_index("ix_detalle_movimientos_producto_id", table_name="detalle_movimientos_inventario")
    op.drop_index("ix_detalle_movimientos_movimiento_id", table_name="detalle_movimientos_inventario")
    op.drop_table("detalle_movimientos_inventario")
    op.drop_index("ix_movimientos_inventario_fecha", table_name="movimientos_inventario")
    op.drop_index("ix_movimientos_inventario_empresa_id", table_name="movimientos_inventario")
    op.drop_index("ix_movimientos_inventario_tipo", table_name="movimientos_inventario")
    op.drop_table("movimientos_inventario")
    op.execute(sa.schema.DropSequence(sa.Sequence("movimiento_inventario_seq")))
