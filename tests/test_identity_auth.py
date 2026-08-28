import asyncio
import os
import re
import unittest
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.empresa import Empresa
from app.models.identity import Rol, SesionUsuario, Trabajador, Usuario
from app.schemas.identity import UserCreate
from app.services.auth_service import IdentityError, authenticate_user, create_user, hash_password, verify_password


@dataclass
class ASGIResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    @property
    def text(self):
        return self.body.decode("utf-8")


class ASGIClient:
    def __init__(self):
        self.cookies: dict[str, str] = {}

    def clear(self):
        self.cookies.clear()

    def get(self, path):
        return asyncio.run(self.request("GET", path))

    def post(self, path, data=None):
        return asyncio.run(self.request("POST", path, data or {}))

    async def request(self, method, path, data=None):
        messages, sent = [], False
        body = urlencode(data or {}).encode()
        route, _, query = path.partition("?")

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        headers = [(b"host", b"testserver")]
        if method == "POST":
            headers.append((b"content-type", b"application/x-www-form-urlencoded"))
        if self.cookies:
            headers.append((b"cookie", "; ".join(f"{key}={value}" for key, value in self.cookies.items()).encode()))
        await app({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
            "scheme": "http", "path": route, "raw_path": route.encode(), "query_string": query.encode(),
            "root_path": "", "headers": headers, "client": ("127.0.0.1", 50000), "server": ("testserver", 80)}, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        response_headers: dict[str, str] = {}
        for key, value in start["headers"]:
            decoded_key, decoded_value = key.decode("latin-1"), value.decode("latin-1")
            response_headers[decoded_key] = decoded_value
            if decoded_key.lower() == "set-cookie":
                parsed = SimpleCookie(); parsed.load(decoded_value)
                for name, morsel in parsed.items():
                    if morsel["max-age"] == "0" or not morsel.value:
                        self.cookies.pop(name, None)
                    else:
                        self.cookies[name] = morsel.value
        response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return ASGIResponse(start["status"], response_headers, response_body)


class IdentityAuthTests(unittest.TestCase):
    def setUp(self):
        self.previous = {name: os.environ.get(name) for name in ("AUTH_ENFORCED", "SESSION_SECRET", "COOKIE_SECURE")}
        os.environ.update({"AUTH_ENFORCED": "true", "SESSION_SECRET": "test-secret-only-not-production", "COOKIE_SECURE": "false"})
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.add_all([Rol(codigo="ADMIN", nombre="Administrador"), Rol(codigo="JEFATURA", nombre="Jefatura"), Rol(codigo="TRABAJADOR", nombre="Trabajador")])
            db.commit()

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = ASGIClient()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def create(self, username="admin@boliklor.cl", password="Clave-Muy-Segura-123", role="ADMIN"):
        with self.Session() as db:
            return create_user(db, UserCreate(username=username, password=password), role)

    def login(self, username="admin@boliklor.cl", password="Clave-Muy-Segura-123"):
        page = self.client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return self.client.post("/login", data={"username": username, "password": password, "csrf_token": token})

    def test_argon2_hash_and_password_verification(self):
        password_hash = hash_password("Clave-Muy-Segura-123")
        self.assertTrue(password_hash.startswith("$argon2id$"))
        self.assertTrue(verify_password("Clave-Muy-Segura-123", password_hash))
        self.assertFalse(verify_password("incorrecta", password_hash))
        self.assertNotIn("Clave-Muy-Segura-123", password_hash)

    def test_unknown_inactive_and_wrong_password_are_rejected(self):
        with self.Session() as db:
            self.assertIsNone(authenticate_user(db, "nadie", "cualquier-clave"))
        user = self.create()
        with self.Session() as db:
            self.assertIsNone(authenticate_user(db, user.username, "incorrecta"))
            stored = db.get(Usuario, user.id)
            stored.activo = False
            db.commit()
            self.assertIsNone(authenticate_user(db, user.username, "Clave-Muy-Segura-123"))

    def test_duplicate_normalized_username_is_rejected(self):
        self.create("Admin@Boliklor.cl")
        with self.Session() as db, self.assertRaises(IdentityError):
            create_user(db, UserCreate(username=" ADMIN@BOLIKLOR.CL ", password="Otra-Clave-Segura-456"), "ADMIN")

    def test_worker_can_link_to_user_and_admin_can_exist_without_worker(self):
        admin = self.create()
        worker_user = self.create("trabajador@boliklor.cl", role="TRABAJADOR")
        with self.Session() as db:
            company = Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")
            db.add(company); db.flush()
            worker = Trabajador(usuario_id=worker_user.id, empresa_id=company.id, codigo_interno="T-1", nombres="Ana", apellidos="Pérez")
            db.add(worker); db.commit()
            self.assertIsNone(db.get(Usuario, admin.id).trabajador)
            self.assertEqual(db.get(Usuario, worker_user.id).trabajador.codigo_interno, "T-1")

    def test_anonymous_access_redirects_and_api_returns_401(self):
        self.assertEqual(self.client.get("/dashboard").status_code, 303)
        self.assertEqual(self.client.get("/api/productos/buscar?q=x&empresa_id=1").status_code, 401)

    def test_login_session_current_user_and_logout(self):
        self.create()
        response = self.login()
        self.assertEqual((response.status_code, response.headers["location"]), (303, "/dashboard"))
        self.assertIn("boliklor_session", self.client.cookies)
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("admin@boliklor.cl", dashboard.text)
        csrf = self.client.cookies.get("boliklor_csrf")
        logout = self.client.post("/logout", data={"csrf_token": csrf})
        self.assertEqual((logout.status_code, logout.headers["location"]), (303, "/login"))
        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(SesionUsuario).where(SesionUsuario.revoked_at.is_not(None))), 1)

    def test_roles_and_backend_module_protection(self):
        for username, role in (("admin", "ADMIN"), ("jefatura", "JEFATURA"), ("trabajador", "TRABAJADOR")):
            self.create(username, role=role)
        for username, expected in (("admin", 200), ("jefatura", 403), ("trabajador", 403)):
            self.client.clear()
            self.assertEqual(self.login(username).status_code, 303)
            self.assertEqual(self.client.get("/productos").status_code, expected)
            self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_csrf_protects_existing_authenticated_post(self):
        self.create()
        self.login()
        response = self.client.post("/productos/nuevo", data={})
        self.assertEqual(response.status_code, 403)

    def test_migration_is_additive_and_documents_future_shift_decision(self):
        migration = Path("alembic/versions/20260828_04_identidad_autenticacion_roles.py").read_text(encoding="utf-8")
        self.assertIn('down_revision: str | None = "20260827_03"', migration)
        for protected in ("productos", "movimientos_inventario", "detalle_movimientos_inventario", "ordenes_trabajo", "productos_ot"):
            self.assertNotIn(f'op.alter_table("{protected}"', migration)
        self.assertNotIn("marcajes", migration)
        self.assertNotIn("lugares_trabajo", migration)


if __name__ == "__main__":
    unittest.main()
