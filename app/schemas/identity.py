from pydantic import BaseModel, Field, field_validator


class LoginData(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().casefold()


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=12, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().casefold()


class WorkerData(BaseModel):
    nombres: str = Field(min_length=1, max_length=160)
    apellidos: str = Field(min_length=1, max_length=160)
    empresa_id: int | None = None
    codigo_interno: str | None = Field(default=None, max_length=80)
    activo: bool = True

    @field_validator("nombres", "apellidos")
    @classmethod
    def clean_required(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("codigo_interno")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None


class AdminUserData(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    trabajador_id: int | None = None
    rol: str
    activo: bool = True

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("rol")
    @classmethod
    def valid_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"ADMIN", "JEFATURA", "TRABAJADOR"}:
            raise ValueError("Rol no válido")
        return normalized


class PasswordChangeData(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)
    confirmation: str = Field(min_length=1, max_length=1024)
