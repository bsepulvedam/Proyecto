from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Bodega(Base):
    """Bodega física dentro de una empresa (jerarquía Empresa -> Bodega -> Stock).

    Fase 0 siembra una única bodega ``PRINCIPAL`` por empresa (Boliklor, ALM,
    Mas Vial); el modelo ya soporta múltiples bodegas por empresa sin requerir
    una migración estructural futura.
    """

    __tablename__ = "bodegas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_bodegas_empresa_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="bodegas")
    movimientos_inventario: Mapped[list["MovimientoInventario"]] = relationship(
        back_populates="bodega"
    )


from app.models.empresa import Empresa  # noqa: E402,F401
from app.models.movimiento_inventario import MovimientoInventario  # noqa: E402,F401
