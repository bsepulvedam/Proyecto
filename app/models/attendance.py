from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LugarTrabajo(Base):
    __tablename__ = "lugares_trabajo"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_lugares_trabajo_nombre"),
        CheckConstraint("tipo IN ('BASE','TALLER','TERRENO')", name="ck_lugares_trabajo_tipo"),
        CheckConstraint("tipo_geocerca IS NULL OR tipo_geocerca IN ('RADIO','COMUNA')", name="ck_lugares_tipo_geocerca"),
        CheckConstraint("latitud IS NULL OR latitud BETWEEN -90 AND 90", name="ck_lugares_latitud"),
        CheckConstraint("longitud IS NULL OR longitud BETWEEN -180 AND 180", name="ck_lugares_longitud"),
        CheckConstraint("radio_metros IS NULL OR radio_metros > 0", name="ck_lugares_radio"),
        CheckConstraint("prioridad_geocerca > 0", name="ck_lugares_prioridad_geocerca"),
        CheckConstraint(
            "tipo_geocerca <> 'RADIO' OR (latitud IS NOT NULL AND longitud IS NOT NULL AND radio_metros IS NOT NULL)",
            name="ck_lugares_geocerca_radio_configurada",
        ),
        CheckConstraint(
            "tipo_geocerca <> 'COMUNA' OR (codigo_comuna IS NOT NULL AND latitud IS NOT NULL AND longitud IS NOT NULL AND radio_metros IS NULL)",
            name="ck_lugares_geocerca_comuna_configurada",
        ),
        Index(
            "uq_lugares_geocerca_comuna_activa",
            "codigo_comuna",
            unique=True,
            postgresql_where=text("activo AND tipo_geocerca = 'COMUNA'"),
            sqlite_where=text("activo = 1 AND tipo_geocerca = 'COMUNA'"),
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    comuna: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(300))
    tipo_geocerca: Mapped[str | None] = mapped_column(String(10), index=True)
    codigo_comuna: Mapped[str | None] = mapped_column(String(10), index=True)
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(18, 15))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(18, 15))
    radio_metros: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    prioridad_geocerca: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
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


class SesionTrabajo(Base):
    __tablename__ = "sesiones_trabajo"
    __table_args__ = (
        CheckConstraint("estado IN ('ABIERTA','CERRADA')", name="ck_sesiones_trabajo_estado"),
        CheckConstraint(
            "(estado = 'ABIERTA' AND cerrado_at IS NULL) OR (estado = 'CERRADA' AND cerrado_at IS NOT NULL)",
            name="ck_sesiones_trabajo_cierre",
        ),
        Index(
            "uq_sesiones_trabajo_abierta_por_trabajador",
            "trabajador_id",
            unique=True,
            postgresql_where=text("estado = 'ABIERTA'"),
            sqlite_where=text("estado = 'ABIERTA'"),
        ),
        Index("ix_sesiones_trabajo_trabajador_fecha", "trabajador_id", "fecha_operacional"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajador_id: Mapped[int] = mapped_column(ForeignKey("trabajadores.id", ondelete="RESTRICT"), nullable=False)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id", ondelete="RESTRICT"), nullable=False, index=True)
    fecha_operacional: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="ABIERTA", server_default="ABIERTA", index=True)
    cerrado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    trabajador: Mapped["Trabajador"] = relationship(back_populates="sesiones_trabajo")
    turno: Mapped[Turno] = relationship()
    marcajes: Mapped[list["MarcajeAsistencia"]] = relationship(back_populates="sesion", order_by="MarcajeAsistencia.ocurrido_at")
    intervencion_salida: Mapped["IntervencionSalidaAdministrativa | None"] = relationship(
        back_populates="sesion",
        uselist=False,
    )


class MarcajeAsistencia(Base):
    __tablename__ = "marcajes_asistencia"
    __table_args__ = (
        UniqueConstraint("sesion_id", "tipo", name="uq_marcajes_asistencia_sesion_tipo"),
        UniqueConstraint(
            "id",
            "sesion_id",
            "tipo",
            name="uq_marcajes_asistencia_identidad_sesion_tipo",
        ),
        CheckConstraint("tipo IN ('ENTRADA','SALIDA')", name="ck_marcajes_asistencia_tipo"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesiones_trabajo.id", ondelete="RESTRICT"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ocurrido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sesion: Mapped[SesionTrabajo] = relationship(back_populates="marcajes")
    evidencia_gps: Mapped["EvidenciaGPSMarcaje"] = relationship(back_populates="marcaje", uselist=False)
    evaluacion_geografica: Mapped["EvaluacionGeograficaMarcaje"] = relationship(back_populates="marcaje", uselist=False)
    incidencias: Mapped[list["IncidenciaAsistencia"]] = relationship(back_populates="marcaje")
    correcciones: Mapped[list["CorreccionMarcaje"]] = relationship(back_populates="marcaje")
    intervencion_salida: Mapped["IntervencionSalidaAdministrativa | None"] = relationship(
        back_populates="marcaje_salida",
        uselist=False,
        viewonly=True,
    )


class EvidenciaGPSMarcaje(Base):
    __tablename__ = "evidencias_gps_marcaje"
    __table_args__ = (
        UniqueConstraint("marcaje_id", name="uq_evidencias_gps_marcaje_marcaje"),
        CheckConstraint("latitud BETWEEN -90 AND 90", name="ck_evidencias_gps_latitud"),
        CheckConstraint("longitud BETWEEN -180 AND 180", name="ck_evidencias_gps_longitud"),
        CheckConstraint("NOT (latitud = 0 AND longitud = 0)", name="ck_evidencias_gps_no_cero_cero"),
        CheckConstraint("precision_m > 0", name="ck_evidencias_gps_precision"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marcaje_id: Mapped[int] = mapped_column(ForeignKey("marcajes_asistencia.id", ondelete="RESTRICT"), nullable=False)
    latitud: Mapped[Decimal] = mapped_column(Numeric(12, 9), nullable=False)
    longitud: Mapped[Decimal] = mapped_column(Numeric(13, 9), nullable=False)
    precision_m: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    capturada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    marcaje: Mapped[MarcajeAsistencia] = relationship(back_populates="evidencia_gps")


class EvaluacionGeograficaMarcaje(Base):
    __tablename__ = "evaluaciones_geograficas_marcaje"
    __table_args__ = (
        UniqueConstraint("marcaje_id", name="uq_evaluaciones_geograficas_marcaje"),
        CheckConstraint(
            "estado_geocerca IN ('DENTRO_RANGO','DENTRO_TOLERANCIA','FUERA_RANGO','SIN_ZONA_CONFIGURADA')",
            name="ck_evaluaciones_geograficas_estado",
        ),
        CheckConstraint("estado_precision IN ('ACEPTABLE','BAJA_PRECISION')", name="ck_evaluaciones_geograficas_precision"),
        CheckConstraint("distancia_m IS NULL OR distancia_m >= 0", name="ck_evaluaciones_geograficas_distancia"),
        CheckConstraint("radio_m_aplicado IS NULL OR radio_m_aplicado > 0", name="ck_evaluaciones_geograficas_radio"),
        CheckConstraint("tolerancia_m_aplicada IS NULL OR tolerancia_m_aplicada > 0", name="ck_evaluaciones_geograficas_tolerancia"),
        CheckConstraint("max_precision_m_aplicada > 0", name="ck_evaluaciones_geograficas_max_precision"),
        CheckConstraint(
            "(lugar_detectado_id IS NULL AND estado_geocerca = 'SIN_ZONA_CONFIGURADA' AND distancia_m IS NULL AND radio_m_aplicado IS NULL AND tolerancia_m_aplicada IS NULL AND tipo_geocerca_aplicado IS NULL AND geometria_version IS NULL) OR "
            "(lugar_detectado_id IS NOT NULL AND tipo_geocerca_aplicado = 'RADIO' AND estado_geocerca IN ('DENTRO_RANGO','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NOT NULL AND tolerancia_m_aplicada IS NULL AND geometria_version IS NULL) OR "
            "(lugar_detectado_id IS NOT NULL AND tipo_geocerca_aplicado = 'COMUNA' AND estado_geocerca IN ('DENTRO_RANGO','DENTRO_TOLERANCIA','FUERA_RANGO') AND distancia_m IS NOT NULL AND radio_m_aplicado IS NULL AND tolerancia_m_aplicada IS NOT NULL AND geometria_version IS NOT NULL)",
            name="ck_evaluaciones_geograficas_zona_coherente",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marcaje_id: Mapped[int] = mapped_column(ForeignKey("marcajes_asistencia.id", ondelete="RESTRICT"), nullable=False)
    lugar_detectado_id: Mapped[int | None] = mapped_column(ForeignKey("lugares_trabajo.id", ondelete="RESTRICT"), index=True)
    distancia_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    radio_m_aplicado: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    tolerancia_m_aplicada: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    tipo_geocerca_aplicado: Mapped[str | None] = mapped_column(String(10))
    geometria_version: Mapped[str | None] = mapped_column(String(80))
    estado_geocerca: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    estado_precision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    max_precision_m_aplicada: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    regla_version: Mapped[str] = mapped_column(String(30), nullable=False)
    evaluada_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    marcaje: Mapped[MarcajeAsistencia] = relationship(back_populates="evaluacion_geografica")
    lugar_detectado: Mapped[LugarTrabajo | None] = relationship()


class IncidenciaAsistencia(Base):
    __tablename__ = "incidencias_asistencia"
    __table_args__ = (
        UniqueConstraint("marcaje_id", "tipo", name="uq_incidencias_asistencia_marcaje_tipo"),
        CheckConstraint("estado IN ('PENDIENTE','APROBADA','RECHAZADA')", name="ck_incidencias_asistencia_estado"),
        CheckConstraint(
            "(estado = 'PENDIENTE' AND resuelto_por_id IS NULL AND resuelto_at IS NULL) OR "
            "(estado IN ('APROBADA','RECHAZADA') AND resuelto_por_id IS NOT NULL AND resuelto_at IS NOT NULL)",
            name="ck_incidencias_asistencia_resolucion",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marcaje_id: Mapped[int] = mapped_column(ForeignKey("marcajes_asistencia.id", ondelete="RESTRICT"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDIENTE", server_default="PENDIENTE", index=True)
    detalle: Mapped[str | None] = mapped_column(Text)
    resuelto_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    resuelto_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comentario_resolucion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    marcaje: Mapped[MarcajeAsistencia] = relationship(back_populates="incidencias")
    resuelto_por: Mapped["Usuario | None"] = relationship(foreign_keys=[resuelto_por_id])


class IntervencionSalidaAdministrativa(Base):
    __tablename__ = "intervenciones_salida_administrativa"
    __table_args__ = (
        UniqueConstraint("sesion_id", name="uq_intervenciones_salida_sesion"),
        UniqueConstraint("marcaje_salida_id", name="uq_intervenciones_salida_marcaje"),
        ForeignKeyConstraint(
            ["marcaje_salida_id", "sesion_id", "tipo_marcaje_salida"],
            [
                "marcajes_asistencia.id",
                "marcajes_asistencia.sesion_id",
                "marcajes_asistencia.tipo",
            ],
            name="fk_intervenciones_salida_marcaje_sesion_tipo",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "tipo_intervencion = 'COMPLETAR_SALIDA'",
            name="ck_intervenciones_salida_tipo",
        ),
        CheckConstraint(
            "tipo_marcaje_salida = 'SALIDA'",
            name="ck_intervenciones_salida_tipo_marcaje",
        ),
        CheckConstraint(
            "salida_original_ausente",
            name="ck_intervenciones_salida_original_ausente",
        ),
        CheckConstraint(
            "length(trim(motivo)) > 0",
            name="ck_intervenciones_salida_motivo",
        ),
        Index("ix_intervenciones_salida_actor", "creado_por_id"),
        Index("ix_intervenciones_salida_created_at", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sesion_id: Mapped[int] = mapped_column(
        ForeignKey("sesiones_trabajo.id", ondelete="RESTRICT"), nullable=False
    )
    marcaje_salida_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_marcaje_salida: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SALIDA", server_default="SALIDA"
    )
    tipo_intervencion: Mapped[str] = mapped_column(
        String(30), nullable=False, default="COMPLETAR_SALIDA", server_default="COMPLETAR_SALIDA"
    )
    hora_laboral_introducida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    salida_original_ausente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    creado_por_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sesion: Mapped[SesionTrabajo] = relationship(back_populates="intervencion_salida")
    marcaje_salida: Mapped[MarcajeAsistencia] = relationship(
        back_populates="intervencion_salida",
        viewonly=True,
    )
    creado_por: Mapped["Usuario"] = relationship(foreign_keys=[creado_por_id])


class TarifaProvisionalAsistencia(Base):
    __tablename__ = "tarifas_provisionales_asistencia"
    __table_args__ = (
        CheckConstraint("valor_clp > 0", name="ck_tarifas_asistencia_valor_positivo"),
        CheckConstraint(
            "origen IN ('SISTEMA','ADMIN')",
            name="ck_tarifas_asistencia_origen",
        ),
        CheckConstraint(
            "(origen = 'SISTEMA' AND creado_por_id IS NULL) OR "
            "(origen = 'ADMIN' AND creado_por_id IS NOT NULL)",
            name="ck_tarifas_asistencia_actor",
        ),
        Index(
            "uq_tarifas_asistencia_global_fecha",
            "vigente_desde",
            unique=True,
            postgresql_where=text("trabajador_id IS NULL"),
            sqlite_where=text("trabajador_id IS NULL"),
        ),
        Index(
            "uq_tarifas_asistencia_trabajador_fecha",
            "trabajador_id",
            "vigente_desde",
            unique=True,
            postgresql_where=text("trabajador_id IS NOT NULL"),
            sqlite_where=text("trabajador_id IS NOT NULL"),
        ),
        Index(
            "ix_tarifas_asistencia_resolucion",
            "trabajador_id",
            "vigente_desde",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trabajador_id: Mapped[int | None] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="RESTRICT")
    )
    valor_clp: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    trabajador: Mapped["Trabajador | None"] = relationship(foreign_keys=[trabajador_id])
    creado_por: Mapped["Usuario | None"] = relationship(foreign_keys=[creado_por_id])


class CorreccionMarcaje(Base):
    __tablename__ = "correcciones_marcaje"
    __table_args__ = (CheckConstraint("valor_original <> valor_corregido", name="ck_correcciones_marcaje_valores_distintos"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marcaje_id: Mapped[int] = mapped_column(ForeignKey("marcajes_asistencia.id", ondelete="RESTRICT"), nullable=False, index=True)
    campo: Mapped[str] = mapped_column(String(80), nullable=False)
    valor_original: Mapped[str] = mapped_column(Text, nullable=False)
    valor_corregido: Mapped[str] = mapped_column(Text, nullable=False)
    corregido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False, index=True)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    marcaje: Mapped[MarcajeAsistencia] = relationship(back_populates="correcciones")
    corregido_por: Mapped["Usuario"] = relationship(foreign_keys=[corregido_por_id])


from app.models.identity import Trabajador, Usuario  # noqa: E402,F401
