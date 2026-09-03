from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterator

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.time import operational_date, utc_now
from app.models.attendance import (
    EvaluacionGeograficaMarcaje,
    IncidenciaAsistencia,
    MarcajeAsistencia,
    SesionTrabajo,
)
from app.models.identity import Trabajador
from app.services.attendance_calendar_service import attendance_session_facts
from app.services.attendance_rate_service import rate_versions_for_workers
from app.services.attendance_rules_service import (
    AttendanceDayProjection,
    AttendancePeriodProjection,
    AttendanceSessionProjection,
    project_period,
)


MAX_PERIOD_DAYS = 366
PAGE_SIZE = 25


class AttendanceSupervisionError(ValueError):
    pass


@dataclass(frozen=True)
class SupervisionPeriod:
    start: date
    end: date


@dataclass(frozen=True)
class SupervisionIncident:
    id: int
    kind: str
    status: str
    detail: str | None
    resolution_comment: str | None


@dataclass(frozen=True)
class SupervisionMark:
    kind: str
    occurred_at: datetime
    place_name: str | None
    geofence_type: str | None
    geofence_status: str | None
    accuracy_status: str | None
    incidents: tuple[SupervisionIncident, ...]
    is_administrative: bool


@dataclass(frozen=True)
class SupervisionSession:
    projection: AttendanceSessionProjection
    marks: tuple[SupervisionMark, ...]
    administrative_exit_reason: str | None


@dataclass(frozen=True)
class SupervisionDay:
    projection: AttendanceDayProjection
    sessions: tuple[SupervisionSession, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class WorkerSupervision:
    worker: Trabajador
    period: SupervisionPeriod
    projection: AttendancePeriodProjection
    days: tuple[SupervisionDay, ...]

    @property
    def days_by_date(self) -> dict[date, SupervisionDay]:
        return {item.projection.operational_date: item for item in self.days}


@dataclass(frozen=True)
class WorkerSupervisionSummary:
    worker: Trabajador
    projection: AttendancePeriodProjection


@dataclass(frozen=True)
class SupervisionListing:
    period: SupervisionPeriod
    query: str
    page: int
    page_size: int
    total_workers: int
    workers: tuple[WorkerSupervisionSummary, ...]

    @property
    def total_pages(self) -> int:
        return max(1, (self.total_workers + self.page_size - 1) // self.page_size)


def supervision_period(
    start_value: str | None,
    end_value: str | None,
    *,
    today: date | None = None,
) -> SupervisionPeriod:
    current = today or operational_date(utc_now())
    if not start_value and not end_value:
        return SupervisionPeriod(current.replace(day=1), current)
    if not start_value or not end_value:
        raise AttendanceSupervisionError("Debes indicar ambas fechas del período.")
    try:
        start = date.fromisoformat(start_value)
        end = date.fromisoformat(end_value)
    except ValueError as exc:
        raise AttendanceSupervisionError("El período no tiene un formato válido.") from exc
    if start > end:
        raise AttendanceSupervisionError("La fecha desde no puede ser posterior a la fecha hasta.")
    if (end - start).days + 1 > MAX_PERIOD_DAYS:
        raise AttendanceSupervisionError(
            f"El período no puede superar {MAX_PERIOD_DAYS} días."
        )
    return SupervisionPeriod(start, end)


def _normalized_query(value: str | None) -> str:
    normalized = (value or "").strip()
    if len(normalized) > 100:
        raise AttendanceSupervisionError("La búsqueda no puede superar 100 caracteres.")
    return normalized


def _sessions_query(worker_ids: tuple[int, ...], period: SupervisionPeriod):
    return (
        select(SesionTrabajo)
        .options(
            joinedload(SesionTrabajo.turno),
            joinedload(SesionTrabajo.intervencion_salida),
            selectinload(SesionTrabajo.marcajes)
            .joinedload(MarcajeAsistencia.evaluacion_geografica)
            .joinedload(EvaluacionGeograficaMarcaje.lugar_detectado),
            selectinload(SesionTrabajo.marcajes).selectinload(
                MarcajeAsistencia.incidencias
            ),
        )
        .where(
            SesionTrabajo.trabajador_id.in_(worker_ids),
            SesionTrabajo.fecha_operacional >= period.start,
            SesionTrabajo.fecha_operacional <= period.end,
        )
        .order_by(SesionTrabajo.fecha_operacional, SesionTrabajo.id)
    )


def _load_sessions(
    db: Session,
    worker_ids: tuple[int, ...],
    period: SupervisionPeriod,
) -> tuple[SesionTrabajo, ...]:
    if not worker_ids:
        return ()
    return tuple(db.scalars(_sessions_query(worker_ids, period)).all())


def _period_projection(
    worker_id: int,
    sessions: tuple[SesionTrabajo, ...],
    rate_versions,
) -> AttendancePeriodProjection:
    return project_period(
        worker_id,
        (
            attendance_session_facts(session, incident_states=None)
            for session in sessions
        ),
        rate_versions,
        allow_missing_rates=True,
    )


def _worker_conditions(period: SupervisionPeriod, query: str):
    activity = exists(
        select(SesionTrabajo.id).where(
            SesionTrabajo.trabajador_id == Trabajador.id,
            SesionTrabajo.fecha_operacional >= period.start,
            SesionTrabajo.fecha_operacional <= period.end,
        )
    )
    conditions = [or_(Trabajador.activo.is_(True), activity)]
    if query:
        escaped_query = (
            query.casefold()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped_query}%"
        conditions.append(
            or_(
                func.lower(Trabajador.nombres).like(pattern, escape="\\"),
                func.lower(Trabajador.apellidos).like(pattern, escape="\\"),
                func.lower(func.coalesce(Trabajador.codigo_interno, "")).like(
                    pattern, escape="\\"
                ),
                func.lower(Trabajador.nombres + " " + Trabajador.apellidos).like(
                    pattern, escape="\\"
                ),
            )
        )
    return conditions


def _summaries_for_workers(
    db: Session,
    workers: tuple[Trabajador, ...],
    period: SupervisionPeriod,
) -> tuple[WorkerSupervisionSummary, ...]:
    worker_ids = tuple(worker.id for worker in workers)
    sessions = _load_sessions(db, worker_ids, period)
    rates = rate_versions_for_workers(db, worker_ids, through_date=period.end)
    sessions_by_worker: dict[int, list[SesionTrabajo]] = {}
    for session in sessions:
        sessions_by_worker.setdefault(session.trabajador_id, []).append(session)
    return tuple(
        WorkerSupervisionSummary(
            worker=worker,
            projection=_period_projection(
                worker.id,
                tuple(sessions_by_worker.get(worker.id, [])),
                rates,
            ),
        )
        for worker in workers
    )


def _mark(
    mark: MarcajeAsistencia,
    administrative_exit_mark_id: int | None,
) -> SupervisionMark:
    evaluation = mark.evaluacion_geografica
    return SupervisionMark(
        kind=mark.tipo,
        occurred_at=mark.ocurrido_at,
        place_name=(evaluation.lugar_detectado.nombre if evaluation and evaluation.lugar_detectado else None),
        geofence_type=evaluation.tipo_geocerca_aplicado if evaluation else None,
        geofence_status=evaluation.estado_geocerca if evaluation else None,
        accuracy_status=evaluation.estado_precision if evaluation else None,
        incidents=tuple(
            SupervisionIncident(
                id=incident.id,
                kind=incident.tipo,
                status=incident.estado,
                detail=incident.detalle,
                resolution_comment=incident.comentario_resolucion,
            )
            for incident in sorted(mark.incidencias, key=lambda item: item.id)
        ),
        is_administrative=mark.id == administrative_exit_mark_id,
    )


def _day_labels(day: AttendanceDayProjection, sessions: tuple[SesionTrabajo, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    if day.has_incomplete_session:
        labels.append("INCOMPLETA")
    if day.incident_count:
        labels.append("INCIDENCIA")
    if any(
        mark.evaluacion_geografica is not None
        and mark.evaluacion_geografica.estado_geocerca == "DENTRO_TOLERANCIA"
        for session in sessions
        for mark in session.marcajes
    ):
        labels.append("TOLERANCIA / REVISIÓN")
    if day.is_double_shift:
        labels.append("DOBLE TURNO")
    if not labels:
        labels.append("JORNADA CORRECTA" if day.has_activity else "SIN ACTIVIDAD")
    return tuple(labels)


def _worker_result(
    worker: Trabajador,
    period: SupervisionPeriod,
    sessions: tuple[SesionTrabajo, ...],
    rate_versions,
) -> WorkerSupervision:
    projection = _period_projection(worker.id, sessions, rate_versions)
    source_by_id = {session.id: session for session in sessions}
    detailed_days: list[SupervisionDay] = []
    for day in projection.days:
        source_sessions = tuple(source_by_id[item.session_id] for item in day.sessions)
        detailed_sessions = tuple(
            SupervisionSession(
                projection=session_projection,
                marks=tuple(
                    _mark(
                        mark,
                        source.intervencion_salida.marcaje_salida_id
                        if source.intervencion_salida is not None
                        else None,
                    )
                    for mark in source.marcajes
                ),
                administrative_exit_reason=(
                    source.intervencion_salida.motivo
                    if source.intervencion_salida is not None
                    else None
                ),
            )
            for session_projection, source in zip(day.sessions, source_sessions, strict=True)
        )
        detailed_days.append(
            SupervisionDay(
                projection=day,
                sessions=detailed_sessions,
                labels=_day_labels(day, source_sessions),
            )
        )
    return WorkerSupervision(
        worker=worker,
        period=period,
        projection=projection,
        days=tuple(detailed_days),
    )


def list_worker_supervision(
    db: Session,
    period: SupervisionPeriod,
    *,
    query: str | None = None,
    page: int = 1,
) -> SupervisionListing:
    if isinstance(page, bool) or page < 1:
        raise AttendanceSupervisionError("La página solicitada no es válida.")
    normalized_query = _normalized_query(query)
    conditions = _worker_conditions(period, normalized_query)
    total_workers = db.scalar(
        select(func.count(Trabajador.id)).where(*conditions)
    ) or 0
    workers = tuple(
        db.scalars(
            select(Trabajador)
            .where(*conditions)
            .order_by(Trabajador.apellidos, Trabajador.nombres, Trabajador.id)
            .limit(PAGE_SIZE)
            .offset((page - 1) * PAGE_SIZE)
        ).all()
    )
    summaries = _summaries_for_workers(db, workers, period)
    return SupervisionListing(
        period=period,
        query=normalized_query,
        page=page,
        page_size=PAGE_SIZE,
        total_workers=total_workers,
        workers=summaries,
    )


def iter_worker_supervision_summaries(
    db: Session,
    period: SupervisionPeriod,
    *,
    query: str | None = None,
    batch_size: int = 200,
) -> Iterator[WorkerSupervisionSummary]:
    """Project all filtered Workers in bounded batches for XLSX generation."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise AttendanceSupervisionError("El tamaño de lote no es válido.")
    normalized_query = _normalized_query(query)
    conditions = _worker_conditions(period, normalized_query)
    offset = 0
    while True:
        workers = tuple(
            db.scalars(
                select(Trabajador)
                .where(*conditions)
                .order_by(Trabajador.apellidos, Trabajador.nombres, Trabajador.id)
                .limit(batch_size)
                .offset(offset)
            ).all()
        )
        if not workers:
            return
        yield from _summaries_for_workers(db, workers, period)
        offset += len(workers)


def get_worker_supervision(
    db: Session,
    worker_id: int,
    period: SupervisionPeriod,
) -> WorkerSupervision | None:
    worker = db.get(Trabajador, worker_id)
    if worker is None:
        return None
    sessions = _load_sessions(db, (worker.id,), period)
    rates = rate_versions_for_workers(db, (worker.id,), through_date=period.end)
    return _worker_result(worker, period, sessions, rates)


def get_worker_day_supervision(
    db: Session,
    worker_id: int,
    target_date: date,
) -> tuple[WorkerSupervision, SupervisionDay | None] | None:
    period = SupervisionPeriod(target_date, target_date)
    result = get_worker_supervision(db, worker_id, period)
    if result is None:
        return None
    return result, (result.days[0] if result.days else None)


def session_location(db: Session, session_id: int) -> tuple[int, date] | None:
    return db.execute(
        select(SesionTrabajo.trabajador_id, SesionTrabajo.fecha_operacional).where(
            SesionTrabajo.id == session_id
        )
    ).one_or_none()


def incident_location(db: Session, incident_id: int) -> tuple[int, date] | None:
    return db.execute(
        select(SesionTrabajo.trabajador_id, SesionTrabajo.fecha_operacional)
        .join(MarcajeAsistencia, MarcajeAsistencia.sesion_id == SesionTrabajo.id)
        .join(IncidenciaAsistencia, IncidenciaAsistencia.marcaje_id == MarcajeAsistencia.id)
        .where(IncidenciaAsistencia.id == incident_id)
    ).one_or_none()


def period_dates(period: SupervisionPeriod) -> tuple[date, ...]:
    return tuple(
        period.start + timedelta(days=offset)
        for offset in range((period.end - period.start).days + 1)
    )
