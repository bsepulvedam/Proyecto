from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LineaRecepcionCreate(BaseModel):
    producto_id: int
    cantidad_presentaciones: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class RecepcionCreate(BaseModel):
    empresa_id: int
    fecha: date
    guia_despacho: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaRecepcionCreate] = Field(min_length=1)
