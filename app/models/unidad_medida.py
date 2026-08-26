from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UnidadMedida(Base):
    __tablename__ = "unidades_medida"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_unidades_medida_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    permite_decimales: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    productos_stock: Mapped[list["Producto"]] = relationship(
        back_populates="unidad_stock", foreign_keys="Producto.unidad_stock_id"
    )
    productos_contenido: Mapped[list["Producto"]] = relationship(
        back_populates="unidad_contenido", foreign_keys="Producto.unidad_contenido_id"
    )
    productos_costo: Mapped[list["Producto"]] = relationship(
        back_populates="unidad_costo", foreign_keys="Producto.unidad_costo_id"
    )


from app.models.producto import Producto  # noqa: E402,F401
