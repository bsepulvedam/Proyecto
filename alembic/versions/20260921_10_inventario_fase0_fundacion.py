"""Fase 0 de Inventario: empresa Mas Vial, tabla Bodega, trazabilidad de origen
y tipo de movimiento TRANSFERENCIA_ENTRE_EMPRESAS.

Revision ID: 20260921_10
Revises: 20260902_09
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260921_10"
down_revision: str | None = "20260902_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BODEGA_PRINCIPAL_CODIGO = "PRINCIPAL"
BODEGA_PRINCIPAL_NOMBRE = "Bodega Principal"

TIPOS_MOVIMIENTO_ANTERIOR = (
    "RECEPCION",
    "DESPACHO",
    "DEVOLUCION",
    "AJUSTE_INICIAL",
    "AJUSTE_POSITIVO",
    "AJUSTE_NEGATIVO",
)
TIPOS_MOVIMIENTO_NUEVO = TIPOS_MOVIMIENTO_ANTERIOR + ("TRANSFERENCIA_ENTRE_EMPRESAS",)


def _check_tipo_sql(tipos: tuple[str, ...]) -> str:
    valores = ",".join(f"'{tipo}'" for tipo in tipos)
    return f"tipo IN ({valores})"


def upgrade() -> None:
    connection = op.get_bind()

    existe_masv = connection.scalar(sa.text("SELECT 1 FROM empresas WHERE codigo = 'MASV'"))
    if not existe_masv:
        empresas = sa.table(
            "empresas",
            sa.column("codigo", sa.String),
            sa.column("nombre", sa.String),
            sa.column("activo", sa.Boolean),
        )
        op.bulk_insert(empresas, [{"codigo": "MASV", "nombre": "Mas Vial", "activo": True}])

    op.create_table(
        "bodegas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text()),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_bodegas_empresa_codigo"),
    )
    op.create_index("ix_bodegas_empresa_id", "bodegas", ["empresa_id"])

    # Una bodega "PRINCIPAL" por cada empresa activa (Boliklor, ALM, Mas Vial),
    # sin asumir IDs fijos: se resuelve por SELECT sobre la tabla empresas ya poblada.
    connection.execute(
        sa.text(
            "INSERT INTO bodegas (empresa_id, codigo, nombre, activo) "
            "SELECT id, CAST(:codigo AS VARCHAR(50)), CAST(:nombre AS VARCHAR(200)), true FROM empresas "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM bodegas WHERE bodegas.empresa_id = empresas.id "
            "AND bodegas.codigo = CAST(:codigo AS VARCHAR(50))"
            ")"
        ),
        {"codigo": BODEGA_PRINCIPAL_CODIGO, "nombre": BODEGA_PRINCIPAL_NOMBRE},
    )

    op.add_column("movimientos_inventario", sa.Column("bodega_id", sa.Integer(), nullable=True))
    op.add_column(
        "movimientos_inventario",
        sa.Column("origen", sa.String(length=30), nullable=False, server_default="ERP_WEB"),
    )
    op.add_column(
        "movimientos_inventario", sa.Column("actor_referencia", sa.String(length=200), nullable=True)
    )

    op.create_foreign_key(
        "fk_movimientos_inventario_bodega_id",
        "movimientos_inventario",
        "bodegas",
        ["bodega_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_movimientos_inventario_bodega_id", "movimientos_inventario", ["bodega_id"])

    op.create_check_constraint(
        "ck_movimientos_inventario_origen",
        "movimientos_inventario",
        "origen IN ('ERP_WEB','BOT_TELEGRAM')",
    )

    op.drop_constraint("ck_movimientos_inventario_tipo", "movimientos_inventario", type_="check")
    op.create_check_constraint(
        "ck_movimientos_inventario_tipo",
        "movimientos_inventario",
        _check_tipo_sql(TIPOS_MOVIMIENTO_NUEVO),
    )


def downgrade() -> None:
    connection = op.get_bind()

    tipo_incompatible = connection.scalar(
        sa.text("SELECT count(*) FROM movimientos_inventario WHERE tipo = 'TRANSFERENCIA_ENTRE_EMPRESAS'")
    )
    if tipo_incompatible:
        raise RuntimeError(
            "No es seguro bajar 20260921_10: existen movimientos TRANSFERENCIA_ENTRE_EMPRESAS "
            "que no caben en el CHECK constraint de tipo anterior."
        )

    trazabilidad_incompatible = connection.scalar(
        sa.text(
            "SELECT count(*) FROM movimientos_inventario "
            "WHERE origen <> 'ERP_WEB' OR actor_referencia IS NOT NULL OR bodega_id IS NOT NULL"
        )
    )
    if trazabilidad_incompatible:
        raise RuntimeError(
            "No es seguro bajar 20260921_10: hay movimientos con origen/actor_referencia/bodega_id "
            "ya poblados; esos datos se perderían al eliminar las columnas."
        )

    bodegas_extra = connection.scalar(
        sa.text("SELECT count(*) FROM bodegas WHERE codigo <> :codigo"),
        {"codigo": BODEGA_PRINCIPAL_CODIGO},
    )
    if bodegas_extra:
        raise RuntimeError(
            "No es seguro bajar 20260921_10: existen bodegas adicionales a las 'PRINCIPAL' "
            "sembradas por esta migración."
        )

    masv_en_uso = connection.scalar(
        sa.text(
            "SELECT count(*) FROM empresas e WHERE e.codigo = 'MASV' AND ("
            "EXISTS (SELECT 1 FROM productos p WHERE p.empresa_id = e.id) OR "
            "EXISTS (SELECT 1 FROM movimientos_inventario m WHERE m.empresa_id = e.id)"
            ")"
        )
    )
    if masv_en_uso:
        raise RuntimeError(
            "No es seguro bajar 20260921_10: la empresa MASV ya tiene productos o movimientos asociados."
        )

    op.drop_constraint("ck_movimientos_inventario_tipo", "movimientos_inventario", type_="check")
    op.create_check_constraint(
        "ck_movimientos_inventario_tipo",
        "movimientos_inventario",
        _check_tipo_sql(TIPOS_MOVIMIENTO_ANTERIOR),
    )

    op.drop_constraint("ck_movimientos_inventario_origen", "movimientos_inventario", type_="check")
    op.drop_index("ix_movimientos_inventario_bodega_id", table_name="movimientos_inventario")
    op.drop_constraint("fk_movimientos_inventario_bodega_id", "movimientos_inventario", type_="foreignkey")
    op.drop_column("movimientos_inventario", "actor_referencia")
    op.drop_column("movimientos_inventario", "origen")
    op.drop_column("movimientos_inventario", "bodega_id")

    op.drop_index("ix_bodegas_empresa_id", table_name="bodegas")
    op.drop_table("bodegas")

    op.execute(sa.text("DELETE FROM empresas WHERE codigo = 'MASV'"))
