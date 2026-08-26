from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"
    __table_args__ = (
        UniqueConstraint("numero_ot", name="uq_ordenes_trabajo_numero_ot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_ot: Mapped[int] = mapped_column(Integer, nullable=False)
    comuna: Mapped[str] = mapped_column(String(120), nullable=False)
    empresa_origen: Mapped[str | None] = mapped_column(String(200))
    recibe: Mapped[str | None] = mapped_column(String(200))
    fecha_pedido: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_entrega: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_finalizacion: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str | None] = mapped_column(String(100))
    cliente: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(50))
    correo: Mapped[str | None] = mapped_column(String(320))
    recibido_por: Mapped[str | None] = mapped_column(String(200))
    lugar_trabajo: Mapped[str | None] = mapped_column(String(300))
    estado_cliente: Mapped[str | None] = mapped_column(String(100))
    referencia_pedido: Mapped[str | None] = mapped_column(String(200))
    responsable_boliklor: Mapped[str | None] = mapped_column(String(200))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    productos: Mapped[list["ProductoOT"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan"
    )


from app.models.producto_ot import ProductoOT  # noqa: E402,F401
