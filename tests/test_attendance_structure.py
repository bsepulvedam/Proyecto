import asyncio
import os
import re
import tempfile
import unittest
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.attendance import JustificacionInasistencia, LugarTrabajo, Turno
from app.models.empresa import Empresa
from app.models.identity import Rol, Trabajador
from app.schemas.identity import UserCreate
from app.services.attendance_service import (
    create_assignment,
    create_justification,
    get_justification,
    list_assignments,
    save_place,
)
from app.services.auth_service import IdentityError, create_user
from tests.test_identity_auth import ASGIClient


class AttendanceStructureTests(unittest.TestCase):
    def setUp(self):
        names = ("AUTH_ENFORCED", "SESSION_SECRET", "COOKIE_SECURE", "JUSTIFICATION_STORAGE_DIR")
        self.previous = {name: os.environ.get(name) for name in names}
        self.storage = tempfile.TemporaryDirectory()
        os.environ.update({
            "AUTH_ENFORCED": "true",
            "SESSION_SECRET": "test-secret-only-not-production",
            "COOKIE_SECURE": "false",
            "JUSTIFICATION_STORAGE_DIR": self.storage.name,
        })
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.add_all([
                Rol(codigo="ADMIN", nombre="Administrador"),
                Rol(codigo="JEFATURA", nombre="Jefatura"),
                Rol(codigo="TRABAJADOR", nombre="Trabajador"),
                Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR"),
                Turno(codigo="DIURNO", nombre="Diurno"),
                Turno(codigo="NOCTURNO", nombre="Nocturno"),
            ])
            db.commit()
            self.admin = create_user(db, UserCreate(username="admin", password="Clave-Admin-Segura-123"), "ADMIN")
            worker_user = create_user(db, UserCreate(username="ana", password="Clave-Trabajador-123"), "TRABAJADOR")
            other_user = create_user(db, UserCreate(username="beto", password="Clave-Trabajador-456"), "TRABAJADOR")
            company = db.scalar(select(Empresa))
            self.worker = Trabajador(usuario_id=worker_user.id, empresa_id=company.id, codigo_interno="T-1", nombres="Ana", apellidos="Pérez")
            self.other_worker = Trabajador(usuario_id=other_user.id, empresa_id=company.id, codigo_interno="T-2", nombres="Beto", apellidos="Rojas")
            db.add_all([self.worker, self.other_worker]); db.commit()

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.storage.cleanup()
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    @staticmethod
    def login(client, username, password):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return client.post("/login", {"username": username, "password": password, "csrf_token": token})

    def test_admin_lists_creates_edits_places_and_worker_is_denied(self):
        admin = ASGIClient(); self.login(admin, "admin", "Clave-Admin-Segura-123")
        self.assertEqual(admin.get("/admin/lugares").status_code, 200)
        created = admin.post("/admin/lugares", {"csrf_token": admin.cookies["boliklor_csrf"], "nombre": "Obra Norte", "tipo": "TERRENO", "comuna": "Colina", "activo": "1"})
        self.assertEqual(created.status_code, 303)
        with self.Session() as db:
            place = db.scalar(select(LugarTrabajo).where(LugarTrabajo.nombre == "Obra Norte"))
        edited = admin.post(f"/admin/lugares/{place.id}", {"csrf_token": admin.cookies["boliklor_csrf"], "nombre": "Obra Norte", "tipo": "TERRENO", "comuna": "Colina"})
        self.assertEqual(edited.status_code, 303)
        with self.Session() as db:
            self.assertFalse(db.get(LugarTrabajo, place.id).activo)
        worker = ASGIClient(); self.login(worker, "ana", "Clave-Trabajador-123")
        self.assertEqual(worker.get("/admin/lugares").status_code, 403)

    def test_assignments_preserve_history_when_place_is_inactive(self):
        with self.Session() as db:
            first = save_place(db, {"nombre": "Base", "tipo": "BASE", "activo": True})
            second = save_place(db, {"nombre": "Taller", "tipo": "TALLER", "activo": True})
            create_assignment(db, self.worker.id, first.id, datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc), False, self.admin.id)
            create_assignment(db, self.worker.id, second.id, datetime(2026, 2, 1, tzinfo=timezone.utc), None, True, self.admin.id)
            first.activo = False; db.commit()
            history = list_assignments(db)
            self.assertEqual(len(history), 2)
            self.assertIn("Base", {item.lugar.nombre for item in history})

    def test_initial_shifts_and_additive_migration(self):
        with self.Session() as db:
            self.assertEqual(set(db.scalars(select(Turno.codigo)).all()), {"DIURNO", "NOCTURNO"})
        migration = Path("alembic/versions/20260830_06_asistencia_estructura.py").read_text(encoding="utf-8")
        self.assertIn('down_revision: str | None = "20260829_05"', migration)
        self.assertNotIn("marcajes", migration.lower())
        for protected in ("productos", "movimientos_inventario", "ordenes_trabajo"):
            self.assertNotIn(f'op.alter_table("{protected}"', migration)

    def test_worker_landing_sidebar_calendar_and_register_without_gps(self):
        client = ASGIClient()
        login = self.login(client, "ana", "Clave-Trabajador-123")
        self.assertEqual(login.headers["location"], "/mi-asistencia")
        calendar = client.get("/mi-asistencia")
        self.assertEqual(calendar.status_code, 200)
        self.assertNotIn("AUSENTE", calendar.text.upper())
        for forbidden in ("Administración", "Inventario", "Productos", "Órdenes de Trabajo"):
            self.assertNotIn(forbidden, calendar.text)
        for allowed in ("Días trabajados", "Registrar asistencia", "Justificar inasistencia"):
            self.assertIn(allowed, calendar.text)
        self.assertEqual(client.get("/dashboard").headers["location"], "/mi-asistencia")
        register = client.get("/mi-asistencia/registrar")
        self.assertEqual(register.status_code, 200)
        self.assertIn("DIURNO", register.text); self.assertIn("NOCTURNO", register.text)
        self.assertNotIn("geolocation", register.text.lower())

    def test_justifications_text_file_validation_states_and_isolation(self):
        with self.Session() as db:
            text_item = asyncio.run(create_justification(db, db.get(Trabajador, self.worker.id), date(2026, 8, 20), "COORDINACION_JEFATURA", "Coordinado previamente.", None))
            self.assertEqual(text_item.estado, "PENDIENTE")
            upload = UploadFile(filename="licencia.pdf", file=BytesIO(b"%PDF-1.4\nprueba"))
            file_item = asyncio.run(create_justification(db, db.get(Trabajador, self.worker.id), date(2026, 8, 21), "LICENCIA_MEDICA", "", upload))
            self.assertTrue(Path(self.storage.name, file_item.archivo_storage_key).is_file())
            self.assertEqual(file_item.archivo_mime, "application/pdf")
            self.assertIsNone(get_justification(db, self.other_worker.id, file_item.id))
            with self.assertRaises(IdentityError):
                asyncio.run(create_justification(db, db.get(Trabajador, self.worker.id), date(2026, 8, 22), "OTRO", "", None))
            file_item.estado = "APROBADA"; db.commit()
            self.assertEqual(db.get(JustificacionInasistencia, file_item.id).estado, "APROBADA")

        ana = ASGIClient(); self.login(ana, "ana", "Clave-Trabajador-123")
        self.assertIn("Coordinado previamente", ana.get("/mi-asistencia/justificaciones").text)
        beto = ASGIClient(); self.login(beto, "beto", "Clave-Trabajador-456")
        self.assertNotIn("Coordinado previamente", beto.get("/mi-asistencia/justificaciones").text)
        self.assertEqual(beto.get(f"/mi-asistencia/justificaciones/{file_item.id}/archivo").status_code, 404)

    def test_invalid_disguised_upload_is_rejected(self):
        with self.Session() as db, self.assertRaises(IdentityError):
            upload = UploadFile(filename="falso.pdf", file=BytesIO(b"contenido no PDF"))
            asyncio.run(create_justification(db, db.get(Trabajador, self.worker.id), date.today(), "OTRO", "", upload))

    def test_inactive_worker_is_blocked_but_history_remains(self):
        with self.Session() as db:
            worker = db.get(Trabajador, self.worker.id); worker.activo = False; db.commit()
        client = ASGIClient(); self.login(client, "ana", "Clave-Trabajador-123")
        self.assertEqual(client.get("/mi-asistencia").status_code, 403)

    def test_login_visual_and_csrf_remain_active(self):
        client = ASGIClient(); login = client.get("/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn("login-card", login.text); self.assertIn("btn-brand", login.text)
        self.assertEqual(client.post("/login", {"username": "admin", "password": "Clave-Admin-Segura-123"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
