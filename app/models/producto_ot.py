from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProductoOT(Base):
    __tablename__ = "productos_ot"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_productos_ot_cantidad_positiva"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes_trabajo.id", ondelete="CASCADE"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    unidad: Mapped[str] = mapped_column(String(100), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    medida_especifica: Mapped[str | None] = mapped_column(String(200))

    orden: Mapped["OrdenTrabajo"] = relationship(back_populates="productos")


from app.models.orden_trabajo import OrdenTrabajo  # noqa: E402,F401
