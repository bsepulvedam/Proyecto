import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from pyproj.enums import TransformDirection
from shapely.geometry import Polygon, mapping
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.attendance import (
    AsignacionTrabajadorLugar,
    EvaluacionGeograficaMarcaje,
    IncidenciaAsistencia,
    LugarTrabajo,
    MarcajeAsistencia,
    Turno,
)
from app.models.empresa import Empresa
from app.models.identity import Trabajador, Usuario
from app.schemas.attendance import EvidenciaGPSCreate
from app.services.attendance_geofence_service import (
    COMMUNE_GEOJSON_PATH,
    GeoEvaluationResult,
    GeofenceConfigurationError,
    evaluate_geolocation,
    load_commune_catalog,
)
from app.services.attendance_marking_service import register_attendance_mark


def evidence(latitude: float, longitude: float) -> EvidenciaGPSCreate:
    return EvidenciaGPSCreate(
        latitud=Decimal(str(latitude)).quantize(Decimal("0.000000001")),
        longitud=Decimal(str(longitude)).quantize(Decimal("0.000000001")),
        precision_m=Decimal("10"),
    )


def commune_place(code: str, *, place_id: int = 1, priority: int = 100, active: bool = True) -> LugarTrabajo:
    return LugarTrabajo(
        id=place_id,
        nombre=f"Comuna {code}",
        tipo="TERRENO",
        tipo_geocerca="COMUNA",
        codigo_comuna=code,
        latitud=Decimal("-33"),
        longitud=Decimal("-70"),
        prioridad_geocerca=priority,
        activo=active,
    )


class AttendanceGeofenceRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "communes.geojson"
        self.write_catalog()

    def tearDown(self) -> None:
        load_commune_catalog.cache_clear()
        self.temp.cleanup()

    def write_catalog(self, *, overlap: bool = False, ambiguous_names: bool = False) -> None:
        features = []
        for index in range(13):
            code = f"{index + 1:05d}"
            if index == 0 or (index == 1 and overlap):
                west, south, east, north = -70.01, -33.01, -69.99, -32.99
            elif index == 1:
                west, south, east, north = -69.51, -33.01, -69.49, -32.99
            else:
                offset = index * 0.03
                west, south, east, north = -72 + offset, -36.01, -71.99 + offset, -35.99
            name = "Nombre repetido" if ambiguous_names and index in {0, 1} else f"Comuna {index + 1}"
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "CUT_COM": code,
                        "nombre_oficial_fuente": name,
                        "nombre_presentacion": name,
                    },
                    "geometry": mapping(Polygon([(west, south), (west, north), (east, north), (east, south), (west, south)])),
                }
            )
        self.path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "metadata": {"derived_crs": "EPSG:4326", "geometry_version": "TEST-v1"},
                    "features": features,
                }
            ),
            encoding="utf-8",
        )
        load_commune_catalog.cache_clear()

    def outside_first_commune(self, meters: float) -> EvidenciaGPSCreate:
        commune = load_commune_catalog(str(self.path)).communes["00001"]
        x, y = commune.to_metric.transform(-69.99, -33.0)
        longitude, latitude = commune.to_metric.transform(
            x + meters, y, direction=TransformDirection.INVERSE
        )
        return evidence(latitude, longitude)

    def test_versioned_real_catalog_has_exact_approved_identity(self):
        self.assertEqual(COMMUNE_GEOJSON_PATH.stat().st_size, 656212)
        self.assertEqual(
            hashlib.sha256(COMMUNE_GEOJSON_PATH.read_bytes()).hexdigest(),
            "4962c9a4a931002a51872f0ef9dfbf541c088d8419fc671d02b3a304d213a638",
        )
        catalog = load_commune_catalog(str(COMMUNE_GEOJSON_PATH))
        self.assertEqual(len(catalog.communes), 13)
        self.assertEqual(set(catalog.communes), {"06110", "08301", "13102", "13103", "13107", "13110", "13112", "13117", "13119", "13121", "13301", "13404", "16301"})
        self.assertEqual(catalog.communes["08301"].source_name, "Los Angeles")
        self.assertEqual(catalog.communes["08301"].display_name, "Los \u00c1ngeles")

    def test_commune_border_tolerance_and_outside_states(self):
        place = commune_place("00001")
        cases = (
            (evidence(-33.0, -69.99), "DENTRO_RANGO"),
            (self.outside_first_commune(50), "DENTRO_TOLERANCIA"),
            (self.outside_first_commune(101), "FUERA_RANGO"),
        )
        for point, expected in cases:
            with self.subTest(expected=expected):
                result = evaluate_geolocation(point, [place], commune_tolerance_m=100, dataset_path=self.path)
                self.assertEqual(result.geofence_status, expected)
                self.assertEqual(result.geofence_type, "COMUNA")

    def test_inactive_commune_is_not_applicable(self):
        result = evaluate_geolocation(evidence(-33, -70), [commune_place("00001", active=False)], dataset_path=self.path)
        self.assertEqual(result.geofence_status, "SIN_ZONA_CONFIGURADA")

    def test_overlapping_tolerances_use_priority_then_id(self):
        self.write_catalog(overlap=True)
        point = self.outside_first_commune(50)
        first = commune_place("00001", place_id=20, priority=20)
        second = commune_place("00002", place_id=30, priority=10)
        result = evaluate_geolocation(point, [first, second], dataset_path=self.path)
        self.assertEqual((result.geofence_status, result.place_id), ("DENTRO_TOLERANCIA", 30))
        second.prioridad_geocerca = 20
        result = evaluate_geolocation(point, [first, second], dataset_path=self.path)
        self.assertEqual(result.place_id, 20)

    def test_radio_and_commune_coexist_with_deterministic_priority(self):
        commune = commune_place("00001", place_id=10, priority=20)
        radio = LugarTrabajo(
            id=11,
            nombre="Radio",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=Decimal("-33"),
            longitud=Decimal("-70"),
            radio_metros=Decimal("500"),
            prioridad_geocerca=10,
            activo=True,
        )
        result = evaluate_geolocation(evidence(-33, -70), [commune, radio], dataset_path=self.path)
        self.assertEqual((result.place_id, result.geofence_type), (11, "RADIO"))

    def test_status_precedes_priority_and_margin_breaks_equal_priority(self):
        tolerance = commune_place("00001", place_id=10, priority=1)
        inside_small = LugarTrabajo(
            id=11,
            nombre="Radio pequeno",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=Decimal("-33"),
            longitud=Decimal("-69.9895"),
            radio_metros=Decimal("100"),
            prioridad_geocerca=999,
            activo=True,
        )
        point = self.outside_first_commune(50)
        result = evaluate_geolocation(point, [tolerance, inside_small], dataset_path=self.path)
        self.assertEqual((result.geofence_status, result.place_id), ("DENTRO_RANGO", 11))

        inside_large = LugarTrabajo(
            id=12,
            nombre="Radio grande",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=inside_small.latitud,
            longitud=inside_small.longitud,
            radio_metros=Decimal("200"),
            prioridad_geocerca=999,
            activo=True,
        )
        result = evaluate_geolocation(point, [inside_small, inside_large], dataset_path=self.path)
        self.assertEqual(result.place_id, 12)

    def test_dataset_missing_corrupt_and_unknown_code_fail_safely(self):
        place = commune_place("00001")
        with self.assertRaises(GeofenceConfigurationError):
            evaluate_geolocation(evidence(-33, -70), [place], dataset_path=Path(self.temp.name) / "missing.json")
        corrupt = Path(self.temp.name) / "corrupt.json"
        corrupt.write_text("{", encoding="utf-8")
        with self.assertRaises(GeofenceConfigurationError):
            evaluate_geolocation(evidence(-33, -70), [place], dataset_path=corrupt)
        invalid_geometry = Path(self.temp.name) / "invalid-geometry.json"
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["features"][0]["geometry"] = None
        invalid_geometry.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(GeofenceConfigurationError):
            evaluate_geolocation(evidence(-33, -70), [place], dataset_path=invalid_geometry)
        with self.assertRaises(GeofenceConfigurationError):
            evaluate_geolocation(evidence(-33, -70), [commune_place("99999")], dataset_path=self.path)

    def test_geometry_selection_uses_code_not_ambiguous_name(self):
        self.write_catalog(ambiguous_names=True)
        result = evaluate_geolocation(evidence(-33, -69.50), [commune_place("00002", place_id=2)], dataset_path=self.path)
        self.assertEqual((result.place_id, result.geofence_status), (2, "DENTRO_RANGO"))


class AttendanceGeofencePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        company = Empresa(codigo="TEST", nombre="Empresa Test")
        self.shift = Turno(codigo="DIURNO", nombre="Diurno")
        self.worker = Trabajador(empresa=company, nombres="Ana", apellidos="Prueba", activo=True)
        self.admin = Usuario(username="admin@example.test", password_hash="not-a-real-hash")
        self.colina = LugarTrabajo(
            nombre="Colina",
            tipo="TERRENO",
            tipo_geocerca="COMUNA",
            codigo_comuna="13301",
            latitud=Decimal("-33.2023"),
            longitud=Decimal("-70.6749"),
            prioridad_geocerca=100,
        )
        self.old_radio = LugarTrabajo(
            nombre="Asignación histórica",
            tipo="TERRENO",
            tipo_geocerca="RADIO",
            latitud=Decimal("-36"),
            longitud=Decimal("-72"),
            radio_metros=Decimal("10"),
            prioridad_geocerca=1,
        )
        self.db.add_all([company, self.shift, self.worker, self.admin, self.colina, self.old_radio])
        self.db.flush()
        self.db.add(
            AsignacionTrabajadorLugar(
                trabajador_id=self.worker.id,
                lugar_id=self.old_radio.id,
                desde=datetime(2025, 1, 1, tzinfo=timezone.utc),
                hasta=datetime(2025, 2, 1, tzinfo=timezone.utc),
                activo=False,
                creado_por_id=self.admin.id,
            )
        )
        self.db.commit()
        self.when = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_worker_needs_no_assignment_and_historical_assignment_is_ignored(self):
        with patch("app.services.attendance_marking_service.utc_now", return_value=self.when):
            mark = register_attendance_mark(
                self.db,
                self.worker,
                "ENTRADA",
                evidence(-33.2023, -70.6749),
                shift_id=self.shift.id,
            )
        evaluation = self.db.scalar(select(EvaluacionGeograficaMarcaje).where(EvaluacionGeograficaMarcaje.marcaje_id == mark.id))
        self.assertEqual((evaluation.lugar_detectado_id, evaluation.estado_geocerca), (self.colina.id, "DENTRO_RANGO"))
        self.assertEqual(evaluation.tipo_geocerca_aplicado, "COMUNA")
        self.assertEqual(evaluation.geometria_version, "SUBDERE_DPA_2023_2023-08-03")

    def test_outside_all_zones_persists_mark_and_incident(self):
        self.old_radio.activo = False
        self.db.commit()
        with patch("app.services.attendance_marking_service.utc_now", return_value=self.when):
            mark = register_attendance_mark(
                self.db,
                self.worker,
                "ENTRADA",
                evidence(-40, -73),
                shift_id=self.shift.id,
            )
        evaluation = self.db.scalar(select(EvaluacionGeograficaMarcaje).where(EvaluacionGeograficaMarcaje.marcaje_id == mark.id))
        self.assertEqual(evaluation.estado_geocerca, "FUERA_RANGO")
        self.assertEqual(self.db.scalar(select(IncidenciaAsistencia.tipo).where(IncidenciaAsistencia.marcaje_id == mark.id)), "FUERA_RANGO")
        self.assertEqual(self.db.scalar(select(func.count(MarcajeAsistencia.id))), 1)

    def test_tolerance_result_is_persisted_without_incident(self):
        result = GeoEvaluationResult(
            place_id=self.colina.id,
            distance_m=Decimal("50.00"),
            radius_m=None,
            tolerance_m=Decimal("100.00"),
            geofence_type="COMUNA",
            geometry_version="TEST-v1",
            geofence_status="DENTRO_TOLERANCIA",
            accuracy_status="ACEPTABLE",
            max_accuracy_m=Decimal("100.00"),
        )
        with patch("app.services.attendance_marking_service.utc_now", return_value=self.when), patch(
            "app.services.attendance_marking_service.evaluate_geolocation", return_value=result
        ):
            mark = register_attendance_mark(
                self.db,
                self.worker,
                "ENTRADA",
                evidence(-33.2, -70.67),
                shift_id=self.shift.id,
            )
        evaluation = self.db.scalar(select(EvaluacionGeograficaMarcaje).where(EvaluacionGeograficaMarcaje.marcaje_id == mark.id))
        self.assertEqual(evaluation.estado_geocerca, "DENTRO_TOLERANCIA")
        self.assertEqual(evaluation.tolerancia_m_aplicada, Decimal("100.00"))
        self.assertIsNone(self.db.scalar(select(IncidenciaAsistencia.id).where(IncidenciaAsistencia.marcaje_id == mark.id)))


if __name__ == "__main__":
    unittest.main()
