"""Identidad, autenticación y roles comunes de la plataforma.

Revision ID: 20260828_04
Revises: 20260827_03
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260828_04"
down_revision: str | None = "20260827_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_roles_codigo"),
    )
    roles = sa.table("roles", sa.column("codigo", sa.String), sa.column("nombre", sa.String), sa.column("activo", sa.Boolean))
    op.bulk_insert(roles, [
        {"codigo": "ADMIN", "nombre": "Administrador", "activo": True},
        {"codigo": "JEFATURA", "nombre": "Jefatura", "activo": True},
        {"codigo": "TRABAJADOR", "nombre": "Trabajador", "activo": True},
    ])
    op.create_table("usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("ultimo_acceso_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_usuarios_username_normalizado", "usuarios", [sa.text("lower(username)")], unique=True)
    op.create_index("ix_usuarios_activo", "usuarios", ["activo"])
    op.create_table("usuarios_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rol_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("usuario_id", "rol_id", name="uq_usuarios_roles_usuario_rol"),
    )
    op.create_index("ix_usuarios_roles_usuario_id", "usuarios_roles", ["usuario_id"])
    op.create_index("ix_usuarios_roles_rol_id", "usuarios_roles", ["rol_id"])
    op.create_table("trabajadores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer()),
        sa.Column("empresa_id", sa.Integer()),
        sa.Column("codigo_interno", sa.String(80)),
        sa.Column("nombres", sa.String(160), nullable=False),
        sa.Column("apellidos", sa.String(160), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("usuario_id", name="uq_trabajadores_usuario_id"),
        sa.UniqueConstraint("codigo_interno", name="uq_trabajadores_codigo_interno"),
    )
    op.create_index("ix_trabajadores_usuario_id", "trabajadores", ["usuario_id"])
    op.create_index("ix_trabajadores_empresa_id", "trabajadores", ["empresa_id"])
    op.create_index("ix_trabajadores_activo", "trabajadores", ["activo"])
    op.create_table("sesiones_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_sesiones_usuario_token_hash"),
    )
    op.create_index("ix_sesiones_usuario_usuario_id", "sesiones_usuario", ["usuario_id"])
    op.create_index("ix_sesiones_usuario_expires_at", "sesiones_usuario", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sesiones_usuario_expires_at", table_name="sesiones_usuario")
    op.drop_index("ix_sesiones_usuario_usuario_id", table_name="sesiones_usuario")
    op.drop_table("sesiones_usuario")
    op.drop_index("ix_trabajadores_activo", table_name="trabajadores")
    op.drop_index("ix_trabajadores_empresa_id", table_name="trabajadores")
    op.drop_index("ix_trabajadores_usuario_id", table_name="trabajadores")
    op.drop_table("trabajadores")
    op.drop_index("ix_usuarios_roles_rol_id", table_name="usuarios_roles")
    op.drop_index("ix_usuarios_roles_usuario_id", table_name="usuarios_roles")
    op.drop_table("usuarios_roles")
    op.drop_index("ix_usuarios_activo", table_name="usuarios")
    op.drop_index("uq_usuarios_username_normalizado", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("roles")
