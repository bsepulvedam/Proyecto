from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LugarTrabajo(Base):
    __tablename__ = "lugares_trabajo"
    __table_args__ = (UniqueConstraint("nombre", name="uq_lugares_trabajo_nombre"), CheckConstraint("tipo IN ('BASE','TALLER','TERRENO')", name="ck_lugares_trabajo_tipo"), CheckConstraint("latitud IS NULL OR latitud BETWEEN -90 AND 90", name="ck_lugares_latitud"), CheckConstraint("longitud IS NULL OR longitud BETWEEN -180 AND 180", name="ck_lugares_longitud"), CheckConstraint("radio_metros IS NULL OR radio_metros > 0", name="ck_lugares_radio"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    comuna: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(300))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    radio_metros: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    asignaciones: Mapped[list["AsignacionTrabajadorLugar"]] = relationship(back_populates="lugar")


class AsignacionTrabajadorLugar(Base):
    __tablename__ = "asignaciones_trabajador_lugar"
    __table_args__ = (CheckConstraint("hasta IS NULL OR hasta > desde", name="ck_asignaciones_vigencia"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajador_id: Mapped[int] = mapped_column(ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False, index=True)
    lugar_id: Mapped[int] = mapped_column(ForeignKey("lugares_trabajo.id", ondelete="RESTRICT"), nullable=False, index=True)
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true", index=True)
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    trabajador: Mapped["Trabajador"] = relationship(back_populates="asignaciones_lugar")
    lugar: Mapped[LugarTrabajo] = relationship(back_populates="asignaciones")
    creado_por: Mapped["Usuario"] = relationship(foreign_keys=[creado_por_id])


class Turno(Base):
    __tablename__ = "turnos"
    __table_args__ = (UniqueConstraint("codigo", name="uq_turnos_codigo"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JustificacionInasistencia(Base):
    __tablename__ = "justificaciones_inasistencia"
    __table_args__ = (CheckConstraint("tipo IN ('LICENCIA_MEDICA','TRAMITE','COORDINACION_JEFATURA','OTRO')", name="ck_justificaciones_tipo"), CheckConstraint("estado IN ('PENDIENTE','APROBADA','RECHAZADA')", name="ck_justificaciones_estado"), CheckConstraint("observacion IS NOT NULL OR archivo_storage_key IS NOT NULL", name="ck_justificaciones_evidencia"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajador_id: Mapped[int] = mapped_column(ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    observacion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE", server_default="PENDIENTE", index=True)
    archivo_nombre_original: Mapped[str | None] = mapped_column(String(255))
    archivo_storage_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    archivo_mime: Mapped[str | None] = mapped_column(String(100))
    archivo_tamano: Mapped[int | None] = mapped_column(Integer)
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    revisado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comentario_revision: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    trabajador: Mapped["Trabajador"] = relationship(back_populates="justificaciones")
    revisado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[revisado_por_id])


from app.models.identity import Trabajador, Usuario  # noqa: E402,F401
