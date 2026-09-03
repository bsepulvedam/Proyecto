from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.time import app_timezone


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


class AttendanceMarkForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["ENTRADA", "SALIDA"]
    turno_id: int | None = Field(default=None, gt=0)
    latitud: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"), max_digits=12, decimal_places=9)
    longitud: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"), max_digits=13, decimal_places=9)
    precision_m: Decimal = Field(gt=0, le=Decimal("999999.99"), max_digits=8, decimal_places=2)
    capturada_at: datetime

    @field_validator("tipo", mode="before")
    @classmethod
    def normalize_mark_type(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_action_fields(self) -> "AttendanceMarkForm":
        if self.tipo == "ENTRADA" and self.turno_id is None:
            raise ValueError("La entrada requiere un turno")
        if self.tipo == "SALIDA" and self.turno_id is not None:
            raise ValueError("La salida no permite seleccionar turno")
        self.gps_evidence()
        return self

    def gps_evidence(self) -> EvidenciaGPSCreate:
        return EvidenciaGPSCreate(
            latitud=self.latitud,
            longitud=self.longitud,
            precision_m=self.precision_m,
            capturada_at=self.capturada_at,
        )


class AdministrativeExitForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    salida_at: datetime
    motivo: str = Field(min_length=1, max_length=1000)

    @field_validator("salida_at")
    @classmethod
    def use_operational_timezone(cls, value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=app_timezone())

    @field_validator("motivo")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El motivo es obligatorio")
        return normalized


class IncidentDecisionForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["APROBADA", "RECHAZADA"]
    comentario: str | None = Field(default=None, max_length=1000)

    @field_validator("decision", mode="before")
    @classmethod
    def normalize_decision(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("comentario")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PlaceData(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    tipo: Literal["BASE", "TALLER", "TERRENO"]
    comuna: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=300)
    tipo_geocerca: Literal["RADIO", "COMUNA"] | None = None
    codigo_comuna: str | None = Field(default=None, pattern=r"^\d{5}$")
    latitud: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"), max_digits=18, decimal_places=15)
    longitud: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"), max_digits=18, decimal_places=15)
    radio_metros: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    prioridad_geocerca: int = Field(default=100, gt=0)
    activo: bool = True

    @field_validator("nombre", "comuna", "direccion", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_geofence(self) -> "PlaceData":
        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("Latitud y longitud deben informarse juntas")
        if self.tipo_geocerca == "RADIO":
            if self.latitud is None or self.radio_metros is None:
                raise ValueError("Una geocerca RADIO requiere coordenadas y radio")
            if self.codigo_comuna is not None:
                raise ValueError("Una geocerca RADIO no usa CUT_COM")
        elif self.tipo_geocerca == "COMUNA":
            if self.codigo_comuna is None or self.latitud is None:
                raise ValueError("Una geocerca COMUNA requiere CUT_COM y coordenadas de referencia")
            if self.radio_metros is not None:
                raise ValueError("Una geocerca COMUNA no usa radio")
        elif self.codigo_comuna is not None or self.radio_metros is not None:
            raise ValueError("Selecciona un tipo de geocerca para configurar código o radio")
        return self
