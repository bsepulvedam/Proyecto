from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EmpresaCreate(BaseModel):
    codigo: str
    nombre: str
    activo: bool = True


class EmpresaRead(EmpresaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class UnidadMedidaCreate(BaseModel):
    codigo: str
    nombre: str
    permite_decimales: bool = False
    activo: bool = True


class UnidadMedidaRead(UnidadMedidaCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProductoCreate(BaseModel):
    empresa_id: int
    sku: str
    nombre: str
    descripcion: str | None = None
    unidad_stock_id: int
    unidad_contenido_id: int | None = None
    factor_conversion: Decimal = Field(default=Decimal("1"), gt=0)
    unidad_costo_id: int
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    tipo: str | None = None
    familia: str | None = None
    activo: bool = True


class ProductoRead(ProductoCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
