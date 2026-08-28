from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.time import local_datetime
from app.schemas.identity import AdminUserData, WorkerData
from app.services.auth_service import IdentityError
from app.services.identity_admin_service import (
    available_workers, create_managed_user, get_user, get_worker, list_users,
    list_workers, reset_password, save_worker, set_user_active,
)
from app.services.inventario_catalogo_service import listar_empresas


router = APIRouter(prefix="/admin", tags=["administracion-identidad"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
templates.env.filters["local_datetime"] = lambda value: local_datetime(value).strftime("%d/%m/%Y %H:%M") if value else "—"


async def _form(request: Request) -> dict[str, list[str]]:
    return parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True, max_num_fields=100)


def _value(form, name):
    return form.get(name, [""])[0].strip()


def _context(**values):
    context = {"active_page": "admin", "page_title": "Administración", "page_eyebrow": "Identidad de plataforma"}
    context.update(values)
    return context


def _worker_data(form) -> WorkerData:
    return WorkerData(nombres=_value(form, "nombres"), apellidos=_value(form, "apellidos"),
        empresa_id=int(_value(form, "empresa_id")) if _value(form, "empresa_id") else None,
        codigo_interno=_value(form, "codigo_interno") or None, activo="activo" in form)


@router.get("/trabajadores", response_class=HTMLResponse, name="admin_workers")
def workers(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="admin/workers.html", context=_context(
        workers=list_workers(db), active_page="admin_workers", page_title="Trabajadores"))


@router.get("/trabajadores/nuevo", response_class=HTMLResponse, name="admin_new_worker")
def new_worker(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="admin/worker_form.html", context=_context(
        worker=None, empresas=listar_empresas(db), error=None, active_page="admin_workers", page_title="Nuevo trabajador"))


@router.post("/trabajadores", response_class=HTMLResponse, name="admin_create_worker")
async def create_worker(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    try:
        worker = save_worker(db, _worker_data(form))
    except (ValueError, ValidationError, IdentityError) as exc:
        return templates.TemplateResponse(request=request, name="admin/worker_form.html", context=_context(
            worker=None, empresas=listar_empresas(db), error=str(exc), form=form,
            active_page="admin_workers", page_title="Nuevo trabajador"), status_code=422)
    return RedirectResponse(f"/admin/trabajadores/{worker.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/trabajadores/{worker_id}", response_class=HTMLResponse, name="admin_worker_detail")
def worker_detail(request: Request, worker_id: int, db: Session = Depends(get_db)):
    worker = get_worker(db, worker_id)
    if worker is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    return templates.TemplateResponse(request=request, name="admin/worker_form.html", context=_context(
        worker=worker, empresas=listar_empresas(db), error=None, active_page="admin_workers", page_title="Editar trabajador"))


@router.post("/trabajadores/{worker_id}", response_class=HTMLResponse, name="admin_update_worker")
async def update_worker(request: Request, worker_id: int, db: Session = Depends(get_db)):
    worker = get_worker(db, worker_id)
    if worker is None:
        return HTMLResponse("Trabajador no encontrado", status_code=404)
    form = await _form(request)
    try:
        save_worker(db, _worker_data(form), worker)
    except (ValueError, ValidationError, IdentityError) as exc:
        return templates.TemplateResponse(request=request, name="admin/worker_form.html", context=_context(
            worker=worker, empresas=listar_empresas(db), error=str(exc), form=form,
            active_page="admin_workers", page_title="Editar trabajador"), status_code=422)
    return RedirectResponse(f"/admin/trabajadores/{worker_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/usuarios", response_class=HTMLResponse, name="admin_users")
def users(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="admin/users.html", context=_context(
        users=list_users(db), active_page="admin_users", page_title="Usuarios"))


@router.get("/usuarios/nuevo", response_class=HTMLResponse, name="admin_new_user")
def new_user(request: Request, trabajador_id: int | None = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="admin/user_form.html", context=_context(
        workers=available_workers(db, trabajador_id), roles=("TRABAJADOR", "JEFATURA", "ADMIN"), selected_worker=trabajador_id,
        error=None, active_page="admin_users", page_title="Nuevo usuario"))


@router.post("/usuarios", response_class=HTMLResponse, name="admin_create_user")
async def create_user(request: Request, db: Session = Depends(get_db)):
    form = await _form(request)
    try:
        data = AdminUserData(username=_value(form, "username"),
            trabajador_id=int(_value(form, "trabajador_id")) if _value(form, "trabajador_id") else None,
            rol=_value(form, "rol"), activo="activo" in form)
        user, temporary_password = create_managed_user(db, data)
    except (ValueError, ValidationError, IdentityError) as exc:
        return templates.TemplateResponse(request=request, name="admin/user_form.html", context=_context(
            workers=available_workers(db), roles=("TRABAJADOR", "JEFATURA", "ADMIN"), selected_worker=None,
            error=str(exc), form=form, active_page="admin_users", page_title="Nuevo usuario"), status_code=422)
    return templates.TemplateResponse(request=request, name="admin/temporary_password.html", context=_context(
        user=user, temporary_password=temporary_password, action="Cuenta creada",
        active_page="admin_users", page_title="Credencial temporal"), status_code=201)


@router.post("/usuarios/{user_id}/estado", name="admin_toggle_user")
async def toggle_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if user is None:
        return HTMLResponse("Usuario no encontrado", status_code=404)
    form = await _form(request)
    try:
        set_user_active(db, user, _value(form, "activo") == "1")
    except IdentityError as exc:
        return templates.TemplateResponse(request=request, name="admin/users.html", context=_context(
            users=list_users(db), error=str(exc), active_page="admin_users", page_title="Usuarios"), status_code=422)
    return RedirectResponse("/admin/usuarios", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/usuarios/{user_id}/restablecer-password", response_class=HTMLResponse, name="admin_reset_password")
def reset_user_password(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if user is None:
        return HTMLResponse("Usuario no encontrado", status_code=404)
    temporary_password = reset_password(db, user)
    return templates.TemplateResponse(request=request, name="admin/temporary_password.html", context=_context(
        user=user, temporary_password=temporary_password, action="Contraseña restablecida",
        active_page="admin_users", page_title="Credencial temporal"))
