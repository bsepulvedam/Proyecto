"""Sesiones, marcajes y evidencia geolocalizada de asistencia.

Revision ID: 20260831_07
Revises: 20260830_06
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_07"
down_revision: str | None = "20260830_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sesiones_trabajo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trabajador_id", sa.Integer(), nullable=False),
        sa.Column("turno_id", sa.Integer(), nullable=False),
        sa.Column("fecha_operacional", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(20), server_default="ABIERTA", nullable=False),
        sa.Column("cerrado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["trabajador_id"], ["trabajadores.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["turno_id"], ["turnos.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("estado IN ('ABIERTA','CERRADA')", name="ck_sesiones_trabajo_estado"),
        sa.CheckConstraint(
            "(estado = 'ABIERTA' AND cerrado_at IS NULL) OR (estado = 'CERRADA' AND cerrado_at IS NOT NULL)",
            name="ck_sesiones_trabajo_cierre",
        ),
    )
    op.create_index("ix_sesiones_trabajo_turno_id", "sesiones_trabajo", ["turno_id"])
    op.create_index("ix_sesiones_trabajo_fecha_operacional", "sesiones_trabajo", ["fecha_operacional"])
    op.create_index("ix_sesiones_trabajo_estado", "sesiones_trabajo", ["estado"])
    op.create_index(
        "ix_sesiones_trabajo_trabajador_fecha",
        "sesiones_trabajo",
        ["trabajador_id", "fecha_operacional"],
    )
    op.create_index(
        "uq_sesiones_trabajo_abierta_por_trabajador",
        "sesiones_trabajo",
        ["trabajador_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'ABIERTA'"),
    )

    op.create_table(
        "marcajes_asistencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sesion_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("ocurrido_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones_trabajo.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("sesion_id", "tipo", name="uq_marcajes_asistencia_sesion_tipo"),
        sa.CheckConstraint("tipo IN ('ENTRADA','SALIDA')", name="ck_marcajes_asistencia_tipo"),
    )
    for column in ("sesion_id", "tipo", "ocurrido_at"):
        op.create_index(f"ix_marcajes_asistencia_{column}", "marcajes_asistencia", [column])

    op.create_table(
        "evidencias_gps_marcaje",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marcaje_id", sa.Integer(), nullable=False),
        sa.Column("latitud", sa.Numeric(12, 9), nullable=False),
        sa.Column("longitud", sa.Numeric(13, 9), nullable=False),
        sa.Column("precision_m", sa.Numeric(8, 2), nullable=False),
        sa.Column("capturada_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["marcaje_id"], ["marcajes_asistencia.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("marcaje_id", name="uq_evidencias_gps_marcaje_marcaje"),
        sa.CheckConstraint("latitud BETWEEN -90 AND 90", name="ck_evidencias_gps_latitud"),
        sa.CheckConstraint("longitud BETWEEN -180 AND 180", name="ck_evidencias_gps_longitud"),
        sa.CheckConstraint("NOT (latitud = 0 AND longitud = 0)", name="ck_evidencias_gps_no_cero_cero"),
        sa.CheckConstraint("precision_m > 0", name="ck_evidencias_gps_precision"),
    )

    op.create_table(
        "evaluaciones_geograficas_marcaje",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marcaje_id", sa.Integer(), nullable=False),
        sa.Column("lugar_detectado_id", sa.Integer(), nullable=True),
        sa.Column("distancia_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("radio_m_aplicado", sa.Numeric(8, 2), nullable=True),
        sa.Column("estado_geocerca", sa.String(30), nullable=False),
        sa.Column("estado_precision", sa.String(30), nullable=False),
        sa.Column("max_precision_m_aplicada", sa.Numeric(8, 2), nullable=False),
        sa.Column("regla_version", sa.String(30), nullable=False),
        sa.Column("evaluada_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["marcaje_id"], ["marcajes_asistencia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lugar_detectado_id"], ["lugares_trabajo.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("marcaje_id", name="uq_evaluaciones_geograficas_marcaje"),
        sa.CheckConstraint(
            "estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO','SIN_ZONA_CONFIGURADA')",
            name="ck_evaluaciones_geograficas_estado",
        ),
        sa.CheckConstraint("estado_precision IN ('ACEPTABLE','BAJA_PRECISION')", name="ck_evaluaciones_geograficas_precision"),
        sa.CheckConstraint("distancia_m IS NULL OR distancia_m >= 0", name="ck_evaluaciones_geograficas_distancia"),
        sa.CheckConstraint("radio_m_aplicado IS NULL OR radio_m_aplicado > 0", name="ck_evaluaciones_geograficas_radio"),
        sa.CheckConstraint("max_precision_m_aplicada > 0", name="ck_evaluaciones_geograficas_max_precision"),
        sa.CheckConstraint(
            "(lugar_detectado_id IS NULL AND estado_geocerca = 'SIN_ZONA_CONFIGURADA' AND distancia_m IS NULL AND radio_m_aplicado IS NULL) OR "
            "(lugar_detectado_id IS NOT NULL AND estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NOT NULL)",
            name="ck_evaluaciones_geograficas_zona_coherente",
        ),
    )
    for column in ("lugar_detectado_id", "estado_geocerca", "estado_precision"):
        op.create_index(
            f"ix_evaluaciones_geograficas_marcaje_{column}",
            "evaluaciones_geograficas_marcaje",
            [column],
        )

    op.create_table(
        "incidencias_asistencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marcaje_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("estado", sa.String(20), server_default="PENDIENTE", nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("resuelto_por_id", sa.Integer(), nullable=True),
        sa.Column("resuelto_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comentario_resolucion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["marcaje_id"], ["marcajes_asistencia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resuelto_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("marcaje_id", "tipo", name="uq_incidencias_asistencia_marcaje_tipo"),
        sa.CheckConstraint("estado IN ('PENDIENTE','RESUELTA','DESCARTADA')", name="ck_incidencias_asistencia_estado"),
    )
    for column in ("marcaje_id", "tipo", "estado"):
        op.create_index(f"ix_incidencias_asistencia_{column}", "incidencias_asistencia", [column])

    op.create_table(
        "correcciones_marcaje",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("marcaje_id", sa.Integer(), nullable=False),
        sa.Column("campo", sa.String(80), nullable=False),
        sa.Column("valor_original", sa.Text(), nullable=False),
        sa.Column("valor_corregido", sa.Text(), nullable=False),
        sa.Column("corregido_por_id", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["marcaje_id"], ["marcajes_asistencia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["corregido_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("valor_original <> valor_corregido", name="ck_correcciones_marcaje_valores_distintos"),
    )
    op.create_index("ix_correcciones_marcaje_marcaje_id", "correcciones_marcaje", ["marcaje_id"])
    op.create_index("ix_correcciones_marcaje_corregido_por_id", "correcciones_marcaje", ["corregido_por_id"])


def downgrade() -> None:
    op.drop_table("correcciones_marcaje")
    op.drop_table("incidencias_asistencia")
    op.drop_table("evaluaciones_geograficas_marcaje")
    op.drop_table("evidencias_gps_marcaje")
    op.drop_table("marcajes_asistencia")
    op.drop_table("sesiones_trabajo")
