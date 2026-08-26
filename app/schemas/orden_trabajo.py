from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductoOT(BaseModel):
    descripcion: str
    unidad: str
    cantidad: Decimal = Field(gt=0)
    medida_especifica: str | None = None


class OrdenTrabajoCreate(BaseModel):
    comuna: str
    empresa_origen: str | None = None
    recibe: str | None = None
    fecha_pedido: date
    fecha_entrega: date
    fecha_finalizacion: date | None = None
    estado: str | None = None
    cliente: str | None = None
    telefono: str | None = None
    correo: str | None = None
    recibido_por: str | None = None
    lugar_trabajo: str | None = None
    estado_cliente: str | None = None
    referencia_pedido: str | None = None
    responsable_boliklor: str | None = None
    productos: list[ProductoOT] = Field(min_length=1)
    observaciones: str | None = None


class OrdenTrabajoResponse(BaseModel):
    ok: bool
    numero_ot: int
    mensaje: str


class ProductoOTRead(ProductoOT):
    model_config = ConfigDict(from_attributes=True)

    id: int


class OrdenTrabajoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_ot: int
    comuna: str
    fecha_pedido: date
    fecha_entrega: date
    estado: str | None
    productos: list[ProductoOTRead]
