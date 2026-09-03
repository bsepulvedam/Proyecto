from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import TarifaProvisionalAsistencia
from app.models.identity import Trabajador, Usuario
from app.services.attendance_rules_service import (
    EffectiveProvisionalRate,
    ProvisionalRateVersion,
    resolve_effective_rate,
)


class AttendanceRateError(ValueError):
    pass


def _exact_positive_clp(value: int | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise AttendanceRateError("La tarifa debe ser un monto CLP entero positivo.")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AttendanceRateError(
            "La tarifa debe ser un monto CLP entero positivo."
        ) from exc
    if amount <= 0 or amount != amount.to_integral_value() or amount > 999_999_999_999:
        raise AttendanceRateError("La tarifa debe ser un monto CLP entero positivo.")
    return amount


def _effective_date(value: date) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise AttendanceRateError(
            "La vigencia debe ser una fecha operacional válida."
        )
    return value


def create_rate_version(
    db: Session,
    *,
    effective_from: date,
    amount_clp: int | Decimal,
    actor: Usuario,
    worker_id: int | None = None,
) -> TarifaProvisionalAsistencia:
    try:
        amount = _exact_positive_clp(amount_clp)
        normalized_effective_from = _effective_date(effective_from)
        if worker_id is not None and db.get(Trabajador, worker_id) is None:
            raise AttendanceRateError("El trabajador no existe.")
        version = TarifaProvisionalAsistencia(
            trabajador_id=worker_id,
            valor_clp=amount,
            vigente_desde=normalized_effective_from,
            origen="ADMIN",
            creado_por_id=actor.id,
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version
    except AttendanceRateError:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        scope = "global" if worker_id is None else "del trabajador"
        raise AttendanceRateError(
            f"Ya existe una tarifa {scope} con esa fecha de vigencia."
        ) from exc
    except Exception:
        db.rollback()
        raise


def rate_versions_for_worker(
    db: Session,
    worker_id: int,
    *,
    through_date: date,
) -> tuple[ProvisionalRateVersion, ...]:
    rows = db.scalars(
        select(TarifaProvisionalAsistencia)
        .where(
            TarifaProvisionalAsistencia.vigente_desde <= through_date,
            or_(
                TarifaProvisionalAsistencia.trabajador_id.is_(None),
                TarifaProvisionalAsistencia.trabajador_id == worker_id,
            ),
        )
        .order_by(
            TarifaProvisionalAsistencia.vigente_desde,
            TarifaProvisionalAsistencia.id,
        )
    ).all()
    return tuple(
        ProvisionalRateVersion(
            version_id=row.id,
            effective_from=row.vigente_desde,
            amount_clp=int(row.valor_clp),
            worker_id=row.trabajador_id,
        )
        for row in rows
    )


def rate_versions_for_workers(
    db: Session,
    worker_ids: list[int] | tuple[int, ...],
    *,
    through_date: date,
) -> tuple[ProvisionalRateVersion, ...]:
    """Load global and worker-specific versions in one bounded query."""
    normalized_ids = tuple(sorted(set(worker_ids)))
    if not normalized_ids:
        return ()
    rows = db.scalars(
        select(TarifaProvisionalAsistencia)
        .where(
            TarifaProvisionalAsistencia.vigente_desde <= through_date,
            or_(
                TarifaProvisionalAsistencia.trabajador_id.is_(None),
                TarifaProvisionalAsistencia.trabajador_id.in_(normalized_ids),
            ),
        )
        .order_by(
            TarifaProvisionalAsistencia.vigente_desde,
            TarifaProvisionalAsistencia.id,
        )
    ).all()
    return tuple(
        ProvisionalRateVersion(
            version_id=row.id,
            effective_from=row.vigente_desde,
            amount_clp=int(row.valor_clp),
            worker_id=row.trabajador_id,
        )
        for row in rows
    )


def effective_rate_for_worker(
    db: Session,
    worker_id: int,
    target_date: date,
) -> EffectiveProvisionalRate:
    return resolve_effective_rate(
        target_date,
        worker_id,
        rate_versions_for_worker(db, worker_id, through_date=target_date),
    )
