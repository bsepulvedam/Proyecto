import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import session_hours, session_secret
from app.core.time import utc_now
from app.models.identity import Rol, SesionUsuario, Usuario
from app.schemas.identity import UserCreate


SESSION_COOKIE = "boliklor_session"
CSRF_COOKIE = "boliklor_csrf"
LOGIN_CSRF_COOKIE = "boliklor_login_csrf"
ROLE_PERMISSIONS = {
    "ADMIN": {"*", "ADMIN_ACCESS", "INVENTARIO_ACCESS", "OT_ACCESS"},
    "JEFATURA": {"ASISTENCIA_SUPERVISAR"},
    "TRABAJADOR": {"ASISTENCIA_PROPIA"},
}
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
_DUMMY_HASH = _hasher.hash("Boliklor-dummy-password-not-used")


class IdentityError(ValueError):
    pass


@dataclass(frozen=True)
class SessionCredentials:
    session_token: str
    csrf_token: str
    expires_at: object


def normalize_username(username: str) -> str:
    return username.strip().casefold()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise IdentityError("La contraseña debe tener al menos 12 caracteres.")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _token_digest(token: str) -> str:
    return hmac.new(session_secret().encode(), token.encode(), hashlib.sha256).hexdigest()


def find_user(db: Session, username: str) -> Usuario | None:
    query = select(Usuario).options(selectinload(Usuario.roles), selectinload(Usuario.trabajador)).where(
        Usuario.username == normalize_username(username)
    )
    return db.scalar(query)


def authenticate_user(db: Session, username: str, password: str) -> Usuario | None:
    user = find_user(db, username)
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not user.activo or not valid:
        return None
    user.ultimo_acceso_at = utc_now()
    db.commit()
    return user


def create_user(db: Session, data: UserCreate, role_code: str) -> Usuario:
    role = db.scalar(select(Rol).where(Rol.codigo == role_code.upper(), Rol.activo.is_(True)))
    if role is None:
        raise IdentityError(f"El rol {role_code.upper()} no existe.")
    user = Usuario(username=normalize_username(data.username), password_hash=hash_password(data.password), roles=[role])
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise IdentityError("El username/email ya existe.") from exc


def create_session(db: Session, user: Usuario) -> SessionCredentials:
    session_token, csrf_token = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    expires_at = utc_now() + timedelta(hours=session_hours())
    db.add(SesionUsuario(usuario_id=user.id, token_hash=_token_digest(session_token),
        csrf_token_hash=_token_digest(csrf_token), expires_at=expires_at, last_seen_at=utc_now()))
    db.commit()
    return SessionCredentials(session_token, csrf_token, expires_at)


def resolve_session(db: Session, session_token: str | None) -> tuple[Usuario, SesionUsuario] | None:
    if not session_token:
        return None
    query = select(SesionUsuario).options(
        selectinload(SesionUsuario.usuario).selectinload(Usuario.roles),
        selectinload(SesionUsuario.usuario).selectinload(Usuario.trabajador),
    ).where(SesionUsuario.token_hash == _token_digest(session_token), SesionUsuario.revoked_at.is_(None))
    session = db.scalar(query)
    if session is None or not session.usuario.activo:
        return None
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utc_now():
        return None
    session.last_seen_at = utc_now()
    db.commit()
    return session.usuario, session


def csrf_is_valid(session: SesionUsuario, token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(session.csrf_token_hash, _token_digest(token))


def revoke_session(db: Session, session_token: str | None) -> None:
    if not session_token:
        return
    session = db.scalar(select(SesionUsuario).where(SesionUsuario.token_hash == _token_digest(session_token)))
    if session and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()


def user_has_permission(user: Usuario, permission: str) -> bool:
    permissions = set().union(*(ROLE_PERMISSIONS.get(code, set()) for code in user.role_codes))
    return "*" in permissions or permission in permissions
