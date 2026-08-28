from types import SimpleNamespace
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import auth_enforced
from app.database.session import get_db
from app.models.identity import Usuario
from app.services.auth_service import CSRF_COOKIE, SESSION_COOKIE, csrf_is_valid, resolve_session, user_has_permission


DEVELOPMENT_IDENTITY = SimpleNamespace(username="Modo desarrollo", primary_role="DESARROLLO", role_codes={"ADMIN"})
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _unauthenticated(request: Request) -> None:
    if request.url.path.startswith("/api/"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida")
    raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario | None:
    resolved = resolve_session(db, request.cookies.get(SESSION_COOKIE))
    if resolved is None:
        return None
    user, session = resolved
    request.state.current_user = user
    request.state.user_session = session
    return user


async def require_authenticated(request: Request, db: Session = Depends(get_db)) -> Usuario:
    user = await get_current_user(request, db)
    if user is None:
        _unauthenticated(request)
    return user


def require_role(*allowed_roles: str):
    async def dependency(user: Usuario = Depends(require_authenticated)) -> Usuario:
        if not user.role_codes.intersection({role.upper() for role in allowed_roles}):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        return user
    return dependency


def require_permission(permission: str):
    async def dependency(user: Usuario = Depends(require_authenticated)) -> Usuario:
        if not user_has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
        return user
    return dependency


async def _validate_csrf(request: Request) -> None:
    token = request.headers.get("x-csrf-token")
    if not token:
        form = parse_qs((await request.body()).decode("utf-8"), keep_blank_values=True)
        token = form.get("csrf_token", [None])[0]
    if not csrf_is_valid(request.state.user_session, token) or token != request.cookies.get(CSRF_COOKIE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido")


async def require_session_csrf(request: Request, db: Session = Depends(get_db)) -> Usuario:
    user = await require_authenticated(request, db)
    if request.method not in SAFE_METHODS:
        await _validate_csrf(request)
    return user


async def require_platform_access(request: Request, db: Session = Depends(get_db)):
    if not auth_enforced():
        request.state.current_user = DEVELOPMENT_IDENTITY
        return DEVELOPMENT_IDENTITY
    user = await require_authenticated(request, db)
    if user.debe_cambiar_password and request.url.path not in {"/cambiar-password", "/logout"}:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debes cambiar tu contraseña antes de continuar")
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/cambiar-password"})
    if request.method not in SAFE_METHODS:
        await _validate_csrf(request)
    return user


def require_module(permission: str):
    async def dependency(request: Request, user=Depends(require_platform_access)):
        if not auth_enforced() or user_has_permission(user, permission):
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return dependency
