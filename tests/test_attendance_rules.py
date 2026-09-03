import os
import unittest
from dataclasses import replace
from datetime import date, datetime, time, timezone

from app.core.time import app_timezone
from app.services.attendance_rules_service import (
    DAY_SHIFT,
    EARLY_ENTRY,
    EARLY_EXIT,
    GLOBAL_RATE,
    INDIVIDUAL_RATE,
    LATE_ENTRY,
    LATE_EXIT,
    NIGHT_SHIFT,
    ON_TIME,
    AttendanceRuleError,
    AttendanceSessionFacts,
    ProvisionalRateVersion,
    configured_shift_references,
    project_period,
    project_session,
    resolve_effective_rate,
)


class AttendanceRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_timezone = os.environ.get("APP_TIMEZONE")
        os.environ["APP_TIMEZONE"] = "America/Santiago"

    def tearDown(self) -> None:
        if self.previous_timezone is None:
            os.environ.pop("APP_TIMEZONE", None)
        else:
            os.environ["APP_TIMEZONE"] = self.previous_timezone

    @staticmethod
    def local_utc(day: date, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(
            day,
            time(hour, minute),
            tzinfo=app_timezone(),
        ).astimezone(timezone.utc)

    def facts(
        self,
        session_id: int,
        operational_day: date,
        *,
        shift_code: str = DAY_SHIFT,
        entry: tuple[date, int, int] | None = None,
        exit_time: tuple[date, int, int] | None = None,
        incidents: tuple[str, ...] = (),
    ) -> AttendanceSessionFacts:
        entry_value = entry or (operational_day, 9, 0)
        return AttendanceSessionFacts(
            session_id=session_id,
            worker_id=7,
            operational_date=operational_day,
            shift_code=shift_code,
            shift_name="Diurno" if shift_code == DAY_SHIFT else "Nocturno",
            recorded_state="CERRADA" if exit_time else "ABIERTA",
            entry_at=self.local_utc(*entry_value) if entry_value else None,
            exit_at=self.local_utc(*exit_time) if exit_time else None,
            incident_count=len(incidents),
            incident_types=incidents,
        )

    @staticmethod
    def global_rate(
        amount: int = 30000,
        *,
        effective_from: date = date.min,
        version_id: int = 1,
    ):
        return ProvisionalRateVersion(
            version_id=version_id,
            effective_from=effective_from,
            amount_clp=amount,
        )

    def test_confirmed_shift_references_end_night_at_five(self):
        references = configured_shift_references()
        self.assertEqual(
            (references[DAY_SHIFT].start, references[DAY_SHIFT].end),
            (time(9, 0), time(18, 0)),
        )
        self.assertEqual(
            (references[NIGHT_SHIFT].start, references[NIGHT_SHIFT].end),
            (time(19, 0), time(5, 0)),
        )
        self.assertTrue(references[NIGHT_SHIFT].crosses_midnight)

    def test_day_entry_and_exit_boundaries_are_deterministic(self):
        day = date(2026, 9, 2)
        cases = (
            ((day, 8, 30), (day, 17, 59), EARLY_ENTRY, EARLY_EXIT),
            ((day, 9, 0), (day, 18, 0), ON_TIME, ON_TIME),
            ((day, 9, 10), (day, 18, 30), ON_TIME, LATE_EXIT),
            ((day, 9, 11), (day, 18, 1), LATE_ENTRY, LATE_EXIT),
        )
        for index, (entry, exit_time, expected_entry, expected_exit) in enumerate(cases, 1):
            with self.subTest(entry=entry, exit=exit_time):
                projection = project_session(
                    self.facts(index, day, entry=entry, exit_time=exit_time)
                )
                self.assertEqual(projection.entry_situation, expected_entry)
                self.assertEqual(projection.exit_situation, expected_exit)

    def test_night_shift_uses_factual_turn_and_crosses_midnight(self):
        day = date(2026, 9, 2)
        projection = project_session(
            self.facts(
                1,
                day,
                shift_code=NIGHT_SHIFT,
                entry=(day, 18, 30),
                exit_time=(date(2026, 9, 3), 4, 30),
            )
        )
        self.assertEqual(projection.shift_code, NIGHT_SHIFT)
        self.assertEqual(projection.operational_date, day)
        self.assertEqual(projection.entry_time.strftime("%d/%m %H:%M"), "02/09 18:30")
        self.assertEqual(projection.exit_time.strftime("%d/%m %H:%M"), "03/09 04:30")
        self.assertEqual(projection.entry_situation, EARLY_ENTRY)
        self.assertEqual(projection.exit_situation, EARLY_EXIT)
        self.assertEqual(projection.duration_minutes, 600)

    def test_night_entry_and_exit_reference_boundaries(self):
        day = date(2026, 9, 2)
        cases = (
            ((day, 19, 0), (date(2026, 9, 3), 5, 0), ON_TIME, ON_TIME),
            ((day, 19, 10), (date(2026, 9, 3), 5, 1), ON_TIME, LATE_EXIT),
            ((day, 20, 30), (date(2026, 9, 3), 5, 30), LATE_ENTRY, LATE_EXIT),
        )
        for index, (entry, exit_time, expected_entry, expected_exit) in enumerate(cases, 1):
            with self.subTest(entry=entry, exit=exit_time):
                projection = project_session(
                    self.facts(
                        index,
                        day,
                        shift_code=NIGHT_SHIFT,
                        entry=entry,
                        exit_time=exit_time,
                    )
                )
                self.assertEqual(projection.entry_situation, expected_entry)
                self.assertEqual(projection.exit_situation, expected_exit)

    def test_atypical_five_thirty_entry_keeps_factual_shift(self):
        day = date(2026, 9, 2)
        projection = project_session(
            self.facts(
                1,
                day,
                shift_code=DAY_SHIFT,
                entry=(day, 5, 30),
                exit_time=(day, 18, 0),
            )
        )
        self.assertEqual(projection.shift_code, DAY_SHIFT)
        self.assertEqual(projection.entry_time.strftime("%H:%M"), "05:30")
        self.assertEqual(projection.entry_situation, EARLY_ENTRY)

    def test_incomplete_session_is_activity_and_requires_review(self):
        projection = project_session(self.facts(1, date(2026, 9, 2)))
        self.assertTrue(projection.has_activity)
        self.assertTrue(projection.is_incomplete)
        self.assertFalse(projection.is_closed_valid)
        self.assertTrue(projection.requires_review)

    def test_closed_session_must_respect_five_minute_minimum(self):
        day = date(2026, 9, 2)
        projection = project_session(
            self.facts(
                1,
                day,
                entry=(day, 9, 0),
                exit_time=(day, 9, 4),
            )
        )
        self.assertEqual(projection.duration_minutes, 4)
        self.assertFalse(projection.meets_minimum_duration)
        self.assertFalse(projection.is_closed_valid)

    def test_same_shift_sessions_create_one_payable_shift(self):
        day = date(2026, 9, 2)
        facts = (
            self.facts(1, day, entry=(day, 9, 0), exit_time=(day, 12, 0)),
            self.facts(2, day, entry=(day, 13, 0), exit_time=(day, 18, 0)),
        )
        period = project_period(7, facts, (self.global_rate(),))
        self.assertEqual(period.activity_days, 1)
        self.assertEqual(period.payable_shifts, 1)
        self.assertEqual(period.double_shift_days, 0)
        self.assertEqual(period.provisional_total_clp, 30000)

    def test_day_and_night_create_two_payable_shifts_and_one_double(self):
        day = date(2026, 9, 2)
        facts = (
            self.facts(1, day, exit_time=(day, 18, 0)),
            self.facts(
                2,
                day,
                shift_code=NIGHT_SHIFT,
                entry=(day, 19, 0),
                exit_time=(date(2026, 9, 3), 5, 0),
            ),
        )
        period = project_period(7, facts, (self.global_rate(),))
        self.assertEqual(period.activity_days, 1)
        self.assertEqual(period.completed_worked_days, 1)
        self.assertEqual(period.payable_shifts, 2)
        self.assertEqual(period.double_shift_days, 1)
        self.assertEqual(period.provisional_total_clp, 60000)

    def test_incomplete_and_incident_keep_provisional_payability(self):
        day = date(2026, 9, 2)
        period = project_period(
            7,
            (self.facts(1, day, incidents=("FUERA_RANGO", "FUERA_RANGO")),),
            (self.global_rate(),),
        )
        self.assertEqual(period.incomplete_sessions, 1)
        self.assertEqual(period.incident_count, 2)
        self.assertEqual(period.days[0].sessions[0].incident_types, ("FUERA_RANGO",))
        self.assertEqual(period.payable_shifts, 1)
        self.assertEqual(period.provisional_total_clp, 30000)

    def test_individual_rate_precedes_global_and_versions_are_historical(self):
        versions = (
            self.global_rate(30000, effective_from=date(2026, 9, 1), version_id=1),
            self.global_rate(35000, effective_from=date(2026, 10, 1), version_id=2),
            ProvisionalRateVersion(
                version_id=3,
                effective_from=date(2026, 9, 15),
                amount_clp=40000,
                worker_id=7,
            ),
        )
        september_early = resolve_effective_rate(date(2026, 9, 10), 7, versions)
        september_late = resolve_effective_rate(date(2026, 9, 20), 7, versions)
        october_other_worker = resolve_effective_rate(date(2026, 10, 2), 8, versions)
        self.assertEqual(
            (september_early.amount_clp, september_early.source),
            (30000, GLOBAL_RATE),
        )
        self.assertEqual(
            (september_late.amount_clp, september_late.source),
            (40000, INDIVIDUAL_RATE),
        )
        self.assertEqual(
            (october_other_worker.amount_clp, october_other_worker.source),
            (35000, GLOBAL_RATE),
        )

    def test_rate_and_worker_invariants_fail_closed(self):
        day = date(2026, 9, 2)
        with self.assertRaises(AttendanceRuleError):
            resolve_effective_rate(day, 7, ())
        with self.assertRaises(AttendanceRuleError):
            resolve_effective_rate(day, 7, (self.global_rate(0),))
        mixed_worker = replace(
            self.facts(1, day, exit_time=(day, 18, 0)),
            worker_id=8,
        )
        with self.assertRaises(AttendanceRuleError):
            project_period(7, (mixed_worker,), (self.global_rate(),))

    def test_unknown_shift_is_visible_but_not_silently_paid(self):
        day = date(2026, 9, 2)
        unknown = self.facts(
            1,
            day,
            shift_code="ESPECIAL",
            exit_time=(day, 18, 0),
        )
        projection = project_session(unknown)
        self.assertTrue(projection.has_activity)
        self.assertIsNone(projection.entry_situation)
        with self.assertRaisesRegex(AttendanceRuleError, "sin regla pagable"):
            project_period(7, (unknown,), (self.global_rate(),))


if __name__ == "__main__":
    unittest.main()
