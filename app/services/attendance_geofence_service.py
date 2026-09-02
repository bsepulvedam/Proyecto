from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable, Mapping

from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
from shapely.errors import ShapelyError
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from app.core.config import (
    attendance_commune_boundary_tolerance_meters,
    attendance_max_gps_accuracy_meters,
)
from app.models.attendance import LugarTrabajo
from app.schemas.attendance import EvidenciaGPSCreate

EARTH_RADIUS_METERS = 6_371_000
COMMUNE_GEOJSON_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "geofences"
    / "subdere_dpa_2023_approved_communes.geojson"
)
EXPECTED_COMMUNE_COUNT = 13
EXPECTED_COMMUNE_GEOJSON_SHA256 = "4962c9a4a931002a51872f0ef9dfbf541c088d8419fc671d02b3a304d213a638"


class GeofenceConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommuneGeometry:
    code: str
    source_name: str
    display_name: str
    geometry_wgs84: BaseGeometry
    geometry_metric: BaseGeometry
    to_metric: Transformer


@dataclass(frozen=True)
class CommuneCatalog:
    geometry_version: str
    communes: Mapping[str, CommuneGeometry]


@dataclass(frozen=True)
class GeoEvaluationResult:
    place_id: int | None
    distance_m: Decimal | None
    radius_m: Decimal | None
    tolerance_m: Decimal | None
    geofence_type: str | None
    geometry_version: str | None
    geofence_status: str
    accuracy_status: str
    max_accuracy_m: Decimal


@dataclass(frozen=True)
class _Candidate:
    place: LugarTrabajo
    status: str
    distance_m: Decimal
    margin_m: Decimal
    radius_m: Decimal | None
    tolerance_m: Decimal | None
    geofence_type: str
    geometry_version: str | None


def _decimal_meters(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def haversine_distance_m(
    latitude_a: Decimal,
    longitude_a: Decimal,
    latitude_b: Decimal,
    longitude_b: Decimal,
) -> Decimal:
    lat_a, lon_a, lat_b, lon_b = map(
        radians, map(float, (latitude_a, longitude_a, latitude_b, longitude_b))
    )
    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    value = sin(delta_lat / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
    return _decimal_meters(2 * EARTH_RADIUS_METERS * asin(sqrt(value)))


def _utm_crs_for_geometry(geometry: BaseGeometry) -> CRS:
    centroid = geometry.centroid
    zone = int((centroid.x + 180) // 6) + 1
    return CRS.from_epsg(32700 + zone)


@lru_cache(maxsize=4)
def load_commune_catalog(path_value: str = str(COMMUNE_GEOJSON_PATH)) -> CommuneCatalog:
    path = Path(path_value)
    try:
        raw_payload = path.read_bytes()
        if (
            path.resolve() == COMMUNE_GEOJSON_PATH.resolve()
            and hashlib.sha256(raw_payload).hexdigest() != EXPECTED_COMMUNE_GEOJSON_SHA256
        ):
            raise ValueError("el hash del catálogo versionado no coincide")
        payload = json.loads(raw_payload.decode("utf-8"))
        if payload.get("type") != "FeatureCollection":
            raise ValueError("el documento no es FeatureCollection")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("derived_crs") != "EPSG:4326":
            raise ValueError("el CRS derivado no es EPSG:4326")
        geometry_version = metadata.get("geometry_version")
        if not isinstance(geometry_version, str) or not geometry_version:
            raise ValueError("falta la versión de geometría")
        features = payload.get("features")
        if not isinstance(features, list) or len(features) != EXPECTED_COMMUNE_COUNT:
            raise ValueError(f"se esperaban {EXPECTED_COMMUNE_COUNT} comunas")

        communes: dict[str, CommuneGeometry] = {}
        for feature in features:
            if not isinstance(feature, dict):
                raise ValueError("feature inválida")
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                raise ValueError("feature sin propiedades")
            code = properties.get("CUT_COM")
            source_name = properties.get("nombre_oficial_fuente")
            display_name = properties.get("nombre_presentacion")
            if not all(isinstance(value, str) and value for value in (code, source_name, display_name)):
                raise ValueError("feature sin identidad territorial completa")
            if len(code) != 5 or not code.isdigit():
                raise ValueError(f"CUT_COM inválido: {code}")
            if code in communes:
                raise ValueError(f"CUT_COM duplicado: {code}")
            geometry_payload = feature.get("geometry")
            if not isinstance(geometry_payload, dict):
                raise ValueError(f"geometría ausente para CUT_COM={code}")
            geometry = shape(geometry_payload)
            if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty or not geometry.is_valid:
                raise ValueError(f"geometría inválida para CUT_COM={code}")
            min_lon, min_lat, max_lon, max_lat = geometry.bounds
            if not (-76 <= min_lon <= max_lon <= -66 and -56 <= min_lat <= max_lat <= -17):
                raise ValueError(f"geometría fuera de Chile para CUT_COM={code}")
            to_metric = Transformer.from_crs("EPSG:4326", _utm_crs_for_geometry(geometry), always_xy=True)
            communes[code] = CommuneGeometry(
                code=code,
                source_name=source_name,
                display_name=display_name,
                geometry_wgs84=geometry,
                geometry_metric=transform(to_metric.transform, geometry),
                to_metric=to_metric,
            )
        return CommuneCatalog(geometry_version=geometry_version, communes=communes)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ShapelyError, ProjError) as exc:
        raise GeofenceConfigurationError("El catálogo geográfico comunal no está disponible o es inválido.") from exc


def commune_options(path_value: str = str(COMMUNE_GEOJSON_PATH)) -> tuple[tuple[str, str], ...]:
    catalog = load_commune_catalog(path_value)
    return tuple(sorted(((code, item.display_name) for code, item in catalog.communes.items()), key=lambda item: item[1]))


def commune_display_name(code: str, path_value: str = str(COMMUNE_GEOJSON_PATH)) -> str:
    item = load_commune_catalog(path_value).communes.get(code)
    if item is None:
        raise GeofenceConfigurationError("El código comunal no existe en el catálogo autorizado.")
    return item.display_name


def _radio_candidate(evidence: EvidenciaGPSCreate, place: LugarTrabajo) -> _Candidate:
    if place.latitud is None or place.longitud is None or place.radio_metros is None:
        raise GeofenceConfigurationError("Una geocerca RADIO activa está incompleta.")
    distance = haversine_distance_m(evidence.latitud, evidence.longitud, place.latitud, place.longitud)
    radius = Decimal(place.radio_metros)
    margin = radius - distance
    return _Candidate(
        place=place,
        status="DENTRO_RANGO" if margin >= 0 else "FUERA_RANGO",
        distance_m=distance,
        margin_m=margin,
        radius_m=radius,
        tolerance_m=None,
        geofence_type="RADIO",
        geometry_version=None,
    )


def _commune_candidate(
    evidence: EvidenciaGPSCreate,
    place: LugarTrabajo,
    catalog: CommuneCatalog,
    tolerance: Decimal,
) -> _Candidate:
    if not place.codigo_comuna:
        raise GeofenceConfigurationError("Una geocerca COMUNA activa no tiene CUT_COM.")
    commune = catalog.communes.get(place.codigo_comuna)
    if commune is None:
        raise GeofenceConfigurationError("Una geocerca COMUNA activa usa un CUT_COM no autorizado.")
    point_wgs84 = Point(float(evidence.longitud), float(evidence.latitud))
    point_metric = transform(commune.to_metric.transform, point_wgs84)
    boundary_distance = _decimal_meters(commune.geometry_metric.boundary.distance(point_metric))
    inside = commune.geometry_wgs84.covers(point_wgs84)
    margin = boundary_distance if inside else -boundary_distance
    if inside:
        status = "DENTRO_RANGO"
    elif boundary_distance <= tolerance:
        status = "DENTRO_TOLERANCIA"
    else:
        status = "FUERA_RANGO"
    return _Candidate(
        place=place,
        status=status,
        distance_m=boundary_distance,
        margin_m=margin,
        radius_m=None,
        tolerance_m=tolerance,
        geofence_type="COMUNA",
        geometry_version=catalog.geometry_version,
    )


def evaluate_geolocation(
    evidence: EvidenciaGPSCreate,
    places: Iterable[LugarTrabajo],
    max_accuracy_m: int | None = None,
    commune_tolerance_m: int | None = None,
    dataset_path: Path | None = None,
) -> GeoEvaluationResult:
    applied_accuracy = Decimal(
        attendance_max_gps_accuracy_meters() if max_accuracy_m is None else max_accuracy_m
    )
    tolerance = Decimal(
        attendance_commune_boundary_tolerance_meters()
        if commune_tolerance_m is None
        else commune_tolerance_m
    )
    accuracy_status = "BAJA_PRECISION" if evidence.precision_m > applied_accuracy else "ACEPTABLE"
    active = [place for place in places if place.activo and place.tipo_geocerca in {"RADIO", "COMUNA"}]
    if not active:
        return GeoEvaluationResult(None, None, None, None, None, None, "SIN_ZONA_CONFIGURADA", accuracy_status, applied_accuracy)

    catalog = None
    candidates: list[_Candidate] = []
    for place in active:
        if place.tipo_geocerca == "RADIO":
            candidates.append(_radio_candidate(evidence, place))
        else:
            if catalog is None:
                catalog = load_commune_catalog(str(dataset_path or COMMUNE_GEOJSON_PATH))
            candidates.append(_commune_candidate(evidence, place, catalog, tolerance))

    status_rank = {"DENTRO_RANGO": 0, "DENTRO_TOLERANCIA": 1, "FUERA_RANGO": 2}
    selected = min(
        candidates,
        key=lambda candidate: (
            status_rank[candidate.status],
            candidate.place.prioridad_geocerca,
            -candidate.margin_m,
            candidate.place.id,
        ),
    )
    return GeoEvaluationResult(
        place_id=selected.place.id,
        distance_m=selected.distance_m,
        radius_m=selected.radius_m,
        tolerance_m=selected.tolerance_m,
        geofence_type=selected.geofence_type,
        geometry_version=selected.geometry_version,
        geofence_status=selected.status,
        accuracy_status=accuracy_status,
        max_accuracy_m=applied_accuracy,
    )
