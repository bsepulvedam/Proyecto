"""Geocercas RADIO/COMUNA y catálogo inicial de zonas reales.

Revision ID: 20260901_08
Revises: 20260831_07
"""
from collections.abc import Sequence
from decimal import Decimal

from alembic import op
import sqlalchemy as sa

revision: str = "20260901_08"
down_revision: str | None = "20260831_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COMMUNE_ZONES = (
    ("Colina", "13301", Decimal("-33.2023"), Decimal("-70.6749")),
    ("Paine", "13404", Decimal("-33.8080"), Decimal("-70.7411")),
    ("Cerrillos", "13102", Decimal("-33.4833"), Decimal("-70.7000")),
    ("Maip\u00fa", "13119", Decimal("-33.5111"), Decimal("-70.7581")),
    ("La Florida", "13110", Decimal("-33.5227"), Decimal("-70.5483")),
    ("Lo Prado", "13117", Decimal("-33.4442"), Decimal("-70.7225")),
    ("Cerro Navia", "13103", Decimal("-33.4225"), Decimal("-70.7300")),
    ("Mostazal", "06110", Decimal("-33.9833"), Decimal("-70.7000")),
    ("San Carlos", "16301", Decimal("-36.4248"), Decimal("-71.9581")),
    ("Huechuraba", "13107", Decimal("-33.3742"), Decimal("-70.6367")),
    ("Pedro Aguirre Cerda", "13121", Decimal("-33.4931"), Decimal("-70.6761")),
    ("Los \u00c1ngeles", "08301", Decimal("-37.4697"), Decimal("-72.3537")),
    ("La Pintana", "13112", Decimal("-33.5910025641024"), Decimal("-70.65163587224612")),
)


def upgrade() -> None:
    op.alter_column("lugares_trabajo", "latitud", existing_type=sa.Numeric(9, 6), type_=sa.Numeric(18, 15), existing_nullable=True)
    op.alter_column("lugares_trabajo", "longitud", existing_type=sa.Numeric(10, 6), type_=sa.Numeric(18, 15), existing_nullable=True)
    op.add_column("lugares_trabajo", sa.Column("tipo_geocerca", sa.String(10), nullable=True))
    op.add_column("lugares_trabajo", sa.Column("codigo_comuna", sa.String(10), nullable=True))
    op.add_column("lugares_trabajo", sa.Column("prioridad_geocerca", sa.Integer(), server_default="100", nullable=False))
    op.create_index("ix_lugares_trabajo_tipo_geocerca", "lugares_trabajo", ["tipo_geocerca"])
    op.create_index("ix_lugares_trabajo_codigo_comuna", "lugares_trabajo", ["codigo_comuna"])

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE lugares_trabajo SET tipo_geocerca = 'RADIO' "
            "WHERE latitud IS NOT NULL AND longitud IS NOT NULL AND radio_metros IS NOT NULL"
        )
    )
    for name, code, latitude, longitude in COMMUNE_ZONES:
        connection.execute(
            sa.text(
                "UPDATE lugares_trabajo SET comuna=:commune_name, tipo_geocerca='COMUNA', codigo_comuna=:code, "
                "latitud=:latitude, longitud=:longitude, radio_metros=NULL, prioridad_geocerca=100 "
                "WHERE nombre=:match_name"
            ),
            {
                "commune_name": name,
                "match_name": name,
                "code": code,
                "latitude": latitude,
                "longitude": longitude,
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO lugares_trabajo "
                "(nombre, tipo, comuna, tipo_geocerca, codigo_comuna, latitud, longitud, radio_metros, prioridad_geocerca, activo) "
                "SELECT :insert_name, 'TERRENO', :insert_commune, 'COMUNA', :code, :latitude, :longitude, NULL, 100, true "
                "WHERE NOT EXISTS (SELECT 1 FROM lugares_trabajo WHERE nombre=:lookup_name)"
            ),
            {
                "insert_name": name,
                "insert_commune": name,
                "lookup_name": name,
                "code": code,
                "latitude": latitude,
                "longitude": longitude,
            },
        )

    op.create_check_constraint("ck_lugares_tipo_geocerca", "lugares_trabajo", "tipo_geocerca IS NULL OR tipo_geocerca IN ('RADIO','COMUNA')")
    op.create_check_constraint("ck_lugares_prioridad_geocerca", "lugares_trabajo", "prioridad_geocerca > 0")
    op.create_check_constraint(
        "ck_lugares_geocerca_radio_configurada",
        "lugares_trabajo",
        "tipo_geocerca <> 'RADIO' OR (latitud IS NOT NULL AND longitud IS NOT NULL AND radio_metros IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_lugares_geocerca_comuna_configurada",
        "lugares_trabajo",
        "tipo_geocerca <> 'COMUNA' OR (codigo_comuna IS NOT NULL AND latitud IS NOT NULL AND longitud IS NOT NULL AND radio_metros IS NULL)",
    )
    op.create_index(
        "uq_lugares_geocerca_comuna_activa",
        "lugares_trabajo",
        ["codigo_comuna"],
        unique=True,
        postgresql_where=sa.text("activo AND tipo_geocerca = 'COMUNA'"),
    )

    op.add_column("evaluaciones_geograficas_marcaje", sa.Column("tolerancia_m_aplicada", sa.Numeric(8, 2), nullable=True))
    op.add_column("evaluaciones_geograficas_marcaje", sa.Column("tipo_geocerca_aplicado", sa.String(10), nullable=True))
    op.add_column("evaluaciones_geograficas_marcaje", sa.Column("geometria_version", sa.String(80), nullable=True))
    connection.execute(
        sa.text(
            "UPDATE evaluaciones_geograficas_marcaje SET tipo_geocerca_aplicado='RADIO' "
            "WHERE lugar_detectado_id IS NOT NULL"
        )
    )
    op.drop_constraint("ck_evaluaciones_geograficas_estado", "evaluaciones_geograficas_marcaje", type_="check")
    op.drop_constraint("ck_evaluaciones_geograficas_zona_coherente", "evaluaciones_geograficas_marcaje", type_="check")
    op.create_check_constraint(
        "ck_evaluaciones_geograficas_estado",
        "evaluaciones_geograficas_marcaje",
        "estado_geocerca IN ('DENTRO_RANGO','DENTRO_TOLERANCIA','FUERA_RANGO','SIN_ZONA_CONFIGURADA')",
    )
    op.create_check_constraint(
        "ck_evaluaciones_geograficas_tolerancia",
        "evaluaciones_geograficas_marcaje",
        "tolerancia_m_aplicada IS NULL OR tolerancia_m_aplicada > 0",
    )
    op.create_check_constraint(
        "ck_evaluaciones_geograficas_zona_coherente",
        "evaluaciones_geograficas_marcaje",
        "(lugar_detectado_id IS NULL AND estado_geocerca = 'SIN_ZONA_CONFIGURADA' AND distancia_m IS NULL AND radio_m_aplicado IS NULL AND tolerancia_m_aplicada IS NULL AND tipo_geocerca_aplicado IS NULL AND geometria_version IS NULL) OR "
        "(lugar_detectado_id IS NOT NULL AND tipo_geocerca_aplicado = 'RADIO' AND estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NOT NULL AND tolerancia_m_aplicada IS NULL AND geometria_version IS NULL) OR "
        "(lugar_detectado_id IS NOT NULL AND tipo_geocerca_aplicado = 'COMUNA' AND estado_geocerca IN ('DENTRO_RANGO','DENTRO_TOLERANCIA','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NULL AND tolerancia_m_aplicada IS NOT NULL AND geometria_version IS NOT NULL)",
    )


def downgrade() -> None:
    connection = op.get_bind()
    incompatible = connection.scalar(
        sa.text(
            "SELECT count(*) FROM evaluaciones_geograficas_marcaje "
            "WHERE tipo_geocerca_aplicado='COMUNA' OR estado_geocerca='DENTRO_TOLERANCIA'"
        )
    )
    if incompatible:
        raise RuntimeError("No es seguro bajar 20260901_08 después de registrar evaluaciones COMUNA.")

    op.drop_constraint("ck_evaluaciones_geograficas_zona_coherente", "evaluaciones_geograficas_marcaje", type_="check")
    op.drop_constraint("ck_evaluaciones_geograficas_tolerancia", "evaluaciones_geograficas_marcaje", type_="check")
    op.drop_constraint("ck_evaluaciones_geograficas_estado", "evaluaciones_geograficas_marcaje", type_="check")
    op.create_check_constraint(
        "ck_evaluaciones_geograficas_estado",
        "evaluaciones_geograficas_marcaje",
        "estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO','SIN_ZONA_CONFIGURADA')",
    )
    op.create_check_constraint(
        "ck_evaluaciones_geograficas_zona_coherente",
        "evaluaciones_geograficas_marcaje",
        "(lugar_detectado_id IS NULL AND estado_geocerca = 'SIN_ZONA_CONFIGURADA' AND distancia_m IS NULL AND radio_m_aplicado IS NULL) OR "
        "(lugar_detectado_id IS NOT NULL AND estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NOT NULL)",
    )
    op.drop_column("evaluaciones_geograficas_marcaje", "geometria_version")
    op.drop_column("evaluaciones_geograficas_marcaje", "tipo_geocerca_aplicado")
    op.drop_column("evaluaciones_geograficas_marcaje", "tolerancia_m_aplicada")

    op.drop_index("uq_lugares_geocerca_comuna_activa", table_name="lugares_trabajo")
    op.drop_constraint("ck_lugares_geocerca_comuna_configurada", "lugares_trabajo", type_="check")
    op.drop_constraint("ck_lugares_geocerca_radio_configurada", "lugares_trabajo", type_="check")
    op.drop_constraint("ck_lugares_prioridad_geocerca", "lugares_trabajo", type_="check")
    op.drop_constraint("ck_lugares_tipo_geocerca", "lugares_trabajo", type_="check")
    op.drop_index("ix_lugares_trabajo_codigo_comuna", table_name="lugares_trabajo")
    op.drop_index("ix_lugares_trabajo_tipo_geocerca", table_name="lugares_trabajo")
    op.drop_column("lugares_trabajo", "prioridad_geocerca")
    op.drop_column("lugares_trabajo", "codigo_comuna")
    op.drop_column("lugares_trabajo", "tipo_geocerca")
    op.alter_column("lugares_trabajo", "longitud", existing_type=sa.Numeric(18, 15), type_=sa.Numeric(10, 6), existing_nullable=True)
    op.alter_column("lugares_trabajo", "latitud", existing_type=sa.Numeric(18, 15), type_=sa.Numeric(9, 6), existing_nullable=True)
