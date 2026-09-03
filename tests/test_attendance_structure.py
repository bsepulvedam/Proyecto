import asyncio
import os
import re
import tempfile
import unittest
from unittest.mock import patch
from datetime import date, datetime, time, timezone
from html import unescape
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.core.time import app_timezone
from app.models.attendance import JustificacionInasistencia, LugarTrabajo, MarcajeAsistencia, SesionTrabajo, Turno
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
        names = ("AUTH_ENFORCED", "SESSION_SECRET", "COOKIE_SECURE", "JUSTIFICATION_STORAGE_DIR", "APP_TIMEZONE")
        self.previous = {name: os.environ.get(name) for name in names}
        self.storage = tempfile.TemporaryDirectory()
        os.environ.update({
            "AUTH_ENFORCED": "true",
            "SESSION_SECRET": "test-secret-only-not-production",
            "COOKIE_SECURE": "false",
            "JUSTIFICATION_STORAGE_DIR": self.storage.name,
            "APP_TIMEZONE": "America/Santiago",
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
            self.assertTrue(db.get(LugarTrabajo, place.id).activo)

        listing = admin.get("/admin/lugares")
        self.assertIn('data-place-name="Obra Norte"', listing.text)
        self.assertIn('type="button" data-place-state-trigger', listing.text)
        self.assertIn('data-bs-dismiss="modal">No</button>', listing.text)
        self.assertIn("admin-places.js", listing.text)
        with self.Session() as db:
            self.assertTrue(db.get(LugarTrabajo, place.id).activo)

        deactivated = admin.post(f"/admin/lugares/{place.id}/estado", {
            "csrf_token": admin.cookies["boliklor_csrf"], "activo": "0",
        })
        self.assertEqual(deactivated.status_code, 303)
        deactivated_page = admin.get(deactivated.headers["location"])
        self.assertIn('Zona "Obra Norte" desactivada correctamente.', unescape(deactivated_page.text))
        self.assertIn('role="status"', deactivated_page.text)
        self.assertIn('aria-live="polite"', deactivated_page.text)
        with self.Session() as db:
            self.assertFalse(db.get(LugarTrabajo, place.id).activo)

        activated = admin.post(f"/admin/lugares/{place.id}/estado", {
            "csrf_token": admin.cookies["boliklor_csrf"], "activo": "1",
        })
        self.assertEqual(activated.status_code, 303)
        activated_page = admin.get(activated.headers["location"])
        self.assertIn('Zona "Obra Norte" activada correctamente.', unescape(activated_page.text))
        with self.Session() as db:
            self.assertTrue(db.get(LugarTrabajo, place.id).activo)

        script = Path("app/static/js/admin-places.js").read_text(encoding="utf-8")
        self.assertIn('message.textContent = `¿Deseas ${action} "${name}"?`', script)
        self.assertIn("pendingForm.requestSubmit()", script)
        self.assertNotIn("window.confirm", script)
        worker = ASGIClient(); self.login(worker, "ana", "Clave-Trabajador-123")
        self.assertEqual(worker.get("/admin/lugares").status_code, 403)

    def test_admin_configures_commune_by_official_code_and_can_deactivate_it(self):
        admin = ASGIClient(); self.login(admin, "admin", "Clave-Admin-Segura-123")
        payload = {
            "csrf_token": admin.cookies["boliklor_csrf"],
            "nombre": "Zona comunal Colina",
            "tipo": "TERRENO",
            "tipo_geocerca": "COMUNA",
            "codigo_comuna": "13301",
            "latitud": "-33.2023",
            "longitud": "-70.6749",
            "prioridad_geocerca": "20",
            "activo": "1",
        }
        created = admin.post("/admin/lugares", payload)
        self.assertEqual(created.status_code, 303)
        with self.Session() as db:
            place = db.scalar(select(LugarTrabajo).where(LugarTrabajo.nombre == "Zona comunal Colina"))
            self.assertEqual((place.tipo_geocerca, place.codigo_comuna, place.comuna), ("COMUNA", "13301", "Colina"))
            self.assertIsNone(place.radio_metros)
            place_id = place.id
        edited = admin.post(f"/admin/lugares/{place_id}/estado", {
            "csrf_token": admin.cookies["boliklor_csrf"], "activo": "0",
        })
        self.assertEqual(edited.status_code, 303)
        with self.Session() as db:
            self.assertFalse(db.get(LugarTrabajo, place_id).activo)
        payload.pop("activo")
        payload.update({"nombre": "Zona inválida", "codigo_comuna": "99999", "activo": "1"})
        self.assertEqual(admin.post("/admin/lugares", payload).status_code, 422)

    def test_place_state_change_requires_admin_and_csrf(self):
        with self.Session() as db:
            place = save_place(db, {"nombre": "Zona protegida", "tipo": "TERRENO", "activo": True})
            place_id = place.id

        admin = ASGIClient(); self.login(admin, "admin", "Clave-Admin-Segura-123")
        self.assertEqual(
            admin.post(f"/admin/lugares/{place_id}/estado", {"activo": "0"}).status_code,
            403,
        )
        worker = ASGIClient(); self.login(worker, "ana", "Clave-Trabajador-123")
        self.assertEqual(
            worker.post(f"/admin/lugares/{place_id}/estado", {
                "csrf_token": worker.cookies["boliklor_csrf"], "activo": "0",
            }).status_code,
            403,
        )
        invalid = admin.post(f"/admin/lugares/{place_id}/estado", {
            "csrf_token": admin.cookies["boliklor_csrf"], "activo": "desconocido",
        })
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("El estado solicitado no es válido.", invalid.text)
        with self.Session() as db:
            self.assertTrue(db.get(LugarTrabajo, place_id).activo)

    def test_place_state_backend_error_has_no_success_and_keeps_state(self):
        with self.Session() as db:
            place = save_place(db, {"nombre": "Zona con error", "tipo": "TERRENO", "activo": True})
            place_id = place.id

        admin = ASGIClient(); self.login(admin, "admin", "Clave-Admin-Segura-123")
        with patch("app.web.admin.set_place_active", side_effect=IdentityError("Falla interna simulada")):
            response = admin.post(f"/admin/lugares/{place_id}/estado", {
                "csrf_token": admin.cookies["boliklor_csrf"], "activo": "0",
            })

        self.assertEqual(response.status_code, 422)
        self.assertIn('No fue posible desactivar la zona "Zona con error".', unescape(response.text))
        self.assertIn('role="alert"', response.text)
        self.assertIn('aria-live="assertive"', response.text)
        self.assertNotIn("desactivada correctamente", response.text)
        self.assertNotIn("Falla interna simulada", response.text)
        with self.Session() as db:
            self.assertTrue(db.get(LugarTrabajo, place_id).activo)

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

    def test_worker_landing_sidebar_calendar_and_register_with_on_demand_gps(self):
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
        self.assertIn("attendance-register.js", register.text)
        self.assertIn("Marcar entrada", register.text)

    def test_calendar_renders_closed_sessions_and_keeps_other_worker_private(self):
        operational_day = date(2026, 9, 1)
        entry_at = datetime.combine(operational_day, time(9, 0), tzinfo=app_timezone()).astimezone(timezone.utc)
        exit_at = datetime.combine(operational_day, time(18, 30), tzinfo=app_timezone()).astimezone(timezone.utc)
        with self.Session() as db:
            shift = db.scalar(select(Turno).where(Turno.codigo == "DIURNO"))
            own_session = SesionTrabajo(
                trabajador_id=self.worker.id,
                turno_id=shift.id,
                fecha_operacional=operational_day,
                estado="CERRADA",
                cerrado_at=exit_at,
            )
            other_session = SesionTrabajo(
                trabajador_id=self.other_worker.id,
                turno_id=shift.id,
                fecha_operacional=date(2026, 9, 2),
                estado="CERRADA",
                cerrado_at=exit_at,
            )
            incomplete_session = SesionTrabajo(
                trabajador_id=self.worker.id,
                turno_id=shift.id,
                fecha_operacional=date(2026, 9, 3),
                estado="ABIERTA",
            )
            db.add_all([own_session, other_session, incomplete_session]); db.flush()
            db.add_all([
                MarcajeAsistencia(sesion_id=own_session.id, tipo="ENTRADA", ocurrido_at=entry_at),
                MarcajeAsistencia(sesion_id=own_session.id, tipo="SALIDA", ocurrido_at=exit_at),
                MarcajeAsistencia(sesion_id=other_session.id, tipo="ENTRADA", ocurrido_at=entry_at),
                MarcajeAsistencia(sesion_id=other_session.id, tipo="SALIDA", ocurrido_at=exit_at),
                MarcajeAsistencia(
                    sesion_id=incomplete_session.id,
                    tipo="ENTRADA",
                    ocurrido_at=datetime.combine(
                        date(2026, 9, 3),
                        time(9, 0),
                        tzinfo=app_timezone(),
                    ).astimezone(timezone.utc),
                ),
            ])
            db.commit()

        client = ASGIClient(); self.login(client, "ana", "Clave-Trabajador-123")
        page = client.get("/mi-asistencia?year=2026&month=9")
        self.assertEqual(page.status_code, 200)
        self.assertIn("calendar-day--trabajado", page.text)
        self.assertIn("Fecha trabajada", page.text)
        self.assertIn("Duración: 570 min", page.text)
        self.assertIn("Actividad registrada · incompleta", page.text)
        self.assertIn("Jornada incompleta: falta SALIDA", page.text)
        self.assertEqual(page.text.count("Fecha trabajada"), 2)

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
