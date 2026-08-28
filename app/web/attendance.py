from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import require_active_worker
from app.database.session import get_db
from app.models.identity import Trabajador
from app.services.attendance_service import JUSTIFICATION_TYPES, calendar_month, create_justification, get_justification, justification_file_path, list_justifications, list_shifts
from app.services.auth_service import IdentityError

router = APIRouter(prefix="/mi-asistencia", tags=["mi-asistencia"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def context(**values):
    data = {"active_page": "my_attendance", "page_title": "Mi asistencia", "page_eyebrow": "Portal del trabajador"}; data.update(values); return data


@router.get("", response_class=HTMLResponse, name="my_attendance")
def my_attendance(request: Request, year: int | None = None, month: int | None = None, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    today = date.today(); year, month = year or today.year, month or today.month
    if month < 1 or month > 12 or year < 2000 or year > 2200: return HTMLResponse("Mes no válido", status_code=422)
    weeks, entries = calendar_month(db, worker.id, year, month)
    previous = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1); following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return templates.TemplateResponse(request=request, name="attendance/calendar.html", context=context(worker=worker, weeks=weeks, entries=entries, year=year, month=month, previous=previous, following=following, active_page="attendance_days", page_title="Días trabajados"))


@router.get("/registrar", response_class=HTMLResponse, name="attendance_register")
def register(request: Request, db: Session = Depends(get_db), worker: Trabajador = Depends(require_active_worker)):
    return templates.TemplateResponse(request=request, name="attendance/register.html", context=context(worker=worker, shifts=list_shifts(db), active_page="attendance_register", page_title="Registrar asistencia"))


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
