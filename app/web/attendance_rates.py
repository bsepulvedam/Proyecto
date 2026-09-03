from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.core.time import local_datetime, operational_date, utc_now
from app.database.session import get_db
from app.models.identity import Trabajador, Usuario
from app.schemas.attendance import AttendanceRateForm
from app.services.attendance_rate_service import (
    AttendanceRateConflict,
    AttendanceRateError,
    create_rate_version,
    effective_rate_for_worker,
    list_global_rate_versions,
    list_worker_rate_versions,
    list_workers_for_rate_admin,
)
from app.services.attendance_rules_service import MissingProvisionalRateError


router = APIRouter(prefix="/admin/asistencia/tarifas", tags=["tarifas-asistencia"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
templates.env.filters["local_datetime"] = lambda value: (
    local_datetime(value).strftime("%d/%m/%Y %H:%M") if value else "â€”"
)
templates.env.filters["clp"] = lambda value: f"${value:,.0f}".replace(",", ".")


async def _form_payload(request: Request) -> dict[str, object]:
    raw = await request.form()
    payload: dict[str, object] = {}
    for key, value in raw.multi_items():
        if key == "csrf_token":
            continue
        if key in payload:
            raise ValueError("Campos repetidos")
        payload[key] = value
    return payload


def _context(**values):
    context = {
        "active_page": "admin_attendance_rates",
        "page_title": "Tarifas provisionales de asistencia",
        "page_eyebrow": "Administración · Solo ADMIN",
    }
    context.update(values)
    return context


def _global_response(
    request: Request,
    db: Session,
    *,
    error: str | None = None,
    form_values: dict[str, object] | None = None,
    notification: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    return templates.TemplateResponse(
        request=request,
        name="attendance/rates_index.html",
        context=_context(
            history=list_global_rate_versions(db),
            workers=list_workers_for_rate_admin(db),
            error=error,
            form_values=form_values or {},
            notification=notification,
        ),
        status_code=status_code,
    )


def _worker_response(
    request: Request,
    db: Session,
    worker_id: int,
    *,
    error: str | None = None,
    form_values: dict[str, object] | None = None,
    notification: str | None = None,
    status_code: int = status.HTTP_200_OK,
):
    worker = db.get(Trabajador, worker_id)
    if worker is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    today = operational_date(utc_now())
    try:
        effective_rate = effective_rate_for_worker(db, worker_id, today)
    except MissingProvisionalRateError:
        effective_rate = None
    return templates.TemplateResponse(
        request=request,
        name="attendance/rates_worker.html",
        context=_context(
            worker=worker,
            effective_rate=effective_rate,
            history=list_worker_rate_versions(db, worker_id),
            today=today,
            error=error,
            form_values=form_values or {},
            notification=notification,
            page_title="Tarifa individual de asistencia",
        ),
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse, name="admin_attendance_rates")
def rates_index(
    request: Request,
    resultado: str | None = None,
    db: Session = Depends(get_db),
):
    notification = (
        "Nueva tarifa global creada correctamente." if resultado == "global" else None
    )
    return _global_response(request, db, notification=notification)


@router.post("/global", response_class=HTMLResponse, name="admin_attendance_rate_global_create")
async def create_global_rate(
    request: Request,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ADMIN_ACCESS")),
):
    payload: dict[str, object] = {}
    try:
        payload = await _form_payload(request)
        form = AttendanceRateForm.model_validate(payload)
        create_rate_version(
            db,
            effective_from=form.vigente_desde,
            amount_clp=form.monto_clp,
            actor=actor,
        )
    except AttendanceRateConflict as exc:
        return _global_response(
            request,
            db,
            error=str(exc),
            form_values=payload,
            status_code=status.HTTP_409_CONFLICT,
        )
    except (AttendanceRateError, ValidationError, ValueError) as exc:
        message = str(exc) if isinstance(exc, AttendanceRateError) else "Revisa monto, vigencia y confirmación."
        return _global_response(
            request,
            db,
            error=message,
            form_values=payload,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return RedirectResponse(
        f"/admin/asistencia/tarifas?{urlencode({'resultado': 'global'})}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/trabajadores/{worker_id}",
    response_class=HTMLResponse,
    name="admin_attendance_rate_worker",
)
def worker_rate(
    request: Request,
    worker_id: int,
    resultado: str | None = None,
    db: Session = Depends(get_db),
):
    notification = (
        "Nueva tarifa individual creada correctamente."
        if resultado == "individual"
        else None
    )
    return _worker_response(request, db, worker_id, notification=notification)


@router.post(
    "/trabajadores/{worker_id}",
    response_class=HTMLResponse,
    name="admin_attendance_rate_worker_create",
)
async def create_worker_rate(
    request: Request,
    worker_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ADMIN_ACCESS")),
):
    payload: dict[str, object] = {}
    try:
        payload = await _form_payload(request)
        form = AttendanceRateForm.model_validate(payload)
        create_rate_version(
            db,
            effective_from=form.vigente_desde,
            amount_clp=form.monto_clp,
            actor=actor,
            worker_id=worker_id,
        )
    except AttendanceRateConflict as exc:
        return _worker_response(
            request,
            db,
            worker_id,
            error=str(exc),
            form_values=payload,
            status_code=status.HTTP_409_CONFLICT,
        )
    except (AttendanceRateError, ValidationError, ValueError) as exc:
        message = str(exc) if isinstance(exc, AttendanceRateError) else "Revisa monto, vigencia y confirmación."
        return _worker_response(
            request,
            db,
            worker_id,
            error=message,
            form_values=payload,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return RedirectResponse(
        f"/admin/asistencia/tarifas/trabajadores/{worker_id}?{urlencode({'resultado': 'individual'})}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
