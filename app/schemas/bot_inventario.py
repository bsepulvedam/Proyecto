"""Schemas exclusivos de la integración con el bot de Telegram.

Deliberadamente separados de ``app.schemas.movimiento_inventario``: la web
sigue usando ``RecepcionCreate`` sin cambios, y el origen/actor de un
movimiento no es algo que un formulario web deba poder declarar por sí mismo
-- lo decide el llamador de ``create_receipt`` (la web o el router del bot),
nunca el payload que ya valida la web.
"""

from typing import Literal

from pydantic import BaseModel, Field


class OrigenMovimientoBot(BaseModel):
    """Metadata de trazabilidad de quién/qué originó un movimiento.

    ``origen`` está limitado a los dos valores que acepta el CHECK constraint
    de ``movimientos_inventario`` (migración ``20260921_10``): un valor fuera
    de ese conjunto falla aquí, en el límite, en vez de reventar como error de
    integridad en la base de datos. ``actor_referencia`` respeta el mismo
    ``max_length`` que la columna (``VARCHAR(200)``).

    Sin instancia (``None`` en ``create_receipt``) equivale a
    ``OrigenMovimientoBot()``: ``ERP_WEB`` sin actor, el comportamiento que ya
    tenía la web antes de que existiera este schema.
    """

    origen: Literal["ERP_WEB", "BOT_TELEGRAM"] = "ERP_WEB"
    actor_referencia: str | None = Field(default=None, max_length=200)
