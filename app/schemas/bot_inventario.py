"""Schemas exclusivos de la integración con el bot de Telegram.

Deliberadamente separados de ``app.schemas.movimiento_inventario``: la web
sigue usando ``RecepcionCreate`` sin cambios, y el origen/actor de un
movimiento no es algo que un formulario web deba poder declarar por sí mismo
-- lo decide el llamador de ``create_receipt`` (la web o el router del bot),
nunca el payload que ya valida la web.
"""

from datetime import date
from decimal import Decimal
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


class LineaRecepcionBotCreate(BaseModel):
    """Línea de recepción tal como la conoce el bot: por SKU, no por producto_id."""

    sku: str = Field(min_length=1, max_length=100)
    cantidad_presentaciones: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class RecepcionBotCreate(BaseModel):
    """Payload de ``POST /api/bot/inventario/recepciones`` (§7 del diseño).

    ``empresa_codigo`` y ``sku`` en vez de ``empresa_id``/``producto_id``: el
    bot conoce productos y empresas por su código de negocio, no por id
    interno. El router los resuelve antes de delegar en ``create_receipt``.
    """

    empresa_codigo: str = Field(min_length=1, max_length=50)
    fecha: date
    guia_despacho: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaRecepcionBotCreate] = Field(min_length=1)
    solicitado_por: str = Field(min_length=1, max_length=200)


class LineaDespachoBotCreate(BaseModel):
    """Línea de despacho tal como la conoce el bot: por SKU, sin costo (el
    despacho no lleva costeo de salida, igual que el flujo web)."""

    sku: str = Field(min_length=1, max_length=100)
    cantidad_presentaciones: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class DespachoBotCreate(BaseModel):
    """Payload de ``POST /api/bot/inventario/despachos``. Mismo patrón que
    ``RecepcionBotCreate``: ``empresa_codigo``/``sku`` en vez de ids
    internos, resueltos por el router antes de llamar ``create_dispatch``."""

    empresa_codigo: str = Field(min_length=1, max_length=50)
    fecha: date
    guia_despacho: str | None = None
    entregado_a: str | None = None
    comuna: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaDespachoBotCreate] = Field(min_length=1)
    solicitado_por: str = Field(min_length=1, max_length=200)


class LineaDevolucionBotCreate(BaseModel):
    """Línea de devolución tal como la conoce el bot: por SKU, sin costo."""

    sku: str = Field(min_length=1, max_length=100)
    cantidad_presentaciones: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class DevolucionBotCreate(BaseModel):
    """Payload de ``POST /api/bot/inventario/devoluciones``. Mismo patrón que
    ``RecepcionBotCreate``, resuelto por el router antes de llamar
    ``create_return``."""

    empresa_codigo: str = Field(min_length=1, max_length=50)
    fecha: date
    guia_despacho: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaDevolucionBotCreate] = Field(min_length=1)
    solicitado_por: str = Field(min_length=1, max_length=200)
