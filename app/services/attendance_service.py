import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import justification_max_bytes, justification_storage_dir
from app.database.session import PROJECT_ROOT
from app.models.attendance import (
    AsignacionTrabajadorLugar,
    JustificacionInasistencia,
    LugarTrabajo,
    Turno,
)
from app.models.identity import Trabajador, Usuario
from app.schemas.attendance import PlaceData
from app.services.attendance_geofence_service import commune_display_name
from app.services.auth_service import IdentityError

JUSTIFICATION_TYPES = ("LICENCIA_MEDICA", "TRAMITE", "COORDINACION_JEFATURA", "OTRO")
MAGIC_TYPES = {b"%PDF": ("pdf", "application/pdf"), b"\xff\xd8\xff": ("jpg", "image/jpeg"), b"\x89PNG\r\n\x1a\n": ("png", "image/png")}


def list_places(db: Session): return list(db.scalars(select(LugarTrabajo).order_by(LugarTrabajo.tipo, LugarTrabajo.nombre)).all())
def get_place(db: Session, place_id: int): return db.get(LugarTrabajo, place_id)


def save_place(db: Session, values: PlaceData | dict, place: LugarTrabajo | None = None):
    data = values if isinstance(values, PlaceData) else PlaceData.model_validate(values)
    normalized = data.model_dump()
    if data.tipo_geocerca == "COMUNA":
        normalized["comuna"] = commune_display_name(data.codigo_comuna or "")
    target = place or LugarTrabajo()
    for key, value in normalized.items(): setattr(target, key, value)
    try: db.add(target); db.commit(); db.refresh(target); return target
    except IntegrityError as exc: db.rollback(); raise IdentityError("El nombre del lugar ya existe o los datos no son válidos.") from exc


def set_place_active(db: Session, place: LugarTrabajo, active: bool) -> LugarTrabajo:
    place.activo = active
    try:
        db.commit()
        return place
    except SQLAlchemyError as exc:
        db.rollback()
        raise IdentityError("No fue posible actualizar el estado de la zona.") from exc


def create_assignment(db: Session, worker_id: int, place_id: int, desde: datetime, hasta: datetime | None, active: bool, creator_id: int):
    if db.get(Trabajador, worker_id) is None or db.get(LugarTrabajo, place_id) is None: raise IdentityError("Trabajador o lugar no válido.")
    item = AsignacionTrabajadorLugar(trabajador_id=worker_id, lugar_id=place_id, desde=desde, hasta=hasta, activo=active, creado_por_id=creator_id)
    db.add(item); db.commit(); db.refresh(item); return item


def list_assignments(db: Session):
    return list(db.scalars(select(AsignacionTrabajadorLugar).options(joinedload(AsignacionTrabajadorLugar.trabajador), joinedload(AsignacionTrabajadorLugar.lugar), joinedload(AsignacionTrabajadorLugar.creado_por)).order_by(AsignacionTrabajadorLugar.desde.desc())).all())


def list_shifts(db: Session): return list(db.scalars(select(Turno).where(Turno.activo.is_(True)).order_by(Turno.id)).all())


def worker_for_user(user: Usuario) -> Trabajador:
    if user.trabajador is None: raise IdentityError("Tu cuenta no está asociada a un trabajador.")
    if not user.trabajador.activo: raise IdentityError("El trabajador está inactivo. Contacta a un administrador.")
    return user.trabajador


def list_justifications(db: Session, worker_id: int):
    return list(db.scalars(select(JustificacionInasistencia).where(JustificacionInasistencia.trabajador_id == worker_id).order_by(JustificacionInasistencia.fecha.desc(), JustificacionInasistencia.id.desc())).all())


def get_justification(db: Session, worker_id: int, item_id: int):
    return db.scalar(select(JustificacionInasistencia).where(JustificacionInasistencia.id == item_id, JustificacionInasistencia.trabajador_id == worker_id))


async def store_upload(upload: UploadFile | None):
    if upload is None or not upload.filename: return None
    data = await upload.read(justification_max_bytes() + 1)
    if len(data) > justification_max_bytes(): raise IdentityError("El archivo supera el tamaño máximo permitido.")
    detected = next((value for magic, value in MAGIC_TYPES.items() if data.startswith(magic)), None)
    if detected is None: raise IdentityError("El archivo debe ser PDF, JPG, JPEG o PNG válido.")
    extension, mime = detected; key = f"{uuid.uuid4().hex}.{extension}"
    root = Path(justification_storage_dir()); root = root if root.is_absolute() else PROJECT_ROOT / root
    root.mkdir(parents=True, exist_ok=True); path = (root / key).resolve()
    if root.resolve() not in path.parents: raise IdentityError("Ruta de almacenamiento inválida.")
    path.write_bytes(data)
    return {"archivo_nombre_original": Path(upload.filename).name[:255], "archivo_storage_key": key, "archivo_mime": mime, "archivo_tamano": len(data)}


async def create_justification(db: Session, worker: Trabajador, selected_date: date, kind: str, observation: str, upload: UploadFile | None):
    kind = kind.upper()
    if kind not in JUSTIFICATION_TYPES: raise IdentityError("Tipo de justificación no válido.")
    metadata = await store_upload(upload)
    observation = observation.strip()
    if not observation and metadata is None: raise IdentityError("Debes ingresar una observación o adjuntar un archivo.")
    item = JustificacionInasistencia(trabajador_id=worker.id, fecha=selected_date, tipo=kind, observacion=observation or None, **(metadata or {}))
    try: db.add(item); db.commit(); db.refresh(item); return item
    except Exception:
        db.rollback()
        if metadata: justification_file_path(metadata["archivo_storage_key"]).unlink(missing_ok=True)
        raise


def justification_file_path(key: str) -> Path:
    root = Path(justification_storage_dir()); root = (root if root.is_absolute() else PROJECT_ROOT / root).resolve()
    path = (root / Path(key).name).resolve()
    if root not in path.parents: raise IdentityError("Archivo inválido.")
    return path
