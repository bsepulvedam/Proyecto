from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import require_active_worker, require_role
from app.core.time import local_datetime, operational_date, utc_now
from app.database.session import get_db
from app.models.identity import Trabajador
from app.schemas.attendance import AttendanceMarkForm
from app.services.attendance_marking_service import (
    AttendanceMarkError,
    get_attendance_mark_feedback,
    get_attendance_registration_state,
    register_attendance_mark,
)
from app.services.attendance_calendar_service import calendar_month
from app.services.attendance_service import JUSTIFICATION_TYPES, create_justification, get_justification, justification_file_path, list_justifications, list_shifts
from app.services.auth_service import IdentityError

router = APIRouter(prefix="/mi-asistencia", tags=["mi-asistencia"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def context(**values):
    data = {"active_page": "my_attendance", "page_title": "Mi asistencia", "page_eyebrow": "Portal del trabajador"}; data.update(values); return data


def _mark_result_messages(
    result: str | None,
    geofence: str | None,
    accuracy: str | None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if result == "ENTRADA":
        messages.append({"level": "success", "text": "Entrada registrada correctamente."})
    elif result == "SALIDA":
        messages.append({"level": "success", "text": "Salida registrada correctamente."})
    else:
        return messages
    if geofence == "FUERA_RANGO":
        messages.append({"level": "warning", "text": "El marcaje fue registrado fuera del rango permitido y quedó pendiente de revisión."})
    elif geofence == "SIN_ZONA_CONFIGURADA":
        messages.append({"level": "info", "text": "El marcaje fue registrado, pero no existen zonas configuradas para evaluarlo."})
    if accuracy == "BAJA_PRECISION":
        messages.append({"level": "warning", "text": "El marcaje fue registrado con GPS de baja precisión y quedó pendiente de revisión."})
    return messages


def _registration_context(
    db: Session,
    worker: Trabajador,
    *,
    messages: list[dict[str, str]] | None = None,
    error: str | None = None,
    selected_shift_id: int | None = None,
):
    state = get_attendance_registration_state(db, worker)
    entry_time = local_datetime(state.entry_time) if state.entry_time else None
    return context(
        worker=worker,
        shifts=list_shifts(db),
        state=state,
        entry_time=entry_time,
        messages=messages or [],
        error=error,
        selected_shift_id=selected_shift_id,
        active_page="attendance_register",
        page_title="Registrar asistencia",
    )


@router.get("", response_class=HTMLResponse, name="my_attendance")
def my_attendance(request: Request, year: int | None = None, month: int | None = None, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    today = operational_date(utc_now()); year, month = year or today.year, month or today.month
    if month < 1 or month > 12 or year < 2000 or year > 2200: return HTMLResponse("Mes no válido", status_code=422)
    weeks, days = calendar_month(db, worker.id, year, month, today=today)
    previous = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1); following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return templates.TemplateResponse(request=request, name="attendance/calendar.html", context=context(worker=worker, weeks=weeks, days=days, year=year, month=month, previous=previous, following=following, active_page="attendance_days", page_title="Días trabajados"))


@router.get("/registrar", response_class=HTMLResponse, name="attendance_register")
def register(
    request: Request,
    db: Session = Depends(get_db),
    worker: Trabajador = Depends(require_active_worker),
    _user=Depends(require_role("TRABAJADOR")),
):
    return templates.TemplateResponse(
        request=request,
        name="attendance/register.html",
        context=_registration_context(db, worker),
    )


@router.post("/registrar", name="attendance_register_submit")
async def register_submit(
    request: Request,
    db: Session = Depends(get_db),
    worker: Trabajador = Depends(require_active_worker),
    _user=Depends(require_role("TRABAJADOR")),
):
    raw_form = await request.form()
    payload: dict[str, object] = {}
    duplicate_field = False
    for key, value in raw_form.multi_items():
        if key == "csrf_token":
            continue
        if key in payload:
            duplicate_field = True
        payload[key] = value
    try:
        if duplicate_field:
            raise ValueError("Campos repetidos")
        form = AttendanceMarkForm.model_validate(payload)
    except (ValidationError, ValueError):
        return templates.TemplateResponse(
            request=request,
            name="attendance/register.html",
            context=_registration_context(
                db,
                worker,
                error="No fue posible validar el turno o la ubicación. Obtén tu ubicación nuevamente e inténtalo otra vez.",
            ),
            status_code=422,
        )

    try:
        mark = register_attendance_mark(
            db,
            worker,
            form.tipo,
            form.gps_evidence(),
            shift_id=form.turno_id,
        )
        feedback = get_attendance_mark_feedback(db, mark)
    except AttendanceMarkError as exc:
        return templates.TemplateResponse(
            request=request,
            name="attendance/register.html",
            context=_registration_context(
                db,
                worker,
                error=str(exc),
                selected_shift_id=form.turno_id,
            ),
            status_code=409,
        )

    return templates.TemplateResponse(
        request=request,
        name="attendance/register.html",
        context=_registration_context(
            db,
            worker,
            messages=_mark_result_messages(
                feedback.mark_type,
                feedback.geofence_status,
                feedback.accuracy_status,
            ),
        ),
    )


@router.get("/justificaciones", response_class=HTMLResponse, name="my_justifications")
def justifications(request: Request, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    return templates.TemplateResponse(request=request, name="attendance/justifications.html", context=context(items=list_justifications(db, worker.id), active_page="attendance_justifications", page_title="Justificaciones"))


@router.get("/justificar", response_class=HTMLResponse, name="new_justification")
def justification_form(request: Request, worker: Trabajador = Depends(require_active_worker)):
    return templates.TemplateResponse(request=request, name="attendance/justify.html", context=context(types=JUSTIFICATION_TYPES, error=None, active_page="attendance_justifications", page_title="Justificar inasistencia"))


@router.post("/justificar", name="create_justification")
async def justification_create(request: Request, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    form = await request.form(); upload = form.get("archivo")
    try:
        await create_justification(db, worker, date.fromisoformat(str(form.get("fecha", ""))), str(form.get("tipo", "")), str(form.get("observacion", "")), upload)
    except (ValueError, IdentityError) as exc:
        return templates.TemplateResponse(request=request, name="attendance/justify.html", context=context(types=JUSTIFICATION_TYPES, error=str(exc), active_page="attendance_justifications", page_title="Justificar inasistencia"), status_code=422)
    return RedirectResponse("/mi-asistencia/justificaciones", status_code=303)


@router.get("/justificaciones/{item_id}/archivo", name="justification_file")
def justification_file(item_id: int, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    item = get_justification(db, worker.id, item_id)
    if item is None or not item.archivo_storage_key: return HTMLResponse("Archivo no encontrado", status_code=404)
    path = justification_file_path(item.archivo_storage_key)
    if not path.is_file(): return HTMLResponse("Archivo no disponible", status_code=404)
    return FileResponse(path, media_type=item.archivo_mime, filename=item.archivo_nombre_original)
