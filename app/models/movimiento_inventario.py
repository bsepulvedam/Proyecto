from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        UniqueConstraint("numero_documento", name="uq_movimientos_inventario_numero_documento"),
        CheckConstraint("tipo IN ('RECEPCION','DESPACHO','DEVOLUCION','AJUSTE_INICIAL','AJUSTE_POSITIVO','AJUSTE_NEGATIVO')", name="ck_movimientos_inventario_tipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    numero_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    guia_despacho: Mapped[str | None] = mapped_column(String(120))
    referencia: Mapped[str | None] = mapped_column(String(200))
    entregado_a: Mapped[str | None] = mapped_column(String(200))
    comuna: Mapped[str | None] = mapped_column(String(120))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="movimientos_inventario")
    detalles: Mapped[list["DetalleMovimientoInventario"]] = relationship(back_populates="movimiento", cascade="all, delete-orphan", passive_deletes=True)

    @property
    def valor_total(self) -> Decimal:
        return sum((linea.valor_total or Decimal("0") for linea in self.detalles), Decimal("0"))


class DetalleMovimientoInventario(Base):
    __tablename__ = "detalle_movimientos_inventario"
    __table_args__ = (
        CheckConstraint("cantidad_presentaciones > 0", name="ck_detalle_movimientos_cantidad_positiva"),
        CheckConstraint("factor_conversion_snapshot > 0", name="ck_detalle_movimientos_factor_positivo"),
        Index("ix_detalle_movimientos_movimiento_id", "movimiento_id"),
        Index("ix_detalle_movimientos_producto_id", "producto_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("movimientos_inventario.id", ondelete="CASCADE"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    cantidad_presentaciones: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unidad_presentacion_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)
    factor_conversion_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unidad_contenido_snapshot: Mapped[str | None] = mapped_column(String(30))
    unidad_costo_snapshot: Mapped[str | None] = mapped_column(String(30))
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    costo_presentacion: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    observacion_linea: Mapped[str | None] = mapped_column(Text)

    movimiento: Mapped[MovimientoInventario] = relationship(back_populates="detalles")
    producto: Mapped["Producto"] = relationship(back_populates="detalles_movimiento")


from app.models.empresa import Empresa  # noqa: E402,F401
from app.models.producto import Producto  # noqa: E402,F401
