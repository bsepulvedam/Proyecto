from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Mapping

from app.core.config import (
    attendance_day_shift_end,
    attendance_day_shift_start,
    attendance_late_tolerance_minutes,
    attendance_min_session_minutes,
    attendance_night_shift_end,
    attendance_night_shift_start,
)
from app.core.time import app_timezone, local_datetime


DAY_SHIFT = "DIURNO"
NIGHT_SHIFT = "NOCTURNO"
PAYABLE_SHIFT_ORDER = (DAY_SHIFT, NIGHT_SHIFT)

ON_TIME = "EN_HORARIO"
EARLY_ENTRY = "ENTRADA_ADELANTADA"
LATE_ENTRY = "ENTRADA_TARDIA"
EARLY_EXIT = "SALIDA_ANTICIPADA"
LATE_EXIT = "SALIDA_POSTERIOR"

GLOBAL_RATE = "GLOBAL"
INDIVIDUAL_RATE = "INDIVIDUAL"


class AttendanceRuleError(ValueError):
    pass


@dataclass(frozen=True)
class ShiftReference:
    code: str
    start: time
    end: time
    crosses_midnight: bool


@dataclass(frozen=True)
class AttendanceSessionFacts:
    session_id: int
    worker_id: int
    operational_date: date
    shift_code: str
    shift_name: str
    recorded_state: str
    entry_at: datetime | None
    exit_at: datetime | None
    incident_count: int
    incident_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttendanceSessionProjection:
    session_id: int
    worker_id: int
    operational_date: date
    shift_code: str
    shift_name: str
    recorded_state: str
    entry_time: datetime | None
    exit_time: datetime | None
    duration_minutes: int | None
    has_activity: bool
    is_incomplete: bool
    is_chronologically_valid: bool
    meets_minimum_duration: bool
    is_closed_valid: bool
    entry_situation: str | None
    exit_situation: str | None
    incident_count: int
    incident_types: tuple[str, ...]

    @property
    def is_late(self) -> bool:
        return self.entry_situation == LATE_ENTRY

    @property
    def requires_review(self) -> bool:
        return bool(
            self.incident_types
            or self.is_incomplete
            or (self.exit_time is not None and not self.has_activity)
            or (self.has_activity and not self.is_closed_valid)
            or self.entry_situation in {EARLY_ENTRY, LATE_ENTRY}
            or self.exit_situation in {EARLY_EXIT, LATE_EXIT}
        )


@dataclass(frozen=True)
class ProvisionalRateVersion:
    version_id: int
    effective_from: date
    amount_clp: int
    worker_id: int | None = None


@dataclass(frozen=True)
class EffectiveProvisionalRate:
    version_id: int
    effective_from: date
    amount_clp: int
    source: str


@dataclass(frozen=True)
class AttendanceDayProjection:
    worker_id: int
    operational_date: date
    sessions: tuple[AttendanceSessionProjection, ...]
    has_activity: bool
    has_completed_session: bool
    has_incomplete_session: bool
    payable_shift_codes: tuple[str, ...]
    payable_shifts: int
    is_double_shift: bool
    incident_count: int
    effective_rate: EffectiveProvisionalRate
    provisional_total_clp: int


@dataclass(frozen=True)
class AttendancePeriodProjection:
    worker_id: int
    days: tuple[AttendanceDayProjection, ...]
    activity_days: int
    completed_worked_days: int
    incomplete_sessions: int
    payable_shifts: int
    double_shift_days: int
    incident_count: int
    provisional_total_clp: int


def configured_shift_references() -> dict[str, ShiftReference]:
    return {
        DAY_SHIFT: ShiftReference(
            code=DAY_SHIFT,
            start=attendance_day_shift_start(),
            end=attendance_day_shift_end(),
            crosses_midnight=False,
        ),
        NIGHT_SHIFT: ShiftReference(
            code=NIGHT_SHIFT,
            start=attendance_night_shift_start(),
            end=attendance_night_shift_end(),
            crosses_midnight=True,
        ),
    }


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _expected_datetime(
    operational_date: date,
    reference_time: time,
    *,
    next_day: bool = False,
) -> datetime:
    target_date = operational_date + timedelta(days=1) if next_day else operational_date
    return datetime.combine(target_date, reference_time, tzinfo=app_timezone())


def _entry_situation(
    entry_time: datetime | None,
    facts: AttendanceSessionFacts,
    reference: ShiftReference | None,
    late_tolerance_minutes: int,
) -> str | None:
    if entry_time is None or reference is None:
        return None
    expected = _expected_datetime(facts.operational_date, reference.start)
    if entry_time < expected:
        return EARLY_ENTRY
    if entry_time <= expected + timedelta(minutes=late_tolerance_minutes):
        return ON_TIME
    return LATE_ENTRY


def _exit_situation(
    exit_time: datetime | None,
    facts: AttendanceSessionFacts,
    reference: ShiftReference | None,
) -> str | None:
    if exit_time is None or reference is None:
        return None
    expected = _expected_datetime(
        facts.operational_date,
        reference.end,
        next_day=reference.crosses_midnight,
    )
    if exit_time < expected:
        return EARLY_EXIT
    if exit_time == expected:
        return ON_TIME
    return LATE_EXIT


def project_session(
    facts: AttendanceSessionFacts,
    *,
    shift_references: Mapping[str, ShiftReference] | None = None,
    late_tolerance_minutes: int | None = None,
    minimum_session_minutes: int | None = None,
) -> AttendanceSessionProjection:
    references = shift_references or configured_shift_references()
    reference = references.get(facts.shift_code)
    tolerance = (
        attendance_late_tolerance_minutes()
        if late_tolerance_minutes is None
        else late_tolerance_minutes
    )
    minimum = (
        attendance_min_session_minutes()
        if minimum_session_minutes is None
        else minimum_session_minutes
    )
    if isinstance(tolerance, bool) or not isinstance(tolerance, int) or tolerance < 0:
        raise AttendanceRuleError("La tolerancia horaria no puede ser negativa.")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum <= 0:
        raise AttendanceRuleError("El mínimo de sesión debe ser positivo.")
    if (
        isinstance(facts.incident_count, bool)
        or not isinstance(facts.incident_count, int)
        or facts.incident_count < len(set(facts.incident_types))
    ):
        raise AttendanceRuleError("El conteo de incidencias no es coherente.")

    entry_utc = _aware_utc(facts.entry_at)
    exit_utc = _aware_utc(facts.exit_at)
    entry_time = local_datetime(entry_utc) if entry_utc else None
    exit_time = local_datetime(exit_utc) if exit_utc else None
    has_activity = entry_time is not None
    is_incomplete = has_activity and exit_time is None
    is_chronologically_valid = bool(
        entry_utc is not None and exit_utc is not None and exit_utc >= entry_utc
    )
    duration_minutes = (
        int((exit_utc - entry_utc).total_seconds() // 60)
        if is_chronologically_valid and entry_utc is not None and exit_utc is not None
        else None
    )
    meets_minimum_duration = bool(
        duration_minutes is not None and duration_minutes >= minimum
    )
    is_closed_valid = bool(
        facts.recorded_state == "CERRADA"
        and has_activity
        and exit_time is not None
        and is_chronologically_valid
        and meets_minimum_duration
    )
    return AttendanceSessionProjection(
        session_id=facts.session_id,
        worker_id=facts.worker_id,
        operational_date=facts.operational_date,
        shift_code=facts.shift_code,
        shift_name=facts.shift_name,
        recorded_state=facts.recorded_state,
        entry_time=entry_time,
        exit_time=exit_time,
        duration_minutes=duration_minutes,
        has_activity=has_activity,
        is_incomplete=is_incomplete,
        is_chronologically_valid=is_chronologically_valid,
        meets_minimum_duration=meets_minimum_duration,
        is_closed_valid=is_closed_valid,
        entry_situation=_entry_situation(entry_time, facts, reference, tolerance),
        exit_situation=_exit_situation(exit_time, facts, reference),
        incident_count=facts.incident_count,
        incident_types=tuple(sorted(set(facts.incident_types))),
    )


def resolve_effective_rate(
    target_date: date,
    worker_id: int,
    versions: Iterable[ProvisionalRateVersion],
) -> EffectiveProvisionalRate:
    if isinstance(worker_id, bool) or not isinstance(worker_id, int) or worker_id <= 0:
        raise AttendanceRuleError("El trabajador de la tarifa no es válido.")
    applicable: list[ProvisionalRateVersion] = []
    for version in versions:
        if (
            isinstance(version.amount_clp, bool)
            or not isinstance(version.amount_clp, int)
            or version.amount_clp <= 0
        ):
            raise AttendanceRuleError("La tarifa provisional debe ser un entero positivo.")
        if (
            isinstance(version.version_id, bool)
            or not isinstance(version.version_id, int)
            or version.version_id < 0
        ):
            raise AttendanceRuleError("La versión de tarifa no puede ser negativa.")
        if version.worker_id is not None and (
            isinstance(version.worker_id, bool)
            or not isinstance(version.worker_id, int)
            or version.worker_id <= 0
        ):
            raise AttendanceRuleError("El trabajador de la tarifa no es válido.")
        if version.effective_from <= target_date and version.worker_id in {None, worker_id}:
            applicable.append(version)

    individual = [version for version in applicable if version.worker_id == worker_id]
    candidates = individual or [version for version in applicable if version.worker_id is None]
    if not candidates:
        raise AttendanceRuleError(
            f"No existe tarifa provisional vigente para {target_date.isoformat()}."
        )
    selected = max(candidates, key=lambda version: (version.effective_from, version.version_id))
    return EffectiveProvisionalRate(
        version_id=selected.version_id,
        effective_from=selected.effective_from,
        amount_clp=selected.amount_clp,
        source=INDIVIDUAL_RATE if selected.worker_id is not None else GLOBAL_RATE,
    )


def project_day(
    worker_id: int,
    operational_date: date,
    sessions: Iterable[AttendanceSessionProjection],
    rate_versions: Iterable[ProvisionalRateVersion],
) -> AttendanceDayProjection:
    source_sessions = tuple(
        sorted(
            sessions,
            key=lambda item: (
                item.entry_time or datetime.min.replace(tzinfo=timezone.utc),
                item.session_id,
            ),
        )
    )
    if any(item.worker_id != worker_id for item in source_sessions):
        raise AttendanceRuleError("La proyección no puede mezclar trabajadores.")
    if any(item.operational_date != operational_date for item in source_sessions):
        raise AttendanceRuleError("La proyección diaria no puede mezclar fechas operacionales.")

    active_shift_codes = {
        item.shift_code for item in source_sessions if item.has_activity
    }
    unsupported = active_shift_codes.difference(PAYABLE_SHIFT_ORDER)
    if unsupported:
        codes = ", ".join(sorted(unsupported))
        raise AttendanceRuleError(f"Turno factual sin regla pagable aprobada: {codes}.")
    payable_shift_codes = tuple(
        code for code in PAYABLE_SHIFT_ORDER if code in active_shift_codes
    )
    effective_rate = resolve_effective_rate(
        operational_date,
        worker_id,
        rate_versions,
    )
    payable_shifts = len(payable_shift_codes)
    return AttendanceDayProjection(
        worker_id=worker_id,
        operational_date=operational_date,
        sessions=source_sessions,
        has_activity=any(item.has_activity for item in source_sessions),
        has_completed_session=any(item.is_closed_valid for item in source_sessions),
        has_incomplete_session=any(item.is_incomplete for item in source_sessions),
        payable_shift_codes=payable_shift_codes,
        payable_shifts=payable_shifts,
        is_double_shift=payable_shifts == 2,
        incident_count=sum(item.incident_count for item in source_sessions),
        effective_rate=effective_rate,
        provisional_total_clp=payable_shifts * effective_rate.amount_clp,
    )


def project_period(
    worker_id: int,
    session_facts: Iterable[AttendanceSessionFacts],
    rate_versions: Iterable[ProvisionalRateVersion],
    *,
    shift_references: Mapping[str, ShiftReference] | None = None,
) -> AttendancePeriodProjection:
    projected_sessions = [
        project_session(facts, shift_references=shift_references)
        for facts in session_facts
    ]
    if any(item.worker_id != worker_id for item in projected_sessions):
        raise AttendanceRuleError("La proyección no puede mezclar trabajadores.")

    rates = tuple(rate_versions)
    sessions_by_date: dict[date, list[AttendanceSessionProjection]] = {}
    for session in projected_sessions:
        sessions_by_date.setdefault(session.operational_date, []).append(session)
    days = tuple(
        project_day(worker_id, target_date, sessions_by_date[target_date], rates)
        for target_date in sorted(sessions_by_date)
    )
    return AttendancePeriodProjection(
        worker_id=worker_id,
        days=days,
        activity_days=sum(day.has_activity for day in days),
        completed_worked_days=sum(day.has_completed_session for day in days),
        incomplete_sessions=sum(
            session.is_incomplete for day in days for session in day.sessions
        ),
        payable_shifts=sum(day.payable_shifts for day in days),
        double_shift_days=sum(day.is_double_shift for day in days),
        incident_count=sum(day.incident_count for day in days),
        provisional_total_clp=sum(day.provisional_total_clp for day in days),
    )
