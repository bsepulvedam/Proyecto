from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    ultimo_acceso_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("uq_usuarios_username_normalizado", func.lower(username), unique=True),)
    roles: Mapped[list["Rol"]] = relationship(secondary="usuarios_roles", back_populates="usuarios", lazy="selectin")
    trabajador: Mapped["Trabajador | None"] = relationship(back_populates="usuario", uselist=False)
    sesiones: Mapped[list["SesionUsuario"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")

    @property
    def role_codes(self) -> set[str]:
        return {role.codigo for role in self.roles}

    @property
    def primary_role(self) -> str:
        return next((code for code in ("ADMIN", "JEFATURA", "TRABAJADOR") if code in self.role_codes), "SIN ROL")


class Rol(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("codigo", name="uq_roles_codigo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    usuarios: Mapped[list[Usuario]] = relationship(secondary="usuarios_roles", back_populates="roles")


class UsuarioRol(Base):
    __tablename__ = "usuarios_roles"
    __table_args__ = (UniqueConstraint("usuario_id", "rol_id", name="uq_usuarios_roles_usuario_rol"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Trabajador(Base):
    __tablename__ = "trabajadores"
    __table_args__ = (UniqueConstraint("usuario_id", name="uq_trabajadores_usuario_id"), UniqueConstraint("codigo_interno", name="uq_trabajadores_codigo_interno"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), index=True)
    codigo_interno: Mapped[str | None] = mapped_column(String(80))
    nombres: Mapped[str] = mapped_column(String(160), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(160), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    usuario: Mapped[Usuario | None] = relationship(back_populates="trabajador")
    empresa: Mapped["Empresa | None"] = relationship(back_populates="trabajadores")
    asignaciones_lugar: Mapped[list["AsignacionTrabajadorLugar"]] = relationship(back_populates="trabajador")
    justificaciones: Mapped[list["JustificacionInasistencia"]] = relationship(back_populates="trabajador")


class SesionUsuario(Base):
    __tablename__ = "sesiones_usuario"
    __table_args__ = (UniqueConstraint("token_hash", name="uq_sesiones_usuario_token_hash"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    usuario: Mapped[Usuario] = relationship(back_populates="sesiones")


from app.models.empresa import Empresa  # noqa: E402,F401
from app.models.attendance import AsignacionTrabajadorLugar, JustificacionInasistencia  # noqa: E402,F401
