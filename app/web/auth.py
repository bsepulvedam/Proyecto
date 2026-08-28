import hmac
import secrets
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import cookie_secure, session_hours
from app.core.security import require_authenticated, require_session_csrf
from app.database.session import get_db
from app.schemas.identity import LoginData, PasswordChangeData
from app.services.identity_admin_service import change_password
from app.services.auth_service import CSRF_COOKIE, LOGIN_CSRF_COOKIE, SESSION_COOKIE, authenticate_user, create_session, landing_path, resolve_session, revoke_session


router = APIRouter(tags=["autenticacion"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def _set_cookie(response, name: str, value: str, max_age: int):
    response.set_cookie(name, value, max_age=max_age, httponly=True, secure=cookie_secure(), samesite="lax", path="/")


def _login_page(request: Request, error: str | None = None, status_code: int = 200):
    token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request=request, name="auth/login.html", context={"csrf_token": token, "error": error}, status_code=status_code)
    _set_cookie(response, LOGIN_CSRF_COOKIE, token, 600)
    return response


@router.get("/login", response_class=HTMLResponse, name="login")
def login_form(request: Request, db: Session = Depends(get_db)):
    resolved = resolve_session(db, request.cookies.get(SESSION_COOKIE))
    if resolved:
        return RedirectResponse("/cambiar-password" if resolved[0].debe_cambiar_password else landing_path(resolved[0]), status_code=status.HTTP_303_SEE_OTHER)
    return _login_page(request)


@router.post("/login", response_class=HTMLResponse, name="login_submit")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    form_token = form.get("csrf_token", [""])[0]
    if not form_token or not hmac.compare_digest(form_token, request.cookies.get(LOGIN_CSRF_COOKIE, "")):
        return _login_page(request, "La sesión del formulario expiró. Intenta nuevamente.", 403)
    try:
        data = LoginData(username=form.get("username", [""])[0], password=form.get("password", [""])[0])
    except ValueError:
        return _login_page(request, "Usuario o contraseña incorrectos.", 401)
    user = authenticate_user(db, data.username, data.password)
    if user is None:
        return _login_page(request, "Usuario o contraseña incorrectos.", 401)
    credentials = create_session(db, user)
    response = RedirectResponse("/cambiar-password" if user.debe_cambiar_password else landing_path(user), status_code=status.HTTP_303_SEE_OTHER)
    max_age = session_hours() * 3600
    _set_cookie(response, SESSION_COOKIE, credentials.session_token, max_age)
    _set_cookie(response, CSRF_COOKIE, credentials.csrf_token, max_age)
    response.delete_cookie(LOGIN_CSRF_COOKIE, path="/")
    return response


@router.post("/logout", name="logout")
def logout(request: Request, db: Session = Depends(get_db), user=Depends(require_session_csrf)):
    revoke_session(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


def _change_page(request: Request, user, error: str | None = None, success: bool = False, status_code: int = 200):
    return templates.TemplateResponse(request=request, name="auth/change_password.html", context={
        "user": user, "error": error, "success": success,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
    }, status_code=status_code)


@router.get("/cambiar-password", response_class=HTMLResponse, name="change_password_form")
def change_password_form(request: Request, user=Depends(require_authenticated)):
    return _change_page(request, user)


@router.post("/cambiar-password", response_class=HTMLResponse, name="change_password_submit")
async def change_password_submit(request: Request, db: Session = Depends(get_db), user=Depends(require_session_csrf)):
    form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
    try:
        data = PasswordChangeData(
            current_password=form.get("current_password", [""])[0],
            new_password=form.get("new_password", [""])[0],
            confirmation=form.get("confirmation", [""])[0],
        )
        change_password(db, user, data.current_password, data.new_password, data.confirmation, request.state.user_session.id)
    except ValueError as exc:
        message = str(exc)
        return _change_page(request, user, message, status_code=422)
    return RedirectResponse(landing_path(user), status_code=status.HTTP_303_SEE_OTHER)
