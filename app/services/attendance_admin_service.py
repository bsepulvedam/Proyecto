from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import attendance_min_session_minutes
from app.core.time import utc_now
from app.models.attendance import (
    IncidenciaAsistencia,
    IntervencionSalidaAdministrativa,
    MarcajeAsistencia,
    SesionTrabajo,
)
from app.models.identity import Usuario


ADMINISTRATIVE_EXIT = "COMPLETAR_SALIDA"
INCIDENT_DECISIONS = {"APROBADA", "RECHAZADA"}


class AttendanceAdministrationError(ValueError):
    pass


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AttendanceAdministrationError(
            f"{field_name} debe incluir una zona horaria explícita."
        )
    return value.astimezone(timezone.utc)


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AttendanceAdministrationError("El motivo es obligatorio.")
    return normalized


def complete_administrative_exit(
    db: Session,
    session_id: int,
    entered_exit_at: datetime,
    actor: Usuario,
    reason: str,
    *,
    action_at: datetime | None = None,
) -> IntervencionSalidaAdministrativa:
    """Close one incomplete session and preserve the administrative intervention."""
    try:
        exit_at = _aware_utc(entered_exit_at, "La hora de salida")
        closed_at = _aware_utc(action_at or utc_now(), "La fecha de la acción")
        normalized_reason = _reason(reason)
        session = db.scalar(
            select(SesionTrabajo)
            .where(SesionTrabajo.id == session_id)
            .with_for_update()
        )
        if session is None:
            raise AttendanceAdministrationError("La sesión no existe.")
        if session.estado != "ABIERTA":
            raise AttendanceAdministrationError(
                "La sesión ya no está disponible para completar su salida."
            )

        marks = list(
            db.scalars(
                select(MarcajeAsistencia)
                .where(MarcajeAsistencia.sesion_id == session.id)
                .order_by(MarcajeAsistencia.id)
                .with_for_update()
            ).all()
        )
        entries = [mark for mark in marks if mark.tipo == "ENTRADA"]
        exits = [mark for mark in marks if mark.tipo == "SALIDA"]
        if len(entries) != 1 or exits:
            raise AttendanceAdministrationError(
                "La sesión no tiene una ausencia de salida válida para completar."
            )
        entry_at = entries[0].ocurrido_at
        if entry_at.tzinfo is None:
            entry_at = entry_at.replace(tzinfo=timezone.utc)
        else:
            entry_at = entry_at.astimezone(timezone.utc)
        minimum_minutes = attendance_min_session_minutes()
        if exit_at <= entry_at or exit_at - entry_at < timedelta(minutes=minimum_minutes):
            raise AttendanceAdministrationError(
                f"La salida debe ser posterior y respetar al menos {minimum_minutes} minutos desde la entrada."
            )

        exit_mark = MarcajeAsistencia(
            sesion_id=session.id,
            tipo="SALIDA",
            ocurrido_at=exit_at,
        )
        db.add(exit_mark)
        db.flush()
        intervention = IntervencionSalidaAdministrativa(
            sesion_id=session.id,
            marcaje_salida_id=exit_mark.id,
            tipo_marcaje_salida="SALIDA",
            tipo_intervencion=ADMINISTRATIVE_EXIT,
            hora_laboral_introducida=exit_at,
            salida_original_ausente=True,
            creado_por_id=actor.id,
            motivo=normalized_reason,
        )
        db.add(intervention)
        session.estado = "CERRADA"
        session.cerrado_at = closed_at
        db.commit()
        db.refresh(intervention)
        return intervention
    except AttendanceAdministrationError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise AttendanceAdministrationError(
            "La sesión cambió mientras se completaba la salida."
        ) from exc
    except Exception:
        db.rollback()
        raise


def decide_attendance_incident(
    db: Session,
    incident_id: int,
    decision: str,
    actor: Usuario,
    *,
    comment: str | None = None,
    decided_at: datetime | None = None,
) -> IncidenciaAsistencia:
    normalized_decision = decision.strip().upper()
    if normalized_decision not in INCIDENT_DECISIONS:
        raise AttendanceAdministrationError(
            "La decisión debe ser APROBADA o RECHAZADA."
        )
    normalized_comment = comment.strip() if comment and comment.strip() else None
    try:
        resolution_at = _aware_utc(
            decided_at or utc_now(), "La fecha de resolución"
        )
        incident = db.scalar(
            select(IncidenciaAsistencia)
            .where(IncidenciaAsistencia.id == incident_id)
            .with_for_update()
        )
        if incident is None:
            raise AttendanceAdministrationError("La incidencia no existe.")
        if incident.estado != "PENDIENTE":
            raise AttendanceAdministrationError(
                "La incidencia ya tiene una decisión final."
            )
        incident.estado = normalized_decision
        incident.resuelto_por_id = actor.id
        incident.resuelto_at = resolution_at
        incident.comentario_resolucion = normalized_comment
        db.commit()
        db.refresh(incident)
        return incident
    except AttendanceAdministrationError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise AttendanceAdministrationError(
            "La incidencia cambió mientras se registraba la decisión."
        ) from exc
    except Exception:
        db.rollback()
        raise
