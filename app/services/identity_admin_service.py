import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.time import utc_now
from app.models.empresa import Empresa
from app.models.identity import Rol, SesionUsuario, Trabajador, Usuario
from app.schemas.identity import AdminUserData, WorkerData
from app.services.auth_service import IdentityError, hash_password, normalize_username


def list_workers(db: Session) -> list[Trabajador]:
    return list(db.scalars(select(Trabajador).options(joinedload(Trabajador.empresa), joinedload(Trabajador.usuario).selectinload(Usuario.roles)).order_by(Trabajador.apellidos, Trabajador.nombres)).unique().all())


def get_worker(db: Session, worker_id: int) -> Trabajador | None:
    return db.scalar(select(Trabajador).options(joinedload(Trabajador.empresa), joinedload(Trabajador.usuario).selectinload(Usuario.roles)).where(Trabajador.id == worker_id))


def save_worker(db: Session, data: WorkerData, worker: Trabajador | None = None) -> Trabajador:
    if data.empresa_id is not None and db.get(Empresa, data.empresa_id) is None:
        raise IdentityError("Empresa no válida.")
    target = worker or Trabajador()
    for field, value in data.model_dump().items():
        setattr(target, field, value)
    try:
        db.add(target); db.commit(); db.refresh(target)
        return target
    except IntegrityError as exc:
        db.rollback()
        raise IdentityError("El código interno ya está asociado a otro trabajador.") from exc


def list_users(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).options(selectinload(Usuario.roles), joinedload(Usuario.trabajador)).order_by(Usuario.username)).unique().all())


def get_user(db: Session, user_id: int) -> Usuario | None:
    return db.scalar(select(Usuario).options(selectinload(Usuario.roles), joinedload(Usuario.trabajador)).where(Usuario.id == user_id))


def available_workers(db: Session, selected_id: int | None = None) -> list[Trabajador]:
    query = select(Trabajador).options(joinedload(Trabajador.usuario)).order_by(Trabajador.apellidos, Trabajador.nombres)
    return [worker for worker in db.scalars(query).unique().all() if worker.usuario is None or worker.id == selected_id]


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(18)


def create_managed_user(db: Session, data: AdminUserData) -> tuple[Usuario, str]:
    role = db.scalar(select(Rol).where(Rol.codigo == data.rol, Rol.activo.is_(True)))
    if role is None:
        raise IdentityError("Rol no válido.")
    worker = db.get(Trabajador, data.trabajador_id) if data.trabajador_id else None
    if data.trabajador_id and worker is None:
        raise IdentityError("Trabajador no válido.")
    if worker and worker.usuario_id is not None:
        raise IdentityError("El trabajador ya tiene un usuario asociado.")
    temporary_password = generate_temporary_password()
    user = Usuario(username=normalize_username(data.username), password_hash=hash_password(temporary_password),
        activo=data.activo, debe_cambiar_password=True, roles=[role])
    try:
        db.add(user); db.flush()
        if worker:
            worker.usuario_id = user.id
        db.commit(); db.refresh(user)
        return user, temporary_password
    except IntegrityError as exc:
        db.rollback()
        raise IdentityError("El username/email ya existe o el trabajador ya posee una cuenta.") from exc


def revoke_user_sessions(db: Session, user_id: int, except_session_id: int | None = None) -> None:
    query = select(SesionUsuario).where(SesionUsuario.usuario_id == user_id, SesionUsuario.revoked_at.is_(None))
    if except_session_id is not None:
        query = query.where(SesionUsuario.id != except_session_id)
    for session in db.scalars(query).all():
        session.revoked_at = utc_now()


def reset_password(db: Session, user: Usuario) -> str:
    temporary_password = generate_temporary_password()
    user.password_hash = hash_password(temporary_password)
    user.debe_cambiar_password = True
    revoke_user_sessions(db, user.id)
    db.commit()
    return temporary_password


def change_password(db: Session, user: Usuario, current_password: str, new_password: str, confirmation: str, current_session_id: int) -> None:
    from app.services.auth_service import verify_password
    if not verify_password(current_password, user.password_hash):
        raise IdentityError("La contraseña actual o temporal es incorrecta.")
    if new_password != confirmation:
        raise IdentityError("La confirmación no coincide con la nueva contraseña.")
    if verify_password(new_password, user.password_hash):
        raise IdentityError("La contraseña nueva debe ser diferente de la actual.")
    user.password_hash = hash_password(new_password)
    user.debe_cambiar_password = False
    revoke_user_sessions(db, user.id, current_session_id)
    db.commit()


def set_user_active(db: Session, user: Usuario, active: bool) -> None:
    if not active and "ADMIN" in user.role_codes:
        active_admins = db.scalar(select(func.count(func.distinct(Usuario.id))).select_from(Usuario).join(Usuario.roles).where(Usuario.activo.is_(True), Rol.codigo == "ADMIN")) or 0
        if active_admins <= 1:
            raise IdentityError("No se puede desactivar el último ADMIN activo.")
    user.activo = active
    if not active:
        revoke_user_sessions(db, user.id)
    db.commit()
