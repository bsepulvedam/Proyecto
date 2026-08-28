import os
import re
import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.empresa import Empresa
from app.models.identity import Rol, SesionUsuario, Trabajador, Usuario
from app.schemas.identity import AdminUserData, UserCreate, WorkerData
from app.services.auth_service import IdentityError, authenticate_user, create_user, verify_password
from app.services.identity_admin_service import create_managed_user, get_user, reset_password, save_worker, set_user_active
from tests.test_identity_auth import ASGIClient


class IdentityAdminTests(unittest.TestCase):
    def setUp(self):
        self.previous = {name: os.environ.get(name) for name in ("AUTH_ENFORCED", "SESSION_SECRET", "COOKIE_SECURE")}
        os.environ.update({"AUTH_ENFORCED": "true", "SESSION_SECRET": "test-secret-only-not-production", "COOKIE_SECURE": "false"})
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.add_all([Rol(codigo="ADMIN", nombre="Administrador"), Rol(codigo="JEFATURA", nombre="Jefatura"), Rol(codigo="TRABAJADOR", nombre="Trabajador"), Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")])
            db.commit()

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = ASGIClient()
        with self.Session() as db:
            self.admin = create_user(db, UserCreate(username="admin", password="Clave-Admin-Segura-123"), "ADMIN")

    def tearDown(self):
        app.dependency_overrides.clear(); self.engine.dispose()
        for name, value in self.previous.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value

    def login(self, client, username, password):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return client.post("/login", {"username": username, "password": password, "csrf_token": token})

    def csrf(self, client=None):
        return (client or self.client).cookies["boliklor_csrf"]

    def create_worker_and_temporary_user(self, role="TRABAJADOR"):
        with self.Session() as db:
            company = db.scalar(select(Empresa).where(Empresa.codigo == "BOLIKLOR"))
            worker = save_worker(db, WorkerData(nombres="Ana", apellidos="Pérez", empresa_id=company.id, codigo_interno="T-1"))
            user, temporary = create_managed_user(db, AdminUserData(username="ana", trabajador_id=worker.id, rol=role))
            return worker, user, temporary

    def test_create_edit_and_deactivate_worker_without_disabling_user(self):
        worker, user, _ = self.create_worker_and_temporary_user()
        with self.Session() as db:
            stored = db.get(Trabajador, worker.id)
            save_worker(db, WorkerData(nombres="Ana María", apellidos="Pérez Soto", codigo_interno="T-2", activo=False), stored)
            self.assertFalse(stored.activo)
            self.assertEqual((stored.nombres, stored.codigo_interno), ("Ana María", "T-2"))
            self.assertTrue(db.get(Usuario, user.id).activo)

    def test_admin_worker_routes_create_and_edit(self):
        self.login(self.client, "admin", "Clave-Admin-Segura-123")
        response = self.client.post("/admin/trabajadores", {"csrf_token": self.csrf(), "nombres": "Luis", "apellidos": "Rojas", "codigo_interno": "L-1", "activo": "1"})
        self.assertEqual(response.status_code, 303)
        with self.Session() as db:
            worker = db.scalar(select(Trabajador).where(Trabajador.codigo_interno == "L-1"))
        update = self.client.post(f"/admin/trabajadores/{worker.id}", {"csrf_token": self.csrf(), "nombres": "Luis Alberto", "apellidos": "Rojas", "codigo_interno": "L-1"})
        self.assertEqual(update.status_code, 303)
        with self.Session() as db:
            self.assertEqual(db.get(Trabajador, worker.id).nombres, "Luis Alberto")
            self.assertFalse(db.get(Trabajador, worker.id).activo)

    def test_temporary_user_is_unique_and_admin_can_have_no_worker(self):
        worker, user, temporary = self.create_worker_and_temporary_user()
        self.assertTrue(user.debe_cambiar_password)
        self.assertTrue(verify_password(temporary, user.password_hash))
        with self.Session() as db, self.assertRaises(IdentityError):
            create_managed_user(db, AdminUserData(username="otra", trabajador_id=worker.id, rol="TRABAJADOR"))
        with self.Session() as db:
            administrative, _ = create_managed_user(db, AdminUserData(username="jefatura", trabajador_id=None, rol="JEFATURA"))
            self.assertIsNone(administrative.trabajador)

    def test_admin_creation_shows_temporary_password_once_without_hash(self):
        self.login(self.client, "admin", "Clave-Admin-Segura-123")
        response = self.client.post("/admin/usuarios", {"csrf_token": self.csrf(), "username": "nuevo", "rol": "TRABAJADOR", "activo": "1"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("se muestra una sola vez", response.text)
        self.assertNotIn("password_hash", response.text)
        self.assertNotIn("$argon2", response.text)
        listing = self.client.get("/admin/usuarios")
        self.assertNotIn("password_hash", listing.text)
        self.assertNotIn("$argon2", listing.text)

    def test_forced_redirect_change_and_new_password_replaces_temporary(self):
        _, _, temporary = self.create_worker_and_temporary_user()
        login = self.login(self.client, "ana", temporary)
        self.assertEqual(login.headers["location"], "/cambiar-password")
        self.assertEqual(self.client.get("/dashboard").headers["location"], "/cambiar-password")
        change = self.client.post("/cambiar-password", {"csrf_token": self.csrf(), "current_password": temporary,
            "new_password": "Nueva-Clave-Personal-456", "confirmation": "Nueva-Clave-Personal-456"})
        self.assertEqual(change.headers["location"], "/dashboard")
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.client.clear()
        self.assertEqual(self.login(self.client, "ana", temporary).status_code, 401)
        self.client.clear()
        self.assertEqual(self.login(self.client, "ana", "Nueva-Clave-Personal-456").status_code, 303)

    def test_invalid_new_password_and_different_confirmation(self):
        _, _, temporary = self.create_worker_and_temporary_user()
        self.login(self.client, "ana", temporary)
        short = self.client.post("/cambiar-password", {"csrf_token": self.csrf(), "current_password": temporary, "new_password": "corta", "confirmation": "corta"})
        self.assertEqual(short.status_code, 422)
        mismatch = self.client.post("/cambiar-password", {"csrf_token": self.csrf(), "current_password": temporary,
            "new_password": "Nueva-Clave-Personal-456", "confirmation": "Otra-Clave-Personal-789"})
        self.assertEqual(mismatch.status_code, 422)

    def test_admin_reset_revokes_sessions_and_new_temporary_password_works(self):
        _, user, temporary = self.create_worker_and_temporary_user()
        worker_client = ASGIClient(); self.login(worker_client, "ana", temporary)
        with self.Session() as db:
            stored = get_user(db, user.id)
            new_temporary = reset_password(db, stored)
        self.assertEqual(worker_client.get("/dashboard").status_code, 303)
        worker_client.clear()
        login = self.login(worker_client, "ana", new_temporary)
        self.assertEqual(login.headers["location"], "/cambiar-password")
        with self.Session() as db:
            self.assertGreater(db.scalar(select(func.count()).select_from(SesionUsuario).where(SesionUsuario.usuario_id == user.id, SesionUsuario.revoked_at.is_not(None))) or 0, 0)

    def test_inactive_user_cannot_login_and_deactivation_revokes_sessions(self):
        _, user, temporary = self.create_worker_and_temporary_user()
        worker_client = ASGIClient(); self.login(worker_client, "ana", temporary)
        with self.Session() as db:
            set_user_active(db, get_user(db, user.id), False)
        self.assertEqual(worker_client.get("/dashboard").status_code, 303)
        worker_client.clear()
        self.assertEqual(self.login(worker_client, "ana", temporary).status_code, 401)

    def test_last_active_admin_cannot_be_disabled(self):
        with self.Session() as db, self.assertRaises(IdentityError):
            set_user_active(db, get_user(db, self.admin.id), False)

    def test_admin_allowed_and_other_roles_blocked(self):
        with self.Session() as db:
            create_user(db, UserCreate(username="jefa", password="Clave-Jefatura-123"), "JEFATURA")
            create_user(db, UserCreate(username="trabajador", password="Clave-Trabajador-123"), "TRABAJADOR")
        for username, password, expected in (("admin", "Clave-Admin-Segura-123", 200), ("jefa", "Clave-Jefatura-123", 403), ("trabajador", "Clave-Trabajador-123", 403)):
            client = ASGIClient(); self.login(client, username, password)
            self.assertEqual(client.get("/admin/usuarios").status_code, expected)

    def test_admin_posts_remain_csrf_protected(self):
        self.login(self.client, "admin", "Clave-Admin-Segura-123")
        self.assertEqual(self.client.post("/admin/trabajadores", {"nombres": "Sin", "apellidos": "Token"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
