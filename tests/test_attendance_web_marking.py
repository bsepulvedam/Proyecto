import os
import re
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.attendance import (
    EvaluacionGeograficaMarcaje,
    EvidenciaGPSMarcaje,
    IncidenciaAsistencia,
    LugarTrabajo,
    MarcajeAsistencia,
    SesionTrabajo,
    Turno,
)
from app.models.empresa import Empresa
from app.models.identity import Rol, Trabajador, Usuario
from app.schemas.identity import UserCreate
from app.services.auth_service import create_user
from tests.test_identity_auth import ASGIClient


class AttendanceWebMarkingTests(unittest.TestCase):
    def setUp(self) -> None:
        names = (
            "APP_ENV",
            "AUTH_ENFORCED",
            "SESSION_SECRET",
            "COOKIE_SECURE",
            "APP_TIMEZONE",
            "ATTENDANCE_MIN_SESSION_MINUTES",
            "ATTENDANCE_MAX_GPS_ACCURACY_METERS",
        )
        self.previous_environment = {name: os.environ.get(name) for name in names}
        os.environ.update(
            {
                "APP_ENV": "test",
                "AUTH_ENFORCED": "true",
                "SESSION_SECRET": "test-secret-only-not-production",
                "COOKIE_SECURE": "false",
                "APP_TIMEZONE": "America/Santiago",
                "ATTENDANCE_MIN_SESSION_MINUTES": "5",
                "ATTENDANCE_MAX_GPS_ACCURACY_METERS": "100",
            }
        )
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            db.add_all(
                [
                    Rol(codigo="ADMIN", nombre="Administrador"),
                    Rol(codigo="JEFATURA", nombre="Jefatura"),
                    Rol(codigo="TRABAJADOR", nombre="Trabajador"),
                    Empresa(codigo="TEST", nombre="Empresa Test"),
                    Turno(codigo="DIURNO", nombre="Diurno"),
                    Turno(codigo="NOCTURNO", nombre="Nocturno"),
                    LugarTrabajo(
                        nombre="Zona Test",
                        tipo="TERRENO",
                        latitud=Decimal("-33.000000"),
                        longitud=Decimal("-70.000000"),
                        radio_metros=Decimal("150.00"),
                    ),
                ]
            )
            db.commit()
            users = {
                "ana": create_user(db, UserCreate(username="ana", password="Clave-Trabajador-123"), "TRABAJADOR"),
                "beto": create_user(db, UserCreate(username="beto", password="Clave-Trabajador-456"), "TRABAJADOR"),
                "sin_worker": create_user(db, UserCreate(username="sin-worker", password="Clave-Trabajador-789"), "TRABAJADOR"),
                "inactivo": create_user(db, UserCreate(username="inactivo", password="Clave-Trabajador-012"), "TRABAJADOR"),
                "admin": create_user(db, UserCreate(username="admin", password="Clave-Administrador-123"), "ADMIN"),
                "jefatura": create_user(db, UserCreate(username="jefatura", password="Clave-Jefatura-123"), "JEFATURA"),
            }
            company = db.scalar(select(Empresa))
            workers = {
                "ana": Trabajador(usuario_id=users["ana"].id, empresa_id=company.id, nombres="Ana", apellidos="Pérez"),
                "beto": Trabajador(usuario_id=users["beto"].id, empresa_id=company.id, nombres="Beto", apellidos="Rojas"),
                "inactivo": Trabajador(usuario_id=users["inactivo"].id, empresa_id=company.id, nombres="Ina", apellidos="Activa", activo=True),
                "admin": Trabajador(usuario_id=users["admin"].id, empresa_id=company.id, nombres="Ada", apellidos="Admin"),
            }
            db.add_all(workers.values())
            db.commit()
            self.user_ids = {key: value.id for key, value in users.items()}
            self.worker_ids = {key: value.id for key, value in workers.items()}
            self.day_shift_id = db.scalar(select(Turno.id).where(Turno.codigo == "DIURNO"))
            self.night_shift_id = db.scalar(select(Turno.id).where(Turno.codigo == "NOCTURNO"))
            self.place_id = db.scalar(select(LugarTrabajo.id))

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.start = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        for name, value in self.previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    @staticmethod
    def login(client: ASGIClient, username: str, password: str):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return client.post("/login", {"username": username, "password": password, "csrf_token": token})

    def worker_client(self, username: str = "ana", password: str = "Clave-Trabajador-123") -> ASGIClient:
        client = ASGIClient()
        self.assertEqual(self.login(client, username, password).status_code, 303)
        return client

    def mark_payload(self, client: ASGIClient, mark_type: str = "ENTRADA", **changes) -> dict[str, str]:
        payload = {
            "csrf_token": client.cookies["boliklor_csrf"],
            "tipo": mark_type,
            "latitud": "-33.000000000",
            "longitud": "-70.000000000",
            "precision_m": "20.00",
            "capturada_at": "2026-08-31T11:59:55+00:00",
        }
        if mark_type == "ENTRADA":
            payload["turno_id"] = str(self.day_shift_id)
        payload.update({key: str(value) for key, value in changes.items()})
        return payload

    def post_mark(self, client: ASGIClient, when: datetime, mark_type: str = "ENTRADA", **changes):
        with patch("app.services.attendance_marking_service.utc_now", return_value=when):
            return client.post("/mi-asistencia/registrar", self.mark_payload(client, mark_type, **changes))

    def count(self, model) -> int:
        with self.Session() as db:
            return db.scalar(select(func.count()).select_from(model))

    def test_unauthenticated_request_cannot_mark(self):
        response = ASGIClient().post("/mi-asistencia/registrar", {"tipo": "ENTRADA"})
        self.assertEqual((response.status_code, response.headers["location"]), (303, "/login"))
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_user_without_worker_cannot_mark(self):
        client = self.worker_client("sin-worker", "Clave-Trabajador-789")
        response = self.post_mark(client, self.start)
        self.assertEqual(response.status_code, 403)

    def test_inactive_worker_cannot_mark(self):
        client = self.worker_client("inactivo", "Clave-Trabajador-012")
        with self.Session() as db:
            db.get(Trabajador, self.worker_ids["inactivo"]).activo = False
            db.commit()
        self.assertEqual(self.post_mark(client, self.start).status_code, 403)

    def test_inactive_user_cannot_mark(self):
        client = self.worker_client()
        with self.Session() as db:
            db.get(Usuario, self.user_ids["ana"]).activo = False
            db.commit()
        self.assertEqual(self.post_mark(client, self.start).status_code, 303)

    def test_admin_and_jefatura_cannot_use_worker_marking_endpoint(self):
        cases = (
            ("admin", "Clave-Administrador-123"),
            ("jefatura", "Clave-Jefatura-123"),
        )
        for username, password in cases:
            with self.subTest(role=username):
                client = self.worker_client(username, password)
                self.assertEqual(self.post_mark(client, self.start).status_code, 403)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_missing_csrf_is_rejected(self):
        client = self.worker_client()
        payload = self.mark_payload(client)
        payload.pop("csrf_token")
        self.assertEqual(client.post("/mi-asistencia/registrar", payload).status_code, 403)

    def test_invalid_csrf_is_rejected(self):
        client = self.worker_client()
        self.assertEqual(self.post_mark(client, self.start, csrf_token="incorrecto").status_code, 403)

    def test_request_rejects_worker_ownership_fields(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, trabajador_id=self.worker_ids["beto"], user_id=self.user_ids["beto"], actor_id=self.user_ids["admin"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_request_rejects_official_time_and_operational_date(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, ocurrido_at="2000-01-01T00:00:00Z", fecha_operacional="2000-01-01")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_gps_is_required(self):
        client = self.worker_client()
        payload = self.mark_payload(client)
        for field in ("latitud", "longitud", "precision_m", "capturada_at"):
            payload.pop(field)
        self.assertEqual(client.post("/mi-asistencia/registrar", payload).status_code, 422)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_invalid_coordinates_and_device_timestamp_are_rejected(self):
        client = self.worker_client()
        cases = (
            {"latitud": "91"},
            {"longitud": "181"},
            {"latitud": "0", "longitud": "0"},
            {"precision_m": "0"},
            {"capturada_at": "2026-08-31T11:59:55"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.post_mark(client, self.start, **changes).status_code, 422)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_valid_entry_uses_authenticated_worker_and_server_time(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start)
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            mark = db.scalar(select(MarcajeAsistencia))
            session = db.get(SesionTrabajo, mark.sesion_id)
            evidence = db.scalar(select(EvidenciaGPSMarcaje))
            occurred = mark.ocurrido_at.replace(tzinfo=timezone.utc) if mark.ocurrido_at.tzinfo is None else mark.ocurrido_at
            self.assertEqual(session.trabajador_id, self.worker_ids["ana"])
            self.assertEqual(occurred, self.start)
            self.assertNotEqual(occurred, evidence.capturada_at)

    def test_duplicate_entry_is_rejected(self):
        client = self.worker_client()
        self.assertEqual(self.post_mark(client, self.start).status_code, 200)
        self.assertEqual(self.post_mark(client, self.start + timedelta(minutes=1)).status_code, 409)
        self.assertEqual((self.count(SesionTrabajo), self.count(MarcajeAsistencia)), (1, 1))

    def test_exit_without_open_session_is_rejected(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, "SALIDA")
        self.assertEqual(response.status_code, 409)
        self.assertIn("no tiene una sesión abierta", response.text)

    def test_exit_before_five_minutes_keeps_session_open(self):
        client = self.worker_client()
        self.post_mark(client, self.start)
        response = self.post_mark(client, self.start + timedelta(minutes=4, seconds=59), "SALIDA")
        self.assertEqual(response.status_code, 409)
        self.assertIn("al menos 5 minutos", response.text)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(SesionTrabajo.estado)), "ABIERTA")
        self.assertEqual(self.count(MarcajeAsistencia), 1)

    def test_valid_exit_closes_authenticated_workers_open_session(self):
        client = self.worker_client()
        self.post_mark(client, self.start)
        response = self.post_mark(client, self.start + timedelta(minutes=5), "SALIDA")
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            session = db.scalar(select(SesionTrabajo))
            self.assertEqual((session.trabajador_id, session.estado), (self.worker_ids["ana"], "CERRADA"))
        self.assertEqual(self.count(MarcajeAsistencia), 2)

    def test_invalid_or_inactive_shift_is_rejected_for_entry(self):
        client = self.worker_client()
        self.assertEqual(self.post_mark(client, self.start, turno_id=999999).status_code, 409)
        with self.Session() as db:
            db.get(Turno, self.night_shift_id).activo = False
            db.commit()
        self.assertEqual(self.post_mark(client, self.start, turno_id=self.night_shift_id).status_code, 409)
        self.assertEqual(self.count(MarcajeAsistencia), 0)

    def test_exit_rejects_turno_or_session_selection(self):
        client = self.worker_client()
        self.post_mark(client, self.start)
        for forbidden in ({"turno_id": self.night_shift_id}, {"sesion_id": 999999}):
            with self.subTest(forbidden=forbidden):
                response = self.post_mark(client, self.start + timedelta(minutes=5), "SALIDA", **forbidden)
                self.assertEqual(response.status_code, 422)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(SesionTrabajo.estado)), "ABIERTA")

    def test_out_of_range_registers_mark_and_incident(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, latitud="-34.000000000", longitud="-71.000000000")
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(EvaluacionGeograficaMarcaje.estado_geocerca)), "FUERA_RANGO")
            self.assertEqual(db.scalar(select(IncidenciaAsistencia.tipo)), "FUERA_RANGO")
        self.assertIn("fuera del rango permitido", response.text)
        self.assertNotIn("-34.000000000", response.text)

    def test_low_accuracy_registers_mark_and_incident(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, precision_m="100.01")
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(EvaluacionGeograficaMarcaje.estado_precision)), "BAJA_PRECISION")
            self.assertEqual(db.scalar(select(IncidenciaAsistencia.tipo)), "GPS_BAJA_PRECISION")
        self.assertIn("GPS de baja precisión", response.text)

    def test_no_configured_zones_still_registers_mark(self):
        with self.Session() as db:
            db.get(LugarTrabajo, self.place_id).activo = False
            db.commit()
        client = self.worker_client()
        response = self.post_mark(client, self.start)
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            self.assertEqual(db.scalar(select(EvaluacionGeograficaMarcaje.estado_geocerca)), "SIN_ZONA_CONFIGURADA")
            self.assertEqual(db.scalar(select(func.count()).select_from(IncidenciaAsistencia)), 0)
        self.assertIn("no existen zonas configuradas", response.text)

    def test_double_request_does_not_create_two_open_sessions(self):
        client = self.worker_client()
        first = self.post_mark(client, self.start)
        second = self.post_mark(client, self.start)
        self.assertEqual((first.status_code, second.status_code), (200, 409))
        self.assertEqual((self.count(SesionTrabajo), self.count(MarcajeAsistencia)), (1, 1))

    def test_worker_cannot_close_another_workers_session(self):
        ana = self.worker_client()
        self.post_mark(ana, self.start)
        beto = self.worker_client("beto", "Clave-Trabajador-456")
        response = self.post_mark(beto, self.start + timedelta(minutes=5), "SALIDA")
        self.assertEqual(response.status_code, 409)
        with self.Session() as db:
            session = db.scalar(select(SesionTrabajo))
            self.assertEqual((session.trabajador_id, session.estado), (self.worker_ids["ana"], "ABIERTA"))

    def test_registration_page_shows_only_current_possible_action(self):
        client = self.worker_client()
        page = client.get("/mi-asistencia/registrar")
        self.assertIn("Ana Pérez", page.text)
        self.assertIn("SIN SESIÓN ABIERTA", page.text)
        self.assertIn("Marcar entrada", page.text)
        self.assertNotIn("Marcar salida", page.text)
        self.post_mark(client, self.start)
        page = client.get("/mi-asistencia/registrar")
        self.assertIn("ABIERTA", page.text)
        self.assertIn("Diurno (DIURNO)", page.text)
        self.assertIn("31-08-2026 08:00", page.text)
        self.assertIn("Marcar salida", page.text)
        self.assertNotIn('name="turno_id"', page.text)

    def test_browser_gps_is_on_demand_and_has_no_tracking_or_storage(self):
        script = Path("app/static/js/attendance-register.js").read_text(encoding="utf-8")
        self.assertIn('form.addEventListener("submit"', script)
        self.assertIn("navigator.geolocation.getCurrentPosition", script)
        self.assertIn("enableHighAccuracy: true", script)
        self.assertIn("button.disabled = true", script)
        self.assertIn("button.disabled = false", script)
        for forbidden in ("watchPosition", "localStorage", "sessionStorage", "console.log", "fetch("):
            self.assertNotIn(forbidden, script)

    def test_unknown_place_selection_field_is_rejected(self):
        client = self.worker_client()
        response = self.post_mark(client, self.start, lugar_trabajo_id=self.place_id)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count(MarcajeAsistencia), 0)


if __name__ == "__main__":
    unittest.main()
