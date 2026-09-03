import calendar
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.time import operational_date, utc_now
from app.models.attendance import (
    JustificacionInasistencia,
    MarcajeAsistencia,
    SesionTrabajo,
)
from app.services.attendance_rules_service import (
    AttendanceSessionFacts,
    AttendanceSessionProjection,
    project_session,
)


@dataclass(frozen=True)
class CalendarJustificationSummary:
    kind: str
    status: str


@dataclass(frozen=True)
class AttendanceCalendarDay:
    operational_date: date
    status: str
    label: str
    has_activity: bool
    has_incomplete_session: bool
    is_worked_date: bool
    session_count: int
    sessions: tuple[AttendanceSessionProjection, ...]
    incident_types: tuple[str, ...]
    justifications: tuple[CalendarJustificationSummary, ...]


def _calendar_session_summary(session: SesionTrabajo) -> AttendanceSessionProjection:
    entry = next((mark for mark in session.marcajes if mark.tipo == "ENTRADA"), None)
    exit_mark = next((mark for mark in session.marcajes if mark.tipo == "SALIDA"), None)
    pending_incidents = tuple(
        incident
        for mark in session.marcajes
        for incident in mark.incidencias
        if incident.estado == "PENDIENTE"
    )
    incident_types = tuple(sorted({incident.tipo for incident in pending_incidents}))
    return project_session(AttendanceSessionFacts(
        session_id=session.id,
        worker_id=session.trabajador_id,
        operational_date=session.fecha_operacional,
        shift_code=session.turno.codigo,
        shift_name=session.turno.nombre,
        recorded_state=session.estado,
        entry_at=entry.ocurrido_at if entry else None,
        exit_at=exit_mark.ocurrido_at if exit_mark else None,
        incident_count=len(pending_incidents),
        incident_types=incident_types,
    ))


def calendar_month(
    db: Session,
    worker_id: int,
    year: int,
    month: int,
    *,
    today: date | None = None,
):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    sessions = db.scalars(
        select(SesionTrabajo)
        .options(
            joinedload(SesionTrabajo.turno),
            selectinload(SesionTrabajo.marcajes).joinedload(
                MarcajeAsistencia.evaluacion_geografica
            ),
            selectinload(SesionTrabajo.marcajes).selectinload(
                MarcajeAsistencia.incidencias
            ),
        )
        .where(
            SesionTrabajo.trabajador_id == worker_id,
            SesionTrabajo.fecha_operacional >= first_day,
            SesionTrabajo.fecha_operacional <= last_day,
        )
        .order_by(SesionTrabajo.fecha_operacional, SesionTrabajo.id)
    ).all()
    justifications = db.scalars(
        select(JustificacionInasistencia).where(
            JustificacionInasistencia.trabajador_id == worker_id,
            JustificacionInasistencia.fecha >= first_day,
            JustificacionInasistencia.fecha <= last_day,
        )
    ).all()
    sessions_by_date: dict[date, list[SesionTrabajo]] = {}
    for session in sessions:
        sessions_by_date.setdefault(session.fecha_operacional, []).append(session)
    justifications_by_date: dict[date, list[JustificacionInasistencia]] = {}
    for item in justifications:
        justifications_by_date.setdefault(item.fecha, []).append(item)

    current_date = today or operational_date(utc_now())
    days: dict[int, AttendanceCalendarDay] = {}
    for day_number in range(1, last_day.day + 1):
        target_date = date(year, month, day_number)
        source_sessions = sessions_by_date.get(target_date, [])
        session_summaries = tuple(
            _calendar_session_summary(session) for session in source_sessions
        )
        justification_summaries = tuple(
            CalendarJustificationSummary(item.tipo, item.estado)
            for item in justifications_by_date.get(target_date, [])
        )
        has_activity = any(item.has_activity for item in session_summaries)
        has_incomplete = any(item.is_incomplete for item in session_summaries)
        is_worked = any(item.is_closed_valid for item in session_summaries)
        incident_types = tuple(
            sorted({kind for item in session_summaries for kind in item.incident_types})
        )
        is_out_of_range = any(
            mark.evaluacion_geografica is not None
            and mark.evaluacion_geografica.estado_geocerca == "FUERA_RANGO"
            for session in source_sessions
            for mark in session.marcajes
        ) or "FUERA_RANGO" in incident_types
        needs_review = bool(
            incident_types
            or justification_summaries
            or any(not item.is_closed_valid for item in session_summaries)
            or any(item.is_late for item in session_summaries)
        )
        if is_out_of_range:
            status = "FUERA_RANGO"
            label = "Fecha trabajada · fuera de rango" if is_worked else "Fuera de rango · revisión"
        elif needs_review:
            status = "REVISION"
            if has_incomplete:
                label = "Actividad registrada · incompleta"
            else:
                label = "Fecha trabajada · revisión" if is_worked else "Pendiente de revisión"
        elif is_worked:
            status = "TRABAJADO"
            label = "Fecha trabajada"
        else:
            status = "NEUTRAL"
            label = "Fecha futura" if target_date > current_date else "Sin estado determinable"
        days[day_number] = AttendanceCalendarDay(
            operational_date=target_date,
            status=status,
            label=label,
            has_activity=has_activity,
            has_incomplete_session=has_incomplete,
            is_worked_date=is_worked,
            session_count=len(session_summaries),
            sessions=session_summaries,
            incident_types=incident_types,
            justifications=justification_summaries,
        )
    return calendar.Calendar(firstweekday=0).monthdayscalendar(year, month), days
