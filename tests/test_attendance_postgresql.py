import os
import threading
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models.attendance import (
    IncidenciaAsistencia,
    IntervencionSalidaAdministrativa,
    MarcajeAsistencia,
    SesionTrabajo,
    TarifaProvisionalAsistencia,
    Turno,
)
from app.models.empresa import Empresa
from app.models.identity import Trabajador, Usuario
from app.services.attendance_admin_service import (
    AttendanceAdministrationError,
    complete_administrative_exit,
    decide_attendance_incident,
)
from app.services.attendance_rate_service import (
    AttendanceRateError,
    create_rate_version,
)


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")


@unittest.skipUnless(TEST_DATABASE_URL, "requiere TEST_DATABASE_URL desechable")
class AttendancePostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        test_url = make_url(TEST_DATABASE_URL)
        real_url_value = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(
            "DATABASE_URL"
        )
        if test_url.database is None or not test_url.database.endswith(("_test", "_ci")):
            raise RuntimeError("TEST_DATABASE_URL no apunta a una base desechable.")
        if real_url_value and make_url(real_url_value) == test_url:
            raise RuntimeError("TEST_DATABASE_URL coincide con la base real.")
        cls.engine = create_engine(test_url, pool_pre_ping=True)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        with cls.engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        if revision != "20260902_09":
            raise RuntimeError("La base desechable no está en 20260902_09.")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.prefix = f"4b3b-{uuid.uuid4().hex[:12]}"
        with self.Session() as db:
            company = Empresa(codigo=self.prefix, nombre=f"Empresa {self.prefix}")
            actor = Usuario(
                username=f"{self.prefix}@test.invalid",
                password_hash="hash-no-secreto",
                activo=True,
            )
            shift = Turno(codigo=self.prefix.upper(), nombre="Turno prueba 4B-3B")
            db.add_all([company, actor, shift])
            db.flush()
            worker = Trabajador(
                empresa_id=company.id,
                codigo_interno=self.prefix,
                nombres="Prueba",
                apellidos="PostgreSQL",
            )
            db.add(worker)
            db.commit()
            self.company_id = company.id
            self.actor_id = actor.id
            self.shift_id = shift.id
            self.worker_id = worker.id

    def tearDown(self) -> None:
        with self.Session() as db:
            session_ids = select(SesionTrabajo.id).where(
                SesionTrabajo.trabajador_id == self.worker_id
            )
            mark_ids = select(MarcajeAsistencia.id).where(
                MarcajeAsistencia.sesion_id.in_(session_ids)
            )
            db.execute(
                delete(IntervencionSalidaAdministrativa).where(
                    IntervencionSalidaAdministrativa.sesion_id.in_(session_ids)
                )
            )
            db.execute(
                delete(IncidenciaAsistencia).where(
                    IncidenciaAsistencia.marcaje_id.in_(mark_ids)
                )
            )
            db.execute(
                delete(TarifaProvisionalAsistencia).where(
                    TarifaProvisionalAsistencia.trabajador_id == self.worker_id
                )
            )
            db.execute(
                delete(MarcajeAsistencia).where(
                    MarcajeAsistencia.sesion_id.in_(session_ids)
                )
            )
            db.execute(
                delete(SesionTrabajo).where(
                    SesionTrabajo.trabajador_id == self.worker_id
                )
            )
            db.execute(delete(Trabajador).where(Trabajador.id == self.worker_id))
            db.execute(delete(Usuario).where(Usuario.id == self.actor_id))
            db.execute(delete(Turno).where(Turno.id == self.shift_id))
            db.execute(delete(Empresa).where(Empresa.id == self.company_id))
            db.commit()

    def _incomplete_session(self) -> tuple[int, datetime]:
        entry_at = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
        with self.Session() as db:
            session = SesionTrabajo(
                trabajador_id=self.worker_id,
                turno_id=self.shift_id,
                fecha_operacional=date(2026, 9, 2),
                estado="ABIERTA",
            )
            db.add(session)
            db.flush()
            db.add(
                MarcajeAsistencia(
                    sesion_id=session.id,
                    tipo="ENTRADA",
                    ocurrido_at=entry_at,
                )
            )
            db.commit()
            return session.id, entry_at

    @staticmethod
    def _concurrent(callable_):
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()

        def run() -> None:
            barrier.wait()
            try:
                callable_()
                result = "OK"
            except (AttendanceAdministrationError, AttendanceRateError):
                result = "CONTROLLED_ERROR"
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        if any(thread.is_alive() for thread in threads):
            raise RuntimeError("La prueba concurrente no terminó.")
        return sorted(outcomes)

    def test_row_lock_allows_exactly_one_administrative_exit(self):
        session_id, entry_at = self._incomplete_session()

        def action() -> None:
            with self.Session() as db:
                complete_administrative_exit(
                    db,
                    session_id,
                    entry_at + timedelta(hours=8),
                    db.get(Usuario, self.actor_id),
                    "Prueba concurrente controlada.",
                    action_at=entry_at + timedelta(days=1),
                )

        self.assertEqual(self._concurrent(action), ["CONTROLLED_ERROR", "OK"])
        with self.Session() as db:
            self.assertEqual(
                db.scalar(
                    select(text("count(*)")).select_from(
                        IntervencionSalidaAdministrativa
                    ).where(IntervencionSalidaAdministrativa.sesion_id == session_id)
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(text("count(*)")).select_from(MarcajeAsistencia).where(
                        MarcajeAsistencia.sesion_id == session_id,
                        MarcajeAsistencia.tipo == "SALIDA",
                    )
                ),
                1,
            )

    def test_row_lock_allows_exactly_one_incident_decision(self):
        session_id, _ = self._incomplete_session()
        with self.Session() as db:
            mark_id = db.scalar(
                select(MarcajeAsistencia.id).where(
                    MarcajeAsistencia.sesion_id == session_id,
                    MarcajeAsistencia.tipo == "ENTRADA",
                )
            )
            incident = IncidenciaAsistencia(
                marcaje_id=mark_id,
                tipo="FUERA_RANGO",
            )
            db.add(incident)
            db.commit()
            incident_id = incident.id

        def action() -> None:
            with self.Session() as db:
                decide_attendance_incident(
                    db,
                    incident_id,
                    "APROBADA",
                    db.get(Usuario, self.actor_id),
                )

        self.assertEqual(self._concurrent(action), ["CONTROLLED_ERROR", "OK"])
        with self.Session() as db:
            stored = db.get(IncidenciaAsistencia, incident_id)
            self.assertEqual(stored.estado, "APROBADA")
            self.assertEqual(stored.resuelto_por_id, self.actor_id)

    def test_unique_index_allows_exactly_one_rate_per_worker_and_date(self):
        def action() -> None:
            with self.Session() as db:
                create_rate_version(
                    db,
                    effective_from=date(2026, 10, 1),
                    amount_clp=42_000,
                    actor=db.get(Usuario, self.actor_id),
                    worker_id=self.worker_id,
                )

        self.assertEqual(self._concurrent(action), ["CONTROLLED_ERROR", "OK"])
        with self.Session() as db:
            rows = db.scalars(
                select(TarifaProvisionalAsistencia).where(
                    TarifaProvisionalAsistencia.trabajador_id == self.worker_id,
                    TarifaProvisionalAsistencia.vigente_desde == date(2026, 10, 1),
                )
            ).all()
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
