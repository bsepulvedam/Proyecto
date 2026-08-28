"""Cambio obligatorio de contraseña temporal.

Revision ID: 20260829_05
Revises: 20260828_04
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260829_05"
down_revision: str | None = "20260828_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("debe_cambiar_password", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_usuarios_debe_cambiar_password", "usuarios", ["debe_cambiar_password"])


def downgrade() -> None:
    op.drop_index("ix_usuarios_debe_cambiar_password", table_name="usuarios")
    op.drop_column("usuarios", "debe_cambiar_password")
