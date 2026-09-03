"""Persistencia de supervisión administrativa de Asistencia 4B-3B.

Revision ID: 20260902_09
Revises: 20260901_08
"""
from collections.abc import Sequence
from datetime import date

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_09"
down_revision: str | None = "20260901_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INITIAL_GLOBAL_RATE_EFFECTIVE_FROM = date(2026, 9, 1)
INITIAL_GLOBAL_RATE_CLP = 30_000


def _precheck_incident_states(connection) -> None:
    unexpected = connection.execute(
        sa.text(
            "SELECT estado, count(*) FROM incidencias_asistencia "
            "WHERE estado NOT IN ('PENDIENTE','RESUELTA','DESCARTADA') "
            "GROUP BY estado ORDER BY estado"
        )
    ).all()
    if unexpected:
        raise RuntimeError(
            "20260902_09 abortada: existen estados de incidencia no reconocidos."
        )
    incoherent = connection.scalar(
        sa.text(
            "SELECT count(*) FROM incidencias_asistencia WHERE "
            "(estado = 'PENDIENTE' AND "
            "(resuelto_por_id IS NOT NULL OR resuelto_at IS NOT NULL)) OR "
            "(estado IN ('RESUELTA','DESCARTADA') AND "
            "(resuelto_por_id IS NULL OR resuelto_at IS NULL))"
        )
    )
    if incoherent:
        raise RuntimeError(
            "20260902_09 abortada: hay incidencias históricas con resolución incoherente."
        )


def upgrade() -> None:
    connection = op.get_bind()
    _precheck_incident_states(connection)

    op.create_unique_constraint(
        "uq_marcajes_asistencia_identidad_sesion_tipo",
        "marcajes_asistencia",
        ["id", "sesion_id", "tipo"],
    )

    op.create_table(
        "intervenciones_salida_administrativa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sesion_id",
            sa.Integer(),
            sa.ForeignKey("sesiones_trabajo.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("marcaje_salida_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo_marcaje_salida",
            sa.String(20),
            server_default="SALIDA",
            nullable=False,
        ),
        sa.Column(
            "tipo_intervencion",
            sa.String(30),
            server_default="COMPLETAR_SALIDA",
            nullable=False,
        ),
        sa.Column("hora_laboral_introducida", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "salida_original_ausente",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "creado_por_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("sesion_id", name="uq_intervenciones_salida_sesion"),
        sa.UniqueConstraint(
            "marcaje_salida_id", name="uq_intervenciones_salida_marcaje"
        ),
        sa.ForeignKeyConstraint(
            ["marcaje_salida_id", "sesion_id", "tipo_marcaje_salida"],
            [
                "marcajes_asistencia.id",
                "marcajes_asistencia.sesion_id",
                "marcajes_asistencia.tipo",
            ],
            name="fk_intervenciones_salida_marcaje_sesion_tipo",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "tipo_intervencion = 'COMPLETAR_SALIDA'",
            name="ck_intervenciones_salida_tipo",
        ),
        sa.CheckConstraint(
            "tipo_marcaje_salida = 'SALIDA'",
            name="ck_intervenciones_salida_tipo_marcaje",
        ),
        sa.CheckConstraint(
            "salida_original_ausente",
            name="ck_intervenciones_salida_original_ausente",
        ),
        sa.CheckConstraint(
            "length(trim(motivo)) > 0",
            name="ck_intervenciones_salida_motivo",
        ),
    )
    op.create_index(
        "ix_intervenciones_salida_actor",
        "intervenciones_salida_administrativa",
        ["creado_por_id"],
    )
    op.create_index(
        "ix_intervenciones_salida_created_at",
        "intervenciones_salida_administrativa",
        ["created_at"],
    )

    op.create_table(
        "tarifas_provisionales_asistencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trabajador_id",
            sa.Integer(),
            sa.ForeignKey("trabajadores.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("valor_clp", sa.Numeric(12, 0), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column(
            "creado_por_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "valor_clp > 0", name="ck_tarifas_asistencia_valor_positivo"
        ),
        sa.CheckConstraint(
            "origen IN ('SISTEMA','ADMIN')",
            name="ck_tarifas_asistencia_origen",
        ),
        sa.CheckConstraint(
            "(origen = 'SISTEMA' AND creado_por_id IS NULL) OR "
            "(origen = 'ADMIN' AND creado_por_id IS NOT NULL)",
            name="ck_tarifas_asistencia_actor",
        ),
    )
    op.create_index(
        "uq_tarifas_asistencia_global_fecha",
        "tarifas_provisionales_asistencia",
        ["vigente_desde"],
        unique=True,
        postgresql_where=sa.text("trabajador_id IS NULL"),
    )
    op.create_index(
        "uq_tarifas_asistencia_trabajador_fecha",
        "tarifas_provisionales_asistencia",
        ["trabajador_id", "vigente_desde"],
        unique=True,
        postgresql_where=sa.text("trabajador_id IS NOT NULL"),
    )
    op.create_index(
        "ix_tarifas_asistencia_resolucion",
        "tarifas_provisionales_asistencia",
        ["trabajador_id", "vigente_desde"],
    )
    connection.execute(
        sa.text(
            "INSERT INTO tarifas_provisionales_asistencia "
            "(trabajador_id, valor_clp, vigente_desde, origen, creado_por_id) "
            "VALUES (NULL, :amount, :effective_from, 'SISTEMA', NULL)"
        ),
        {
            "amount": INITIAL_GLOBAL_RATE_CLP,
            "effective_from": INITIAL_GLOBAL_RATE_EFFECTIVE_FROM,
        },
    )

    op.drop_constraint(
        "ck_incidencias_asistencia_estado",
        "incidencias_asistencia",
        type_="check",
    )
    connection.execute(
        sa.text(
            "UPDATE incidencias_asistencia SET estado = CASE estado "
            "WHEN 'RESUELTA' THEN 'APROBADA' "
            "WHEN 'DESCARTADA' THEN 'RECHAZADA' ELSE estado END"
        )
    )
    op.create_check_constraint(
        "ck_incidencias_asistencia_estado",
        "incidencias_asistencia",
        "estado IN ('PENDIENTE','APROBADA','RECHAZADA')",
    )
    op.create_check_constraint(
        "ck_incidencias_asistencia_resolucion",
        "incidencias_asistencia",
        "(estado = 'PENDIENTE' AND resuelto_por_id IS NULL AND resuelto_at IS NULL) OR "
        "(estado IN ('APROBADA','RECHAZADA') AND resuelto_por_id IS NOT NULL AND resuelto_at IS NOT NULL)",
    )


def downgrade() -> None:
    connection = op.get_bind()
    interventions = connection.scalar(
        sa.text("SELECT count(*) FROM intervenciones_salida_administrativa")
    )
    if interventions:
        raise RuntimeError(
            "No es seguro bajar 20260902_09 después de completar salidas administrativas."
        )
    rates = connection.execute(
        sa.text(
            "SELECT trabajador_id, valor_clp, vigente_desde, origen, creado_por_id "
            "FROM tarifas_provisionales_asistencia"
        )
    ).all()
    expected_seed = (
        None,
        INITIAL_GLOBAL_RATE_CLP,
        INITIAL_GLOBAL_RATE_EFFECTIVE_FROM,
        "SISTEMA",
        None,
    )
    if len(rates) != 1 or tuple(rates[0]) != expected_seed:
        raise RuntimeError(
            "No es seguro bajar 20260902_09 después de versionar tarifas."
        )

    op.drop_constraint(
        "ck_incidencias_asistencia_resolucion",
        "incidencias_asistencia",
        type_="check",
    )
    op.drop_constraint(
        "ck_incidencias_asistencia_estado",
        "incidencias_asistencia",
        type_="check",
    )
    connection.execute(
        sa.text(
            "UPDATE incidencias_asistencia SET estado = CASE estado "
            "WHEN 'APROBADA' THEN 'RESUELTA' "
            "WHEN 'RECHAZADA' THEN 'DESCARTADA' ELSE estado END"
        )
    )
    op.create_check_constraint(
        "ck_incidencias_asistencia_estado",
        "incidencias_asistencia",
        "estado IN ('PENDIENTE','RESUELTA','DESCARTADA')",
    )

    op.drop_index(
        "ix_tarifas_asistencia_resolucion",
        table_name="tarifas_provisionales_asistencia",
    )
    op.drop_index(
        "uq_tarifas_asistencia_trabajador_fecha",
        table_name="tarifas_provisionales_asistencia",
    )
    op.drop_index(
        "uq_tarifas_asistencia_global_fecha",
        table_name="tarifas_provisionales_asistencia",
    )
    op.drop_table("tarifas_provisionales_asistencia")
    op.drop_index(
        "ix_intervenciones_salida_created_at",
        table_name="intervenciones_salida_administrativa",
    )
    op.drop_index(
        "ix_intervenciones_salida_actor",
        table_name="intervenciones_salida_administrativa",
    )
    op.drop_table("intervenciones_salida_administrativa")
    op.drop_constraint(
        "uq_marcajes_asistencia_identidad_sesion_tipo",
        "marcajes_asistencia",
        type_="unique",
    )
