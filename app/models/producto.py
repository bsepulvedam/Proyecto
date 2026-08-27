from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Producto(Base):
    """Catálogo maestro separado del snapshot histórico ``ProductoOT``.

    La empresa determina la propiedad futura del stock: BOLIKLOR y ALM nunca lo
    comparten. ``unidad_stock`` representa la presentación física,
    ``unidad_contenido`` su contenido y ``unidad_costo`` la base de costo. El
    factor expresa equivalencias como 1 SACO = 25 KG. La política futura de
    movimientos respetará ``permite_decimales`` (SACO y KIT son enteros) y el
    costo se calculará mediante promedio ponderado; ninguna de esas operaciones
    se implementa en esta fase.
    """

    __tablename__ = "productos"
    __table_args__ = (
        UniqueConstraint("sku", name="uq_productos_sku"),
        CheckConstraint(
            "factor_conversion > 0", name="ck_productos_factor_conversion_positivo"
        ),
        CheckConstraint("stock_minimo >= 0", name="ck_productos_stock_minimo_no_negativo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre: Mapped[str] = mapped_column(String(250), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    unidad_stock_id: Mapped[int] = mapped_column(
        ForeignKey("unidades_medida.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unidad_contenido_id: Mapped[int | None] = mapped_column(
        ForeignKey("unidades_medida.id", ondelete="RESTRICT"), index=True
    )
    factor_conversion: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("1"), server_default="1"
    )
    unidad_costo_id: Mapped[int] = mapped_column(
        ForeignKey("unidades_medida.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stock_minimo: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    tipo: Mapped[str | None] = mapped_column(String(120))
    familia: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="productos")
    unidad_stock: Mapped["UnidadMedida"] = relationship(
        back_populates="productos_stock", foreign_keys=[unidad_stock_id]
    )
    unidad_contenido: Mapped["UnidadMedida | None"] = relationship(
        back_populates="productos_contenido", foreign_keys=[unidad_contenido_id]
    )
    unidad_costo: Mapped["UnidadMedida"] = relationship(
        back_populates="productos_costo", foreign_keys=[unidad_costo_id]
    )
    detalles_movimiento: Mapped[list["DetalleMovimientoInventario"]] = relationship(back_populates="producto")


from app.models.empresa import Empresa  # noqa: E402,F401
from app.models.unidad_medida import UnidadMedida  # noqa: E402,F401
from app.models.movimiento_inventario import DetalleMovimientoInventario  # noqa: E402,F401
