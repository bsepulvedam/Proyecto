from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import (
    attendance_max_gps_accuracy_meters,
    attendance_min_session_minutes,
)
from app.core.time import operational_date, utc_now
from app.models.attendance import (
    EvaluacionGeograficaMarcaje,
    EvidenciaGPSMarcaje,
    IncidenciaAsistencia,
    LugarTrabajo,
    MarcajeAsistencia,
    SesionTrabajo,
    Turno,
)
from app.models.identity import Trabajador
from app.schemas.attendance import EvidenciaGPSCreate

EARTH_RADIUS_METERS = 6_371_000
GEOFENCE_RULE_VERSION = "4B-1"
MARK_TYPES = {"ENTRADA", "SALIDA"}


class AttendanceMarkError(ValueError):
    pass


@dataclass(frozen=True)
class GeoEvaluationResult:
    place_id: int | None
    distance_m: Decimal | None
    radius_m: Decimal | None
    geofence_status: str
    accuracy_status: str
    max_accuracy_m: Decimal


@dataclass(frozen=True)
class AttendanceRegistrationState:
    has_open_session: bool
    shift_code: str | None
    shift_name: str | None
    entry_time: datetime | None


@dataclass(frozen=True)
class AttendanceMarkFeedback:
    mark_type: str
    geofence_status: str
    accuracy_status: str


def get_attendance_registration_state(
    db: Session, worker: Trabajador
) -> AttendanceRegistrationState:
    session = db.scalar(
        select(SesionTrabajo)
        .options(joinedload(SesionTrabajo.turno))
        .where(
            SesionTrabajo.trabajador_id == worker.id,
            SesionTrabajo.estado == "ABIERTA",
        )
    )
    if session is None:
        return AttendanceRegistrationState(False, None, None, None)
    entry_time = db.scalar(
        select(MarcajeAsistencia.ocurrido_at).where(
            MarcajeAsistencia.sesion_id == session.id,
            MarcajeAsistencia.tipo == "ENTRADA",
        )
    )
    return AttendanceRegistrationState(
        True,
        session.turno.codigo,
        session.turno.nombre,
        entry_time,
    )


def get_attendance_mark_feedback(
    db: Session, mark: MarcajeAsistencia
) -> AttendanceMarkFeedback:
    evaluation = db.scalar(
        select(EvaluacionGeograficaMarcaje).where(
            EvaluacionGeograficaMarcaje.marcaje_id == mark.id
        )
    )
    if evaluation is None:
        raise RuntimeError("El marcaje no tiene evaluación geográfica")
    return AttendanceMarkFeedback(
        mark.tipo,
        evaluation.estado_geocerca,
        evaluation.estado_precision,
    )


def haversine_distance_m(
    latitude_a: Decimal,
    longitude_a: Decimal,
    latitude_b: Decimal,
    longitude_b: Decimal,
) -> Decimal:
    lat_a, lon_a, lat_b, lon_b = map(
        radians, map(float, (latitude_a, longitude_a, latitude_b, longitude_b))
    )
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    value = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    distance = 2 * EARTH_RADIUS_METERS * asin(sqrt(value))
    return Decimal(str(distance)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def evaluate_geolocation(
    evidence: EvidenciaGPSCreate,
    places: Iterable[LugarTrabajo],
    max_accuracy_m: int | None = None,
) -> GeoEvaluationResult:
    applied_accuracy = Decimal(
        attendance_max_gps_accuracy_meters() if max_accuracy_m is None else max_accuracy_m
    )
    candidates: list[tuple[Decimal, LugarTrabajo]] = []
    for place in places:
        if not place.activo or place.latitud is None or place.longitud is None or place.radio_metros is None:
            continue
        distance = haversine_distance_m(
            evidence.latitud, evidence.longitud, place.latitud, place.longitud
        )
        candidates.append((distance, place))

    accuracy_status = "BAJA_PRECISION" if evidence.precision_m > applied_accuracy else "ACEPTABLE"
    if not candidates:
        return GeoEvaluationResult(
            place_id=None,
            distance_m=None,
            radius_m=None,
            geofence_status="SIN_ZONA_CONFIGURADA",
            accuracy_status=accuracy_status,
            max_accuracy_m=applied_accuracy,
        )

    distance, nearest = min(candidates, key=lambda item: item[0])
    radius = Decimal(nearest.radio_metros)
    return GeoEvaluationResult(
        place_id=nearest.id,
        distance_m=distance,
        radius_m=radius,
        geofence_status="DENTRO_RANGO" if distance <= radius else "FUERA_RANGO",
        accuracy_status=accuracy_status,
        max_accuracy_m=applied_accuracy,
    )


def _locked_worker(db: Session, worker: Trabajador) -> Trabajador:
    persisted = db.scalar(
        select(Trabajador).where(Trabajador.id == worker.id).with_for_update()
    )
    if persisted is None or not persisted.activo:
        raise AttendanceMarkError("El trabajador no existe o está inactivo.")
    return persisted


def _open_session(db: Session, worker_id: int) -> SesionTrabajo | None:
    return db.scalar(
        select(SesionTrabajo)
        .where(
            SesionTrabajo.trabajador_id == worker_id,
            SesionTrabajo.estado == "ABIERTA",
        )
        .with_for_update()
    )


def _active_places(db: Session) -> list[LugarTrabajo]:
    return list(
        db.scalars(
            select(LugarTrabajo).where(
                LugarTrabajo.activo.is_(True),
                LugarTrabajo.latitud.is_not(None),
                LugarTrabajo.longitud.is_not(None),
                LugarTrabajo.radio_metros.is_not(None),
            )
        ).all()
    )


def _attach_geolocation(
    db: Session,
    mark: MarcajeAsistencia,
    evidence: EvidenciaGPSCreate,
    evaluation: GeoEvaluationResult,
    occurred_at,
) -> None:
    db.add(
        EvidenciaGPSMarcaje(
            marcaje=mark,
            latitud=evidence.latitud,
            longitud=evidence.longitud,
            precision_m=evidence.precision_m,
            capturada_at=evidence.capturada_at,
        )
    )
    db.add(
        EvaluacionGeograficaMarcaje(
            marcaje=mark,
            lugar_detectado_id=evaluation.place_id,
            distancia_m=evaluation.distance_m,
            radio_m_aplicado=evaluation.radius_m,
            estado_geocerca=evaluation.geofence_status,
            estado_precision=evaluation.accuracy_status,
            max_precision_m_aplicada=evaluation.max_accuracy_m,
            regla_version=GEOFENCE_RULE_VERSION,
            evaluada_at=occurred_at,
        )
    )
    if evaluation.geofence_status == "FUERA_RANGO":
        db.add(IncidenciaAsistencia(marcaje=mark, tipo="FUERA_RANGO"))
    if evaluation.accuracy_status == "BAJA_PRECISION":
        db.add(IncidenciaAsistencia(marcaje=mark, tipo="GPS_BAJA_PRECISION"))


def register_attendance_mark(
    db: Session,
    worker: Trabajador,
    mark_type: str,
    gps_evidence: EvidenciaGPSCreate | None,
    *,
    shift_id: int | None = None,
) -> MarcajeAsistencia:
    normalized_type = mark_type.strip().upper()
    if normalized_type not in MARK_TYPES:
        raise AttendanceMarkError("El tipo de marcaje debe ser ENTRADA o SALIDA.")
    if gps_evidence is None:
        raise AttendanceMarkError("El marcaje requiere evidencia GPS válida.")

    try:
        official_time = utc_now().astimezone(timezone.utc)
        evaluation = evaluate_geolocation(gps_evidence, _active_places(db))
        persisted_worker = _locked_worker(db, worker)
        session = _open_session(db, persisted_worker.id)

        if normalized_type == "ENTRADA":
            if session is not None:
                raise AttendanceMarkError("El trabajador ya tiene una sesión abierta.")
            shift = db.get(Turno, shift_id) if shift_id is not None else None
            if shift is None or not shift.activo:
                raise AttendanceMarkError("Debes seleccionar un turno activo.")
            session = SesionTrabajo(
                trabajador_id=persisted_worker.id,
                turno_id=shift.id,
                fecha_operacional=operational_date(official_time),
                estado="ABIERTA",
            )
            db.add(session)
            db.flush()
        else:
            if session is None:
                raise AttendanceMarkError("El trabajador no tiene una sesión abierta.")
            entry = db.scalar(
                select(MarcajeAsistencia).where(
                    MarcajeAsistencia.sesion_id == session.id,
                    MarcajeAsistencia.tipo == "ENTRADA",
                )
            )
            if entry is None:
                raise AttendanceMarkError("La sesión abierta no tiene una entrada válida.")
            entry_time = entry.ocurrido_at
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            minimum_minutes = attendance_min_session_minutes()
            minimum = timedelta(minutes=minimum_minutes)
            if official_time - entry_time < minimum:
                raise AttendanceMarkError(
                    f"La salida requiere al menos {minimum_minutes} minutos desde la entrada."
                )

        mark = MarcajeAsistencia(
            sesion_id=session.id,
            tipo=normalized_type,
            ocurrido_at=official_time,
        )
        db.add(mark)
        db.flush()
        _attach_geolocation(db, mark, gps_evidence, evaluation, official_time)
        if normalized_type == "SALIDA":
            session.estado = "CERRADA"
            session.cerrado_at = official_time
        db.commit()
        return mark
    except AttendanceMarkError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        if normalized_type == "ENTRADA":
            raise AttendanceMarkError("El trabajador ya tiene una sesión abierta.") from exc
        raise AttendanceMarkError("El estado de la sesión cambió durante el marcaje.") from exc
    except Exception:
        db.rollback()
        raise
