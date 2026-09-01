import os
import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import (
    attendance_daily_rate_clp,
    attendance_day_shift_end,
    attendance_day_shift_start,
    attendance_late_tolerance_minutes,
    attendance_night_shift_end,
    attendance_night_shift_start,
)
from app.core.time import app_timezone
from app.database.base import Base
from app.models.attendance import (
    IncidenciaAsistencia,
    MarcajeAsistencia,
    SesionTrabajo,
    Turno,
)
from app.models.empresa import Empresa
from app.models.identity import Trabajador
from app.services.attendance_calendar_service import calendar_month


class AttendanceCalendarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_timezone = os.environ.get("APP_TIMEZONE")
        os.environ["APP_TIMEZONE"] = "America/Santiago"
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
        self.worker = Trabajador(empresa=company, nombres="Ana", apellidos="Pérez")
        self.other_worker = Trabajador(empresa=company, nombres="Beto", apellidos="Rojas")
        self.db.add_all([company, self.day_shift, self.night_shift, self.worker, self.other_worker])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        if self.previous_timezone is None:
            os.environ.pop("APP_TIMEZONE", None)
        else:
            os.environ["APP_TIMEZONE"] = self.previous_timezone

    @staticmethod
    def local_utc(day: date, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(day, time(hour, minute), tzinfo=app_timezone()).astimezone(timezone.utc)

    def add_session(
        self,
        worker: Trabajador,
        day: date,
        *,
        shift: Turno | None = None,
        entry: tuple[int, int] = (9, 0),
        exit_time: tuple[int, int] | None = (18, 0),
        incident: str | None = None,
    ) -> SesionTrabajo:
        selected_shift = shift or self.day_shift
        entry_at = self.local_utc(day, *entry)
        closed_at = self.local_utc(day, *exit_time) if exit_time else None
        session = SesionTrabajo(
            trabajador_id=worker.id,
            turno_id=selected_shift.id,
            fecha_operacional=day,
            estado="CERRADA" if closed_at else "ABIERTA",
            cerrado_at=closed_at,
        )
        self.db.add(session)
        self.db.flush()
        entry_mark = MarcajeAsistencia(
            sesion_id=session.id,
            tipo="ENTRADA",
            ocurrido_at=entry_at,
        )
        self.db.add(entry_mark)
        if closed_at:
            self.db.add(
                MarcajeAsistencia(
                    sesion_id=session.id,
                    tipo="SALIDA",
                    ocurrido_at=closed_at,
                )
            )
        self.db.flush()
        if incident:
            self.db.add(IncidenciaAsistencia(marcaje_id=entry_mark.id, tipo=incident))
        self.db.commit()
        return session

    def month_days(self, worker: Trabajador | None = None):
        _, days = calendar_month(
            self.db,
            (worker or self.worker).id,
            2026,
            9,
            today=date(2026, 9, 15),
        )
        return days

    def test_closed_entry_and_exit_marks_one_worked_date(self):
        self.add_session(self.worker, date(2026, 9, 1))
        day = self.month_days()[1]
        self.assertTrue(day.is_worked_date)
        self.assertEqual((day.status, day.session_count), ("TRABAJADO", 1))
        self.assertEqual(day.sessions[0].duration_minutes, 540)

    def test_open_session_is_review_not_complete_worked_date(self):
        self.add_session(self.worker, date(2026, 9, 2), exit_time=None)
        day = self.month_days()[2]
        self.assertFalse(day.is_worked_date)
        self.assertEqual((day.status, day.session_count), ("REVISION", 1))

    def test_multiple_closed_sessions_remain_one_worked_date(self):
        day = date(2026, 9, 3)
        self.add_session(self.worker, day, entry=(9, 0), exit_time=(13, 0))
        self.add_session(
            self.worker,
            day,
            shift=self.night_shift,
            entry=(19, 0),
            exit_time=(23, 0),
        )
        summary = self.month_days()[3]
        self.assertTrue(summary.is_worked_date)
        self.assertEqual(summary.session_count, 2)
        self.assertFalse(hasattr(summary, "payable_shifts"))

    def test_worker_projection_never_includes_another_worker(self):
        self.add_session(self.other_worker, date(2026, 9, 4))
        own_day = self.month_days()[4]
        other_day = self.month_days(self.other_worker)[4]
        self.assertEqual((own_day.session_count, own_day.is_worked_date), (0, False))
        self.assertEqual((other_day.session_count, other_day.is_worked_date), (1, True))

    def test_incident_and_out_of_range_preserve_worked_fact(self):
        self.add_session(self.worker, date(2026, 9, 5), incident="GPS_BAJA_PRECISION")
        self.add_session(self.worker, date(2026, 9, 6), incident="FUERA_RANGO")
        days = self.month_days()
        self.assertEqual((days[5].status, days[5].is_worked_date), ("REVISION", True))
        self.assertEqual((days[6].status, days[6].is_worked_date), ("FUERA_RANGO", True))

    def test_future_and_unplanned_days_never_infer_absence(self):
        days = self.month_days()
        self.assertEqual((days[10].status, days[10].label), ("NEUTRAL", "Sin estado determinable"))
        self.assertEqual((days[20].status, days[20].label), ("NEUTRAL", "Fecha futura"))
        self.assertNotIn("AUSENCIA", {item.status for item in days.values()})

    def test_shift_parameters_and_provisional_rate_are_centralized(self):
        self.assertEqual(attendance_day_shift_start(), time(9, 0))
        self.assertEqual(attendance_day_shift_end(), time(18, 0))
        self.assertEqual(attendance_night_shift_start(), time(19, 0))
        self.assertEqual(attendance_night_shift_end(), time(6, 0))
        self.assertEqual(attendance_late_tolerance_minutes(), 10)
        self.assertEqual(attendance_daily_rate_clp(), 30000)
        with patch.dict(os.environ, {"ATTENDANCE_DAY_SHIFT_START": "9am"}):
            with self.assertRaises(RuntimeError):
                attendance_day_shift_start()

    def test_late_start_requires_review_without_rejecting_worked_fact(self):
        self.add_session(
            self.worker,
            date(2026, 9, 7),
            entry=(9, 11),
            exit_time=(18, 0),
        )
        day = self.month_days()[7]
        self.assertEqual((day.status, day.is_worked_date), ("REVISION", True))
        self.assertTrue(day.sessions[0].is_late)
        self.assertEqual(day.sessions[0].incident_types, ())
        self.assertEqual(day.sessions[0].duration_minutes, 529)

    def test_exit_between_1801_and_1859_creates_no_overtime_or_incident(self):
        self.add_session(
            self.worker,
            date(2026, 9, 8),
            entry=(9, 0),
            exit_time=(18, 30),
        )
        day = self.month_days()[8]
        self.assertEqual((day.status, day.is_worked_date), ("TRABAJADO", True))
        self.assertEqual(day.sessions[0].incident_types, ())
        self.assertEqual(day.sessions[0].duration_minutes, 570)


if __name__ == "__main__":
    unittest.main()
