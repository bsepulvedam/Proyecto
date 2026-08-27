from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_empresas_codigo"),
        UniqueConstraint("nombre", name="uq_empresas_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    productos: Mapped[list["Producto"]] = relationship(back_populates="empresa")
    movimientos_inventario: Mapped[list["MovimientoInventario"]] = relationship(back_populates="empresa")


from app.models.producto import Producto  # noqa: E402,F401
from app.models.movimiento_inventario import MovimientoInventario  # noqa: E402,F401
