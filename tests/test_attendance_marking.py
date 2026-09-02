import os
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import (
    attendance_commune_boundary_tolerance_meters,
    attendance_max_gps_accuracy_meters,
    attendance_min_session_minutes,
)
from app.database.base import Base
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
from app.models.identity import Trabajador
from app.schemas.attendance import EvidenciaGPSCreate
from app.services.attendance_marking_service import (
    AttendanceMarkError,
    register_attendance_mark,
)


class AttendanceMarkingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_environment = {
            name: os.environ.get(name)
            for name in (
                "APP_TIMEZONE",
                "ATTENDANCE_MIN_SESSION_MINUTES",
                "ATTENDANCE_MAX_GPS_ACCURACY_METERS",
                "ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS",
            )
        }
        os.environ.update(
            {
                "APP_TIMEZONE": "America/Santiago",
                "ATTENDANCE_MIN_SESSION_MINUTES": "5",
                "ATTENDANCE_MAX_GPS_ACCURACY_METERS": "100",
                "ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS": "100",
            }
        )
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        company = Empresa(codigo="TEST", nombre="Empresa Test")
        self.day_shift = Turno(codigo="DIURNO", nombre="Diurno")
        self.night_shift = Turno(codigo="NOCTURNO", nombre="Nocturno")
        self.place = LugarTrabajo(
            nombre="Zona Test",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=Decimal("-33.000000"),
            longitud=Decimal("-70.000000"),
            radio_metros=Decimal("150.00"),
        )
        self.db.add_all([company, self.day_shift, self.night_shift, self.place])
        self.db.flush()
        self.worker = Trabajador(
            empresa_id=company.id, nombres="Ana", apellidos="Prueba", activo=True
        )
        self.other_worker = Trabajador(
            empresa_id=company.id, nombres="Beto", apellidos="Prueba", activo=True
        )
        self.db.add_all([self.worker, self.other_worker])
        self.db.commit()
        self.start = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        for name, value in self.previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    @staticmethod
    def evidence(
        *,
        latitude: str = "-33.000000",
        longitude: str = "-70.000000",
        accuracy: str = "20.00",
        captured_at: datetime | None = None,
    ) -> EvidenciaGPSCreate:
        return EvidenciaGPSCreate(
            latitud=Decimal(latitude),
            longitud=Decimal(longitude),
            precision_m=Decimal(accuracy),
            capturada_at=captured_at,
        )

    def mark(
        self,
        mark_type: str,
        when: datetime,
        *,
        worker: Trabajador | None = None,
        evidence: EvidenciaGPSCreate | None = None,
        shift_id: int | None = None,
    ) -> MarcajeAsistencia:
        selected_shift = self.day_shift.id if shift_id is None else shift_id
        with patch(
            "app.services.attendance_marking_service.utc_now", return_value=when
        ):
            return register_attendance_mark(
                self.db,
                worker or self.worker,
                mark_type,
                evidence or self.evidence(),
                shift_id=selected_shift,
            )

    @staticmethod
    def aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    def test_valid_entry_uses_server_time_worker_and_preserves_gps(self):
        captured = self.start - timedelta(seconds=12)
        mark = self.mark("ENTRADA", self.start, evidence=self.evidence(captured_at=captured))
        stored = self.db.get(MarcajeAsistencia, mark.id)
        gps = self.db.scalar(
            select(EvidenciaGPSMarcaje).where(EvidenciaGPSMarcaje.marcaje_id == mark.id)
        )
        session = self.db.get(SesionTrabajo, stored.sesion_id)
        self.assertEqual(stored.tipo, "ENTRADA")
        self.assertEqual(self.aware(stored.ocurrido_at), self.start)
        self.assertEqual(session.trabajador_id, self.worker.id)
        self.assertEqual(session.fecha_operacional, date(2026, 8, 31))
        self.assertEqual((gps.latitud, gps.longitud, gps.precision_m), (Decimal("-33.000000"), Decimal("-70.000000"), Decimal("20.00")))
        self.assertEqual(self.aware(gps.capturada_at), captured)

    def test_duplicate_entry_is_rejected_with_open_session(self):
        self.mark("ENTRADA", self.start)
        with self.assertRaisesRegex(AttendanceMarkError, "sesión abierta"):
            self.mark("ENTRADA", self.start + timedelta(minutes=10))
        self.assertEqual(self.db.scalar(select(func.count(SesionTrabajo.id))), 1)

    def test_exit_without_open_session_is_rejected(self):
        with self.assertRaisesRegex(AttendanceMarkError, "no tiene una sesión abierta"):
            self.mark("SALIDA", self.start)

    def test_exit_before_minimum_is_rejected_without_partial_event(self):
        entry = self.mark("ENTRADA", self.start)
        with self.assertRaisesRegex(AttendanceMarkError, "al menos 5 minutos"):
            self.mark("SALIDA", self.start + timedelta(minutes=4, seconds=59))
        self.assertEqual(
            self.db.scalar(select(func.count(MarcajeAsistencia.id))), 1
        )
        self.assertEqual(self.db.get(SesionTrabajo, entry.sesion_id).estado, "ABIERTA")

    def test_exit_at_minimum_closes_session_and_duplicate_exit_is_rejected(self):
        entry = self.mark("ENTRADA", self.start)
        exit_mark = self.mark("SALIDA", self.start + timedelta(minutes=5))
        session = self.db.get(SesionTrabajo, entry.sesion_id)
        self.assertEqual((exit_mark.tipo, session.estado), ("SALIDA", "CERRADA"))
        with self.assertRaisesRegex(AttendanceMarkError, "no tiene una sesión abierta"):
            self.mark("SALIDA", self.start + timedelta(minutes=6))

    def test_second_session_is_allowed_on_same_operational_day(self):
        self.mark("ENTRADA", self.start)
        self.mark("SALIDA", self.start + timedelta(hours=5))
        self.mark("ENTRADA", self.start + timedelta(hours=6))
        sessions = list(
            self.db.scalars(
                select(SesionTrabajo).order_by(SesionTrabajo.id)
            ).all()
        )
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].fecha_operacional, sessions[1].fecha_operacional)
        self.assertEqual([item.estado for item in sessions], ["CERRADA", "ABIERTA"])

    def test_night_session_crosses_midnight_without_changing_operational_date(self):
        entry_time = datetime(2026, 9, 1, 3, 58, tzinfo=timezone.utc)
        entry = self.mark("ENTRADA", entry_time, shift_id=self.night_shift.id)
        self.mark("SALIDA", entry_time + timedelta(minutes=12))
        session = self.db.get(SesionTrabajo, entry.sesion_id)
        self.assertEqual(session.fecha_operacional, date(2026, 8, 31))
        self.assertEqual(session.estado, "CERRADA")

    def test_worker_ownership_prevents_closing_another_workers_session(self):
        entry = self.mark("ENTRADA", self.start)
        with self.assertRaisesRegex(AttendanceMarkError, "no tiene una sesión abierta"):
            self.mark("SALIDA", self.start + timedelta(minutes=6), worker=self.other_worker)
        self.assertEqual(self.db.get(SesionTrabajo, entry.sesion_id).estado, "ABIERTA")

    def test_missing_gps_is_rejected(self):
        with patch("app.services.attendance_marking_service.utc_now", return_value=self.start):
            with self.assertRaisesRegex(AttendanceMarkError, "requiere evidencia GPS"):
                register_attendance_mark(
                    self.db, self.worker, "ENTRADA", None, shift_id=self.day_shift.id
                )

    def test_invalid_coordinates_are_rejected(self):
        for latitude, longitude in (("90.1", "-70"), ("-90.1", "-70"), ("-33", "180.1"), ("-33", "-180.1")):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValidationError):
                    self.evidence(latitude=latitude, longitude=longitude)

    def test_zero_zero_coordinates_are_rejected(self):
        with self.assertRaisesRegex(ValidationError, "0,0"):
            self.evidence(latitude="0", longitude="0")

    def test_non_positive_accuracy_is_rejected(self):
        for accuracy in ("0", "-0.01"):
            with self.subTest(accuracy=accuracy), self.assertRaises(ValidationError):
                self.evidence(accuracy=accuracy)

    def test_low_accuracy_registers_mark_and_incident(self):
        mark = self.mark("ENTRADA", self.start, evidence=self.evidence(accuracy="100.01"))
        evaluation = self.db.scalar(
            select(EvaluacionGeograficaMarcaje).where(
                EvaluacionGeograficaMarcaje.marcaje_id == mark.id
            )
        )
        incidents = set(
            self.db.scalars(
                select(IncidenciaAsistencia.tipo).where(
                    IncidenciaAsistencia.marcaje_id == mark.id
                )
            ).all()
        )
        self.assertEqual(evaluation.estado_precision, "BAJA_PRECISION")
        self.assertIn("GPS_BAJA_PRECISION", incidents)

    def test_out_of_range_is_registered_with_nearest_place_and_incident(self):
        nearer = LugarTrabajo(
            nombre="Zona Test Cercana",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=Decimal("-34.000000"),
            longitud=Decimal("-71.000000"),
            radio_metros=Decimal("10.00"),
        )
        self.db.add(nearer)
        self.db.commit()
        mark = self.mark(
            "ENTRADA",
            self.start,
            evidence=self.evidence(latitude="-34.001000", longitude="-71.001000"),
        )
        evaluation = self.db.scalar(
            select(EvaluacionGeograficaMarcaje).where(
                EvaluacionGeograficaMarcaje.marcaje_id == mark.id
            )
        )
        self.assertEqual(evaluation.lugar_detectado_id, nearer.id)
        self.assertEqual(evaluation.estado_geocerca, "FUERA_RANGO")
        self.assertGreater(evaluation.distancia_m, evaluation.radio_m_aplicado)
        self.assertEqual(
            self.db.scalar(
                select(IncidenciaAsistencia.tipo).where(
                    IncidenciaAsistencia.marcaje_id == mark.id
                )
            ),
            "FUERA_RANGO",
        )

    def test_failure_rolls_back_session_and_mark(self):
        with patch("app.services.attendance_marking_service.utc_now", return_value=self.start), patch.object(
            self.db, "flush", side_effect=RuntimeError("fallo sintético")
        ):
            with self.assertRaisesRegex(RuntimeError, "fallo sintético"):
                register_attendance_mark(
                    self.db,
                    self.worker,
                    "ENTRADA",
                    self.evidence(),
                    shift_id=self.day_shift.id,
                )
        self.assertEqual(self.db.scalar(select(func.count(SesionTrabajo.id))), 0)
        self.assertEqual(self.db.scalar(select(func.count(MarcajeAsistencia.id))), 0)

    def test_partial_unique_index_rejects_two_open_sessions(self):
        first = SesionTrabajo(
            trabajador_id=self.worker.id,
            turno_id=self.day_shift.id,
            fecha_operacional=date(2026, 8, 31),
            estado="ABIERTA",
        )
        self.db.add(first)
        self.db.commit()
        self.db.add(
            SesionTrabajo(
                trabajador_id=self.worker.id,
                turno_id=self.night_shift.id,
                fecha_operacional=date(2026, 8, 31),
                estado="ABIERTA",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_attendance_thresholds_are_centralized_and_strict(self):
        self.assertEqual(attendance_min_session_minutes(), 5)
        self.assertEqual(attendance_max_gps_accuracy_meters(), 100)
        self.assertEqual(attendance_commune_boundary_tolerance_meters(), 100)
        with patch.dict(os.environ, {"ATTENDANCE_MIN_SESSION_MINUTES": "0"}):
            with self.assertRaises(RuntimeError):
                attendance_min_session_minutes()
        with patch.dict(os.environ, {"ATTENDANCE_MAX_GPS_ACCURACY_METERS": "invalid"}):
            with self.assertRaises(RuntimeError):
                attendance_max_gps_accuracy_meters()
        with patch.dict(os.environ, {"ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS": "0"}):
            with self.assertRaises(RuntimeError):
                attendance_commune_boundary_tolerance_meters()


if __name__ == "__main__":
    unittest.main()
