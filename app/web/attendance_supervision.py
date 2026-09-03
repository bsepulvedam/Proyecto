from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.core.time import local_datetime
from app.database.session import get_db
from app.models.identity import Usuario
from app.schemas.attendance import AdministrativeExitForm, IncidentDecisionForm
from app.services.attendance_admin_service import (
    AttendanceAdministrationError,
    complete_administrative_exit,
    decide_attendance_incident,
)
from app.services.attendance_export_service import (
    XLSX_MEDIA_TYPE,
    build_combined_attendance_xlsx,
    combined_export_filename,
    export_worker_attendance,
    individual_export_filename,
)
from app.services.attendance_supervision_service import (
    AttendanceSupervisionError,
    SupervisionPeriod,
    get_worker_day_supervision,
    get_worker_supervision,
    incident_location,
    list_worker_supervision,
    period_dates,
    session_location,
    supervision_period,
)


router = APIRouter(prefix="/asistencia/supervision", tags=["supervision-asistencia"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
templates.env.filters["local_datetime"] = lambda value: (
    local_datetime(value).strftime("%d/%m/%Y %H:%M") if value else "—"
)
templates.env.filters["clp"] = lambda value: (
    f"${value:,.0f}".replace(",", ".") if value is not None else "Sin tarifa configurada para la fecha"
)


def _context(**values):
    context = {
        "active_page": "attendance_supervision",
        "page_title": "Supervisión de asistencia",
        "page_eyebrow": "Asistencia · ADMIN/JEFATURA",
    }
    context.update(values)
    return context


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


def _day_url(worker_id: int, target_date: date, *, result: str | None = None) -> str:
    url = f"/asistencia/supervision/trabajadores/{worker_id}/dias/{target_date.isoformat()}"
    return f"{url}?{urlencode({'resultado': result})}" if result else url


def _day_response(
    request: Request,
    db: Session,
    worker_id: int,
    target_date: date,
    *,
    notification: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
):
    result = get_worker_day_supervision(db, worker_id, target_date)
    if result is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    supervision, day = result
    return templates.TemplateResponse(
        request=request,
        name="attendance/supervision_day.html",
        context=_context(
            supervision=supervision,
            day=day,
            target_date=target_date,
            notification=notification,
            page_title="Detalle diario de asistencia",
        ),
        status_code=status_code,
    )


@router.get("", response_class=HTMLResponse, name="attendance_supervision")
def supervision_index(
    request: Request,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    try:
        period = supervision_period(fecha_desde, fecha_hasta)
        listing = list_worker_supervision(db, period, query=q, page=page)
    except AttendanceSupervisionError as exc:
        fallback = supervision_period(None, None)
        listing = list_worker_supervision(db, fallback, query=None)
        return templates.TemplateResponse(
            request=request,
            name="attendance/supervision_index.html",
            context=_context(
                listing=listing,
                error=str(exc),
                input_start=fecha_desde or "",
                input_end=fecha_hasta or "",
                input_query=q or "",
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return templates.TemplateResponse(
        request=request,
        name="attendance/supervision_index.html",
        context=_context(
            listing=listing,
            error=None,
            input_start=period.start.isoformat(),
            input_end=period.end.isoformat(),
            input_query=listing.query,
        ),
    )


@router.get(
    "/trabajadores/{worker_id}",
    response_class=HTMLResponse,
    name="attendance_supervision_worker",
)
def supervision_worker(
    request: Request,
    worker_id: int,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        period = supervision_period(fecha_desde, fecha_hasta)
    except AttendanceSupervisionError as exc:
        return HTMLResponse(str(exc), status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    result = get_worker_supervision(db, worker_id, period)
    if result is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="attendance/supervision_worker.html",
        context=_context(
            supervision=result,
            calendar_dates=period_dates(period),
            page_title="Asistencia individual",
        ),
    )


@router.get("/exportar", name="attendance_supervision_export")
def supervision_export(
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        period = supervision_period(fecha_desde, fecha_hasta)
        content = build_combined_attendance_xlsx(db, period, query=q)
    except AttendanceSupervisionError as exc:
        return HTMLResponse(str(exc), status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    filename = combined_export_filename(period)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/trabajadores/{worker_id}/exportar",
    name="attendance_supervision_worker_export",
)
def supervision_worker_export(
    worker_id: int,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        period = supervision_period(fecha_desde, fecha_hasta)
    except AttendanceSupervisionError as exc:
        return HTMLResponse(str(exc), status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    content = export_worker_attendance(db, worker_id, period)
    if content is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    filename = individual_export_filename(worker_id, period)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/trabajadores/{worker_id}/dias/{fecha}",
    response_class=HTMLResponse,
    name="attendance_supervision_day",
)
def supervision_day(
    request: Request,
    worker_id: int,
    fecha: date,
    resultado: str | None = None,
    db: Session = Depends(get_db),
):
    notification = None
    if resultado == "salida":
        notification = {
            "level": "success",
            "text": "SALIDA administrativa registrada correctamente.",
        }
    elif resultado == "incidencia":
        notification = {
            "level": "success",
            "text": "Decisión de incidencia registrada correctamente.",
        }
    return _day_response(
        request,
        db,
        worker_id,
        fecha,
        notification=notification,
    )


@router.post(
    "/sesiones/{session_id}/completar-salida",
    name="attendance_supervision_complete_exit",
)
async def supervision_complete_exit(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ASISTENCIA_SUPERVISAR")),
):
    location = session_location(db, session_id)
    if location is None:
        return HTMLResponse("La sesión no existe.", status_code=404)
    worker_id, target_date = location
    try:
        form = AdministrativeExitForm.model_validate(await _form_payload(request))
    except (ValidationError, ValueError):
        return _day_response(
            request,
            db,
            worker_id,
            target_date,
            notification={
                "level": "danger",
                "text": "Debes indicar una fecha/hora válida y un motivo.",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        complete_administrative_exit(
            db,
            session_id,
            form.salida_at,
            actor,
            form.motivo,
        )
    except AttendanceAdministrationError as exc:
        message = str(exc)
        if "ya no está disponible" in message:
            message = "La sesión ya fue completada por otro usuario."
        return _day_response(
            request,
            db,
            worker_id,
            target_date,
            notification={"level": "danger", "text": message},
            status_code=status.HTTP_409_CONFLICT,
        )
    return RedirectResponse(
        _day_url(worker_id, target_date, result="salida"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/incidencias/{incident_id}/decision",
    name="attendance_supervision_incident_decision",
)
async def supervision_incident_decision(
    request: Request,
    incident_id: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(require_permission("ASISTENCIA_SUPERVISAR")),
):
    location = incident_location(db, incident_id)
    if location is None:
        return HTMLResponse("La incidencia no existe.", status_code=404)
    worker_id, target_date = location
    try:
        form = IncidentDecisionForm.model_validate(await _form_payload(request))
    except (ValidationError, ValueError):
        return _day_response(
            request,
            db,
            worker_id,
            target_date,
            notification={
                "level": "danger",
                "text": "La decisión debe ser APROBADA o RECHAZADA.",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        decide_attendance_incident(
            db,
            incident_id,
            form.decision,
            actor,
            comment=form.comentario,
        )
    except AttendanceAdministrationError as exc:
        message = str(exc)
        if "decisión final" in message:
            message = "La incidencia ya fue resuelta por otro usuario."
        return _day_response(
            request,
            db,
            worker_id,
            target_date,
            notification={"level": "danger", "text": message},
            status_code=status.HTTP_409_CONFLICT,
        )
    return RedirectResponse(
        _day_url(worker_id, target_date, result="incidencia"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
