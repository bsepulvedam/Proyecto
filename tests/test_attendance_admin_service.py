import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.attendance import (
    EvaluacionGeograficaMarcaje,
    EvidenciaGPSMarcaje,
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
    effective_rate_for_worker,
)
from app.services.attendance_rules_service import GLOBAL_RATE, INDIVIDUAL_RATE


class AttendanceAdminServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        company = Empresa(codigo="TEST-4B3B", nombre="Empresa 4B-3B")
        self.actor = Usuario(
            username="admin-4b3b",
            password_hash="hash-no-secreto",
            activo=True,
        )
        self.shift = Turno(codigo="DIURNO", nombre="Diurno")
        self.night_shift = Turno(codigo="NOCTURNO", nombre="Nocturno")
        self.db.add_all([company, self.actor, self.shift, self.night_shift])
        self.db.flush()
        self.worker = Trabajador(
            empresa_id=company.id,
            codigo_interno="4B3B-1",
            nombres="Trabajador",
            apellidos="Prueba",
        )
        self.other_worker = Trabajador(
            empresa_id=company.id,
            codigo_interno="4B3B-2",
            nombres="Otra",
            apellidos="Persona",
        )
        self.db.add_all([self.worker, self.other_worker])
        self.db.commit()
        self.entry_at = datetime(2026, 9, 1, 13, 0, tzinfo=timezone.utc)
        self.action_at = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def incomplete_session(
        self,
        *,
        entry_at: datetime | None = None,
        operational_day: date = date(2026, 9, 1),
        shift: Turno | None = None,
    ) -> SesionTrabajo:
        session = SesionTrabajo(
            trabajador_id=self.worker.id,
            turno_id=(shift or self.shift).id,
            fecha_operacional=operational_day,
            estado="ABIERTA",
        )
        self.db.add(session)
        self.db.flush()
        self.db.add(
            MarcajeAsistencia(
                sesion_id=session.id,
                tipo="ENTRADA",
                ocurrido_at=entry_at or self.entry_at,
            )
        )
        self.db.commit()
        return session

    def incident(self) -> tuple[IncidenciaAsistencia, MarcajeAsistencia]:
        session = self.incomplete_session()
        mark = self.db.scalar(
            select(MarcajeAsistencia).where(
                MarcajeAsistencia.sesion_id == session.id,
                MarcajeAsistencia.tipo == "ENTRADA",
            )
        )
        incident = IncidenciaAsistencia(
            marcaje_id=mark.id,
            tipo="FUERA_RANGO",
            detalle="Evidencia factual",
        )
        self.db.add(incident)
        self.db.commit()
        return incident, mark

    @staticmethod
    def aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    def test_administrative_exit_is_atomic_auditable_and_has_no_fake_gps(self):
        session = self.incomplete_session()
        exit_at = self.entry_at + timedelta(hours=8)
        intervention = complete_administrative_exit(
            self.db,
            session.id,
            exit_at,
            self.actor,
            "Trabajador informó olvido de marcaje.",
            action_at=self.action_at,
        )

        stored_session = self.db.get(SesionTrabajo, session.id)
        exit_mark = self.db.get(MarcajeAsistencia, intervention.marcaje_salida_id)
        self.assertEqual(stored_session.estado, "CERRADA")
        self.assertEqual(self.aware(stored_session.cerrado_at), self.action_at)
        self.assertEqual(stored_session.fecha_operacional, date(2026, 9, 1))
        self.assertEqual(stored_session.turno_id, self.shift.id)
        self.assertEqual((exit_mark.tipo, self.aware(exit_mark.ocurrido_at)), ("SALIDA", exit_at))
        self.assertEqual(intervention.creado_por_id, self.actor.id)
        self.assertEqual(intervention.motivo, "Trabajador informó olvido de marcaje.")
        self.assertTrue(intervention.salida_original_ausente)
        self.assertEqual(intervention.tipo_marcaje_salida, "SALIDA")
        self.assertIsNotNone(intervention.created_at)
        self.assertEqual(
            self.aware(intervention.hora_laboral_introducida), exit_at
        )
        self.assertIsNone(
            self.db.scalar(
                select(EvidenciaGPSMarcaje).where(
                    EvidenciaGPSMarcaje.marcaje_id == exit_mark.id
                )
            )
        )
        self.assertIsNone(
            self.db.scalar(
                select(EvaluacionGeograficaMarcaje).where(
                    EvaluacionGeograficaMarcaje.marcaje_id == exit_mark.id
                )
            )
        )

    def test_administrative_exit_supports_midnight_without_changing_facts(self):
        entry_at = datetime(2026, 9, 2, 2, 58, tzinfo=timezone.utc)
        session = self.incomplete_session(
            entry_at=entry_at,
            operational_day=date(2026, 9, 1),
            shift=self.night_shift,
        )
        exit_at = datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
        complete_administrative_exit(
            self.db,
            session.id,
            exit_at,
            self.actor,
            "Salida nocturna acreditada.",
            action_at=self.action_at,
        )
        stored = self.db.get(SesionTrabajo, session.id)
        self.assertEqual(stored.fecha_operacional, date(2026, 9, 1))
        self.assertEqual(stored.turno_id, self.night_shift.id)

    def test_administrative_exit_rejects_minimum_naive_time_and_duplicate(self):
        session = self.incomplete_session()
        for exit_at, message in (
            (self.entry_at + timedelta(minutes=4, seconds=59), "al menos 5 minutos"),
            (self.entry_at, "al menos 5 minutos"),
            (self.entry_at - timedelta(minutes=1), "al menos 5 minutos"),
            (self.entry_at.replace(tzinfo=None), "zona horaria"),
        ):
            with self.subTest(exit_at=exit_at), self.assertRaisesRegex(
                AttendanceAdministrationError, message
            ):
                complete_administrative_exit(
                    self.db, session.id, exit_at, self.actor, "Motivo válido."
                )
        self.assertEqual(self.db.scalar(select(func.count(MarcajeAsistencia.id))), 1)
        self.assertEqual(
            self.db.scalar(select(func.count(IntervencionSalidaAdministrativa.id))), 0
        )

        with self.assertRaisesRegex(AttendanceAdministrationError, "motivo es obligatorio"):
            complete_administrative_exit(
                self.db,
                session.id,
                self.entry_at + timedelta(hours=1),
                self.actor,
                "   ",
            )

        complete_administrative_exit(
            self.db,
            session.id,
            self.entry_at + timedelta(minutes=5),
            self.actor,
            "Motivo válido.",
            action_at=self.action_at,
        )
        with self.assertRaisesRegex(AttendanceAdministrationError, "ya no está disponible"):
            complete_administrative_exit(
                self.db,
                session.id,
                self.entry_at + timedelta(minutes=6),
                self.actor,
                "Segundo intento.",
            )

    def test_administrative_exit_rolls_back_everything_on_failure(self):
        session = self.incomplete_session()
        original_flush = self.db.flush
        calls = 0

        def fail_after_exit(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("fallo sintético")
            return original_flush(*args, **kwargs)

        with patch.object(self.db, "flush", side_effect=fail_after_exit):
            with self.assertRaisesRegex(RuntimeError, "fallo sintético"):
                complete_administrative_exit(
                    self.db,
                    session.id,
                    self.entry_at + timedelta(hours=1),
                    self.actor,
                    "Motivo válido.",
                    action_at=self.action_at,
                )
        self.assertEqual(self.db.get(SesionTrabajo, session.id).estado, "ABIERTA")
        self.assertEqual(self.db.scalar(select(func.count(MarcajeAsistencia.id))), 1)
        self.assertEqual(
            self.db.scalar(select(func.count(IntervencionSalidaAdministrativa.id))), 0
        )

    def test_incident_decision_is_final_and_preserves_factual_mark(self):
        incident, mark = self.incident()
        original_mark_time = mark.ocurrido_at
        resolved = decide_attendance_incident(
            self.db,
            incident.id,
            "aprobada",
            self.actor,
            comment="Revisión respaldada.",
            decided_at=self.action_at,
        )
        self.assertEqual(resolved.estado, "APROBADA")
        self.assertEqual(resolved.resuelto_por_id, self.actor.id)
        self.assertEqual(self.aware(resolved.resuelto_at), self.action_at)
        self.assertEqual(resolved.comentario_resolucion, "Revisión respaldada.")
        self.assertEqual(self.db.get(MarcajeAsistencia, mark.id).ocurrido_at, original_mark_time)
        with self.assertRaisesRegex(AttendanceAdministrationError, "decisión final"):
            decide_attendance_incident(
                self.db, incident.id, "RECHAZADA", self.actor
            )

    def test_incident_rejection_and_invalid_decision(self):
        incident, _ = self.incident()
        rejected = decide_attendance_incident(
            self.db,
            incident.id,
            "RECHAZADA",
            self.actor,
            decided_at=self.action_at,
        )
        self.assertEqual(rejected.estado, "RECHAZADA")
        with self.assertRaisesRegex(AttendanceAdministrationError, "APROBADA o RECHAZADA"):
            decide_attendance_incident(self.db, incident.id, "RESUELTA", self.actor)

    def test_incident_database_constraint_rejects_final_state_without_actor(self):
        incident, _ = self.incident()
        incident.estado = "APROBADA"
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_versioned_rates_resolve_individual_then_global_by_date(self):
        self.db.add(
            TarifaProvisionalAsistencia(
                trabajador_id=None,
                valor_clp=Decimal("30000"),
                vigente_desde=date(2026, 9, 1),
                origen="SISTEMA",
            )
        )
        self.db.commit()
        create_rate_version(
            self.db,
            effective_from=date(2026, 10, 1),
            amount_clp=35_000,
            actor=self.actor,
        )
        create_rate_version(
            self.db,
            effective_from=date(2026, 9, 15),
            amount_clp=40_000,
            actor=self.actor,
            worker_id=self.worker.id,
        )
        september = effective_rate_for_worker(
            self.db, self.worker.id, date(2026, 9, 20)
        )
        october = effective_rate_for_worker(
            self.db, self.worker.id, date(2026, 10, 20)
        )
        other = effective_rate_for_worker(
            self.db, self.other_worker.id, date(2026, 10, 20)
        )
        self.assertEqual((september.amount_clp, september.source), (40_000, INDIVIDUAL_RATE))
        self.assertEqual((october.amount_clp, october.source), (40_000, INDIVIDUAL_RATE))
        self.assertEqual((other.amount_clp, other.source), (35_000, GLOBAL_RATE))

    def test_rate_versions_are_unique_by_scope_and_validate_exact_clp(self):
        create_rate_version(
            self.db,
            effective_from=date(2026, 10, 1),
            amount_clp=30_000,
            actor=self.actor,
        )
        with self.assertRaisesRegex(AttendanceRateError, "Ya existe"):
            create_rate_version(
                self.db,
                effective_from=date(2026, 10, 1),
                amount_clp=31_000,
                actor=self.actor,
            )
        for amount in (0, -1, Decimal("30000.50"), True):
            with self.subTest(amount=amount), self.assertRaises(AttendanceRateError):
                create_rate_version(
                    self.db,
                    effective_from=date(2026, 11, 1),
                    amount_clp=amount,
                    actor=self.actor,
                )
        for invalid_date in ("2026-11-01", datetime(2026, 11, 1, tzinfo=timezone.utc)):
            with self.subTest(invalid_date=invalid_date), self.assertRaisesRegex(
                AttendanceRateError, "fecha operacional"
            ):
                create_rate_version(
                    self.db,
                    effective_from=invalid_date,
                    amount_clp=31_000,
                    actor=self.actor,
                )

    def test_rate_actor_and_worker_constraints_are_enforced(self):
        with self.assertRaisesRegex(AttendanceRateError, "trabajador no existe"):
            create_rate_version(
                self.db,
                effective_from=date(2026, 10, 1),
                amount_clp=30_000,
                actor=self.actor,
                worker_id=999_999,
            )
        self.db.add(
            TarifaProvisionalAsistencia(
                valor_clp=Decimal("30000"),
                vigente_desde=date(2026, 10, 1),
                origen="ADMIN",
                creado_por_id=None,
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
