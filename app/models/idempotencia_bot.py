from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ClaveIdempotenciaBot(Base):
    """Claves ``Idempotency-Key`` ya procesadas por la API del bot.

    El número de documento que genera ``create_receipt`` (``MOV-%06d``) nunca
    se repite, así que no sirve como clave de idempotencia de un reintento de
    N8N; tampoco se reutilizan ``actor_referencia`` ni ``referencia`` para
    esto, que son campos de negocio de otro dueño. Esta tabla es
    exclusivamente la memoria de "qué Idempotency-Key ya se procesó y con qué
    movimiento resultó" (``BOLIKLOR_BOT_API_DESIGN.md`` §6).

    Sin código todavía que la lea o escriba -- eso llega con el endpoint
    ``POST /api/bot/inventario/recepciones`` (Fase 1, tarea 4). Esta tarea
    sólo deja el modelo y la migración listos.
    """

    __tablename__ = "claves_idempotencia_bot"
    __table_args__ = (
        UniqueConstraint("clave", name="uq_claves_idempotencia_bot_clave"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(200), nullable=False)
    movimiento_id: Mapped[int] = mapped_column(
        ForeignKey("movimientos_inventario.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    movimiento: Mapped["MovimientoInventario"] = relationship()


from app.models.movimiento_inventario import MovimientoInventario  # noqa: E402,F401
