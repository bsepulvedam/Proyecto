"""Lugares, asignaciones, turnos y justificaciones.

Revision ID: 20260830_06
Revises: 20260829_05
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20260830_06"
down_revision: str | None = "20260829_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("lugares_trabajo", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("nombre", sa.String(200), nullable=False), sa.Column("tipo", sa.String(20), nullable=False), sa.Column("comuna", sa.String(120)), sa.Column("direccion", sa.String(300)), sa.Column("latitud", sa.Numeric(9, 6)), sa.Column("longitud", sa.Numeric(10, 6)), sa.Column("radio_metros", sa.Numeric(8, 2)), sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("nombre", name="uq_lugares_trabajo_nombre"), sa.CheckConstraint("tipo IN ('BASE','TALLER','TERRENO')", name="ck_lugares_trabajo_tipo"), sa.CheckConstraint("latitud IS NULL OR latitud BETWEEN -90 AND 90", name="ck_lugares_latitud"), sa.CheckConstraint("longitud IS NULL OR longitud BETWEEN -180 AND 180", name="ck_lugares_longitud"), sa.CheckConstraint("radio_metros IS NULL OR radio_metros > 0", name="ck_lugares_radio"))
    op.create_index("ix_lugares_trabajo_tipo", "lugares_trabajo", ["tipo"]); op.create_index("ix_lugares_trabajo_activo", "lugares_trabajo", ["activo"])
    lugares = sa.table("lugares_trabajo", sa.column("nombre", sa.String), sa.column("tipo", sa.String), sa.column("comuna", sa.String), sa.column("activo", sa.Boolean))
    op.bulk_insert(lugares, [{"nombre": "Base Boliklor - La Pintana", "tipo": "BASE", "comuna": "La Pintana", "activo": True}, {"nombre": "Taller Boliklor - La Pintana", "tipo": "TALLER", "comuna": "La Pintana", "activo": True}] + [{"nombre": name, "tipo": "TERRENO", "comuna": name, "activo": True} for name in ("Colina", "Paine", "Cerrillos", "Maipú", "La Florida", "Lo Prado", "Cerro Navia", "Mostazal", "San Carlos", "Huechuraba", "Pedro Aguirre Cerda", "Los Ángeles")])
    op.create_table("turnos", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("codigo", sa.String(30), nullable=False), sa.Column("nombre", sa.String(100), nullable=False), sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("codigo", name="uq_turnos_codigo"))
    turnos = sa.table("turnos", sa.column("codigo", sa.String), sa.column("nombre", sa.String), sa.column("activo", sa.Boolean)); op.bulk_insert(turnos, [{"codigo": "DIURNO", "nombre": "Diurno", "activo": True}, {"codigo": "NOCTURNO", "nombre": "Nocturno", "activo": True}])
    op.create_table("asignaciones_trabajador_lugar", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("trabajador_id", sa.Integer(), nullable=False), sa.Column("lugar_id", sa.Integer(), nullable=False), sa.Column("desde", sa.DateTime(timezone=True), nullable=False), sa.Column("hasta", sa.DateTime(timezone=True)), sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False), sa.Column("creado_por_id", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["trabajador_id"], ["trabajadores.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["lugar_id"], ["lugares_trabajo.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["creado_por_id"], ["usuarios.id"], ondelete="RESTRICT"), sa.CheckConstraint("hasta IS NULL OR hasta > desde", name="ck_asignaciones_vigencia"))
    for column in ("trabajador_id", "lugar_id", "desde", "hasta", "activo"): op.create_index(f"ix_asignaciones_trabajador_lugar_{column}", "asignaciones_trabajador_lugar", [column])
    op.create_table("justificaciones_inasistencia", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("trabajador_id", sa.Integer(), nullable=False), sa.Column("fecha", sa.Date(), nullable=False), sa.Column("tipo", sa.String(40), nullable=False), sa.Column("observacion", sa.Text()), sa.Column("estado", sa.String(20), server_default="PENDIENTE", nullable=False), sa.Column("archivo_nombre_original", sa.String(255)), sa.Column("archivo_storage_key", sa.String(120), unique=True), sa.Column("archivo_mime", sa.String(100)), sa.Column("archivo_tamano", sa.Integer()), sa.Column("revisado_por_id", sa.Integer()), sa.Column("revisado_at", sa.DateTime(timezone=True)), sa.Column("comentario_revision", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["trabajador_id"], ["trabajadores.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["revisado_por_id"], ["usuarios.id"], ondelete="RESTRICT"), sa.CheckConstraint("tipo IN ('LICENCIA_MEDICA','TRAMITE','COORDINACION_JEFATURA','OTRO')", name="ck_justificaciones_tipo"), sa.CheckConstraint("estado IN ('PENDIENTE','APROBADA','RECHAZADA')", name="ck_justificaciones_estado"), sa.CheckConstraint("observacion IS NOT NULL OR archivo_storage_key IS NOT NULL", name="ck_justificaciones_evidencia"))
    for column in ("trabajador_id", "fecha", "tipo", "estado"): op.create_index(f"ix_justificaciones_inasistencia_{column}", "justificaciones_inasistencia", [column])


def downgrade() -> None:
    op.drop_table("justificaciones_inasistencia"); op.drop_table("asignaciones_trabajador_lugar"); op.drop_table("turnos"); op.drop_table("lugares_trabajo")
