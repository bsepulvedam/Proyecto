from datetime import date
from decimal import Decimal
from typing import Literal

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


class LineaDespachoCreate(BaseModel):
    producto_id: int
    cantidad_presentaciones: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class DespachoCreate(BaseModel):
    empresa_id: int
    fecha: date
    guia_despacho: str | None = None
    entregado_a: str | None = None
    comuna: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaDespachoCreate] = Field(min_length=1)


class LineaDevolucionCreate(BaseModel):
    producto_id: int
    cantidad_presentaciones: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class DevolucionCreate(BaseModel):
    empresa_id: int
    fecha: date
    guia_despacho: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    lineas: list[LineaDevolucionCreate] = Field(min_length=1)


class LineaAjusteCreate(BaseModel):
    producto_id: int
    cantidad_presentaciones: Decimal = Field(gt=0)
    observacion_linea: str | None = None


class AjusteCreate(BaseModel):
    empresa_id: int
    fecha: date
    tipo_ajuste: Literal["AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"]
    motivo: str = Field(min_length=1)
    referencia: str | None = None
    lineas: list[LineaAjusteCreate] = Field(min_length=1)
