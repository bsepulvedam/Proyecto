import os
import re
import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.attendance import TarifaProvisionalAsistencia
from app.models.empresa import Empresa
from app.models.identity import Rol, Trabajador
from app.schemas.identity import UserCreate
from app.services.attendance_rate_service import effective_rate_for_worker
from app.services.auth_service import create_user
from tests.test_identity_auth import ASGIClient


class AttendanceRatesWebTests(unittest.TestCase):
    def setUp(self) -> None:
        names = ("APP_ENV", "AUTH_ENFORCED", "SESSION_SECRET", "COOKIE_SECURE", "APP_TIMEZONE")
        self.previous = {name: os.environ.get(name) for name in names}
        os.environ.update(
            {
                "APP_ENV": "test",
                "AUTH_ENFORCED": "true",
                "SESSION_SECRET": "test-secret-only-not-production",
                "COOKIE_SECURE": "false",
                "APP_TIMEZONE": "America/Santiago",
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
                    Empresa(codigo="RATE", nombre="Tarifas"),
                ]
            )
            db.commit()
            self.users = {
                "admin": create_user(db, UserCreate(username="admin-rates", password="Clave-Admin-Rates-123"), "ADMIN"),
                "jefatura": create_user(db, UserCreate(username="jefatura-rates", password="Clave-Jefatura-Rates-123"), "JEFATURA"),
                "worker": create_user(db, UserCreate(username="worker-rates", password="Clave-Worker-Rates-123"), "TRABAJADOR"),
            }
            company = db.scalar(select(Empresa))
            self.worker = Trabajador(
                usuario_id=self.users["worker"].id,
                empresa_id=company.id,
                codigo_interno="RATE-001",
                nombres="Ada",
                apellidos="Lovelace",
            )
            self.other_worker = Trabajador(
                empresa_id=company.id,
                codigo_interno="RATE-002",
                nombres="Grace",
                apellidos="Hopper",
            )
            db.add_all([self.worker, self.other_worker])
            db.flush()
            db.add(
                TarifaProvisionalAsistencia(
                    valor_clp=Decimal("30000"),
                    vigente_desde=date(2026, 9, 1),
                    origen="SISTEMA",
                )
            )
            db.commit()
            self.worker_id = self.worker.id
            self.other_worker_id = self.other_worker.id

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    @staticmethod
    def login(client, username, password):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        return client.post(
            "/login",
            {"username": username, "password": password, "csrf_token": token},
        )

    def client_for(self, role):
        client = ASGIClient()
        credentials = {
            "admin": ("admin-rates", "Clave-Admin-Rates-123"),
            "jefatura": ("jefatura-rates", "Clave-Jefatura-Rates-123"),
            "worker": ("worker-rates", "Clave-Worker-Rates-123"),
        }[role]
        self.assertEqual(self.login(client, *credentials).status_code, 303)
        return client

    @staticmethod
    def payload(csrf, effective_from, amount):
        return {
            "csrf_token": csrf,
            "vigente_desde": effective_from,
            "monto_clp": amount,
            "confirmacion": "SI",
        }

    def test_rate_pages_are_admin_only_and_navigation_hides_mutation(self):
        index = "/admin/asistencia/tarifas"
        detail = f"{index}/trabajadores/{self.worker_id}"
        self.assertEqual(ASGIClient().get(index).status_code, 303)
        for role in ("jefatura", "worker"):
            client = self.client_for(role)
            self.assertEqual(client.get(index).status_code, 403)
            self.assertEqual(client.get(detail).status_code, 403)
            self.assertNotIn("Tarifas asistencia", client.get("/dashboard").text)
        admin = self.client_for("admin")
        page = admin.get(index)
        self.assertEqual(page.status_code, 200)
        self.assertIn("$30.000", page.text)
        self.assertIn("Tarifas asistencia", page.text)
        worker_page = admin.get(detail)
        self.assertIn("$30.000", worker_page.text)
        self.assertIn("GLOBAL", worker_page.text)
        self.assertIn("Sin override individual", worker_page.text)

    def test_global_and_individual_mutations_require_valid_csrf(self):
        admin = self.client_for("admin")
        csrf = admin.cookies["boliklor_csrf"]
        global_path = "/admin/asistencia/tarifas/global"
        individual_path = f"/admin/asistencia/tarifas/trabajadores/{self.worker_id}"
        for path in (global_path, individual_path):
            payload = self.payload(csrf, "2026-10-01", "35000")
            without = dict(payload)
            without.pop("csrf_token")
            self.assertEqual(admin.post(path, without).status_code, 403)
            self.assertEqual(admin.post(path, dict(payload, csrf_token="inválido")).status_code, 403)
        self.assertEqual(admin.post(global_path, self.payload(csrf, "2026-10-01", "35000")).status_code, 303)
        self.assertEqual(admin.post(individual_path, self.payload(csrf, "2026-09-15", "40000")).status_code, 303)

    def test_versioning_precedence_history_validation_and_conflicts(self):
        admin = self.client_for("admin")
        csrf = admin.cookies["boliklor_csrf"]
        global_path = "/admin/asistencia/tarifas/global"
        individual_path = f"/admin/asistencia/tarifas/trabajadores/{self.worker_id}"
        self.assertEqual(admin.post(global_path, self.payload(csrf, "2026-10-01", "35000")).status_code, 303)
        self.assertEqual(admin.post(individual_path, self.payload(csrf, "2026-09-15", "40000")).status_code, 303)
        self.assertEqual(admin.post(individual_path, self.payload(csrf, "2026-10-15", "45000")).status_code, 303)
        with self.Session() as db:
            september_early = effective_rate_for_worker(db, self.worker_id, date(2026, 9, 10))
            september_override = effective_rate_for_worker(db, self.worker_id, date(2026, 9, 20))
            october_override = effective_rate_for_worker(db, self.worker_id, date(2026, 10, 20))
            other = effective_rate_for_worker(db, self.other_worker_id, date(2026, 10, 20))
            self.assertEqual((september_early.amount_clp, september_early.source), (30000, "GLOBAL"))
            self.assertEqual((september_override.amount_clp, september_override.source), (40000, "INDIVIDUAL"))
            self.assertEqual((october_override.amount_clp, october_override.source), (45000, "INDIVIDUAL"))
            self.assertEqual((other.amount_clp, other.source), (35000, "GLOBAL"))
            global_rows = db.scalars(
                select(TarifaProvisionalAsistencia)
                .where(TarifaProvisionalAsistencia.trabajador_id.is_(None))
                .order_by(TarifaProvisionalAsistencia.vigente_desde)
            ).all()
            self.assertEqual(
                [(row.vigente_desde, int(row.valor_clp)) for row in global_rows],
                [(date(2026, 9, 1), 30000), (date(2026, 10, 1), 35000)],
            )
            self.assertEqual(global_rows[1].creado_por_id, self.users["admin"].id)

        duplicate = admin.post(global_path, self.payload(csrf, "2026-10-01", "36000"))
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("Ya existe una tarifa global", duplicate.text)
        duplicate_individual = admin.post(
            individual_path, self.payload(csrf, "2026-09-15", "41000")
        )
        self.assertEqual(duplicate_individual.status_code, 409)
        self.assertIn("Ya existe una tarifa del trabajador", duplicate_individual.text)
        for effective_from, amount in (("fecha-mala", "30000"), ("2026-11-01", "0"), ("2026-11-01", "30000.5")):
            response = admin.post(global_path, self.payload(csrf, effective_from, amount))
            self.assertEqual(response.status_code, 422)
        missing_confirmation = self.payload(csrf, "2026-11-01", "36000")
        missing_confirmation.pop("confirmacion")
        self.assertEqual(admin.post(global_path, missing_confirmation).status_code, 422)
        self.assertEqual(
            admin.post(
                "/admin/asistencia/tarifas/trabajadores/999999",
                self.payload(csrf, "2026-11-01", "36000"),
            ).status_code,
            404,
        )

    def test_jefatura_cannot_post_even_with_valid_csrf(self):
        client = self.client_for("jefatura")
        csrf = client.cookies["boliklor_csrf"]
        self.assertEqual(
            client.post(
                "/admin/asistencia/tarifas/global",
                self.payload(csrf, "2026-10-01", "35000"),
            ).status_code,
            403,
        )
        worker = self.client_for("worker")
        self.assertEqual(
            worker.post(
                f"/admin/asistencia/tarifas/trabajadores/{self.worker_id}",
                self.payload(worker.cookies["boliklor_csrf"], "2026-10-01", "35000"),
            ).status_code,
            403,
        )
        self.assertEqual(
            ASGIClient().post(
                "/admin/asistencia/tarifas/global",
                self.payload("sin-sesion", "2026-10-01", "35000"),
            ).status_code,
            303,
        )


if __name__ == "__main__":
    unittest.main()
