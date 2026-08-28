import getpass

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.identity import Rol
from app.schemas.identity import UserCreate
from app.services.auth_service import IdentityError, create_user


def main() -> None:
    username = input("Username o email del ADMIN: ").strip()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Repite la contraseña: ")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")
    with SessionLocal() as db:
        if db.scalar(select(Rol).where(Rol.codigo == "ADMIN")) is None:
            raise SystemExit("Falta aplicar la migración de identidad con: alembic upgrade head")
        try:
            user = create_user(db, UserCreate(username=username, password=password), "ADMIN")
        except (IdentityError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
        print(f"ADMIN creado correctamente: {user.username}")


if __name__ == "__main__":
    main()
