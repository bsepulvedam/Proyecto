"""Fase 4: base estructural del inventario.

Revision ID: 20260826_02
Revises: 20260826_01
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260826_02"
down_revision: str | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("codigo", name="uq_empresas_codigo"),
        sa.UniqueConstraint("nombre", name="uq_empresas_nombre"),
    )
    op.create_table(
        "unidades_medida",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column(
            "permite_decimales", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("codigo", name="uq_unidades_medida_codigo"),
    )
    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("nombre", sa.String(length=250), nullable=False),
        sa.Column("descripcion", sa.Text()),
        sa.Column("unidad_stock_id", sa.Integer(), nullable=False),
        sa.Column("unidad_contenido_id", sa.Integer()),
        sa.Column(
            "factor_conversion",
            sa.Numeric(14, 4),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("unidad_costo_id", sa.Integer(), nullable=False),
        sa.Column(
            "stock_minimo",
            sa.Numeric(14, 3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=120)),
        sa.Column("familia", sa.String(length=120)),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "factor_conversion > 0", name="ck_productos_factor_conversion_positivo"
        ),
        sa.CheckConstraint(
            "stock_minimo >= 0", name="ck_productos_stock_minimo_no_negativo"
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"], ["empresas.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["unidad_stock_id"], ["unidades_medida.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["unidad_contenido_id"], ["unidades_medida.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["unidad_costo_id"], ["unidades_medida.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("sku", name="uq_productos_sku"),
    )
    op.create_index("ix_productos_empresa_id", "productos", ["empresa_id"])
    op.create_index("ix_productos_unidad_stock_id", "productos", ["unidad_stock_id"])
    op.create_index(
        "ix_productos_unidad_contenido_id", "productos", ["unidad_contenido_id"]
    )
    op.create_index("ix_productos_unidad_costo_id", "productos", ["unidad_costo_id"])

    empresas = sa.table(
        "empresas",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("activo", sa.Boolean),
    )
    op.bulk_insert(
        empresas,
        [
            {"codigo": "BOLIKLOR", "nombre": "BOLIKLOR", "activo": True},
            {"codigo": "ALM", "nombre": "ALM", "activo": True},
        ],
    )

    unidades = sa.table(
        "unidades_medida",
        sa.column("codigo", sa.String),
        sa.column("nombre", sa.String),
        sa.column("permite_decimales", sa.Boolean),
        sa.column("activo", sa.Boolean),
    )
    op.bulk_insert(
        unidades,
        [
            {"codigo": "UN", "nombre": "Unidad", "permite_decimales": False, "activo": True},
            {"codigo": "KG", "nombre": "Kilogramo", "permite_decimales": True, "activo": True},
            {"codigo": "SACO", "nombre": "Saco", "permite_decimales": False, "activo": True},
            {"codigo": "TINETA", "nombre": "Tineta", "permite_decimales": False, "activo": True},
            {"codigo": "CAJA", "nombre": "Caja", "permite_decimales": False, "activo": True},
            {"codigo": "KIT", "nombre": "Kit", "permite_decimales": False, "activo": True},
            {"codigo": "ROLLO", "nombre": "Rollo", "permite_decimales": False, "activo": True},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_productos_unidad_costo_id", table_name="productos")
    op.drop_index("ix_productos_unidad_contenido_id", table_name="productos")
    op.drop_index("ix_productos_unidad_stock_id", table_name="productos")
    op.drop_index("ix_productos_empresa_id", table_name="productos")
    op.drop_table("productos")
    op.drop_table("unidades_medida")
    op.drop_table("empresas")
