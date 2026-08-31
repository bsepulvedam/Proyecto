from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenciaGPSCreate(BaseModel):
    latitud: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"), max_digits=12, decimal_places=9)
    longitud: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"), max_digits=13, decimal_places=9)
    precision_m: Decimal = Field(gt=0, le=Decimal("999999.99"), max_digits=8, decimal_places=2)
    capturada_at: datetime | None = None

    @field_validator("capturada_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("capturada_at debe incluir zona horaria")
        return value

    @model_validator(mode="after")
    def reject_zero_coordinates(self) -> "EvidenciaGPSCreate":
        if self.latitud == 0 and self.longitud == 0:
            raise ValueError("Las coordenadas 0,0 no son evidencia GPS válida")
        return self
