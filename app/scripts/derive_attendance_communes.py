"""Inspect and derive the approved attendance commune GeoJSON from SUBDERE DPA 2023.

This deliberately reads the small subset of the ESRI Shapefile format used by the
official polygon layer so the derivation needs no GIS dependency beyond Shapely
and pyproj, which are also runtime dependencies of the resulting geofence logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator

from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, mapping
from shapely.ops import transform


SOURCE_URL = "https://ide.subdere.gov.cl/descargas/SHP/Limite_DPA_03082023.rar"
SOURCE_DATASET_DATE = "2023-08-03"
SOURCE_CRS = "EPSG:5360"
DERIVED_CRS = "EPSG:4326"
GEOMETRY_VERSION = "SUBDERE_DPA_2023_2023-08-03"
EXPECTED_SOURCE_SHA256 = "4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3"
APPROVED_COMMUNES = {
    "06110": ("Mostazal", "Mostazal"),
    "08301": ("Los Angeles", "Los \u00c1ngeles"),
    "13102": ("Cerrillos", "Cerrillos"),
    "13103": ("Cerro Navia", "Cerro Navia"),
    "13107": ("Huechuraba", "Huechuraba"),
    "13110": ("La Florida", "La Florida"),
    "13112": ("La Pintana", "La Pintana"),
    "13117": ("Lo Prado", "Lo Prado"),
    "13119": ("Maip\u00fa", "Maip\u00fa"),
    "13121": ("Pedro Aguirre Cerda", "Pedro Aguirre Cerda"),
    "13301": ("Colina", "Colina"),
    "13404": ("Paine", "Paine"),
    "16301": ("San Carlos", "San Carlos"),
}


@dataclass(frozen=True)
class DbfField:
    name: str
    kind: str
    length: int
    decimals: int


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_dbf(path: Path, encoding: str) -> tuple[list[DbfField], list[dict[str, str]]]:
    with path.open("rb") as stream:
        header = stream.read(32)
        if len(header) != 32:
            raise ValueError("Cabecera DBF incompleta")
        record_count = struct.unpack("<I", header[4:8])[0]
        header_length = struct.unpack("<H", header[8:10])[0]
        record_length = struct.unpack("<H", header[10:12])[0]
        fields: list[DbfField] = []
        while stream.tell() < header_length:
            descriptor = stream.read(32)
            if not descriptor or descriptor[0] == 0x0D:
                break
            fields.append(
                DbfField(
                    descriptor[:11].split(b"\0", 1)[0].decode("ascii"),
                    chr(descriptor[11]),
                    descriptor[16],
                    descriptor[17],
                )
            )
        stream.seek(header_length)
        records: list[dict[str, str]] = []
        for _ in range(record_count):
            raw = stream.read(record_length)
            if len(raw) != record_length:
                raise ValueError("Registro DBF incompleto")
            if raw[:1] == b"*":
                continue
            offset = 1
            record: dict[str, str] = {}
            for field in fields:
                value = raw[offset : offset + field.length]
                record[field.name] = value.decode(encoding).strip()
                offset += field.length
            records.append(record)
    return fields, records


def read_shp_parts(path: Path) -> Iterator[list[list[tuple[float, float]]] | None]:
    with path.open("rb") as stream:
        header = stream.read(100)
        if len(header) != 100 or struct.unpack(">I", header[:4])[0] != 9994:
            raise ValueError("Cabecera SHP inválida")
        declared_type = struct.unpack("<I", header[32:36])[0]
        if declared_type not in {5, 15, 25}:
            raise ValueError(f"La capa SHP no es poligonal: tipo {declared_type}")
        while record_header := stream.read(8):
            if len(record_header) != 8:
                raise ValueError("Cabecera de registro SHP incompleta")
            content_length = struct.unpack(">I", record_header[4:8])[0] * 2
            content = stream.read(content_length)
            if len(content) != content_length:
                raise ValueError("Registro SHP incompleto")
            shape_type = struct.unpack("<I", content[:4])[0]
            if shape_type == 0:
                yield None
                continue
            if shape_type not in {5, 15, 25}:
                raise ValueError(f"Registro SHP no poligonal: tipo {shape_type}")
            part_count, point_count = struct.unpack("<II", content[36:44])
            part_starts = list(struct.unpack(f"<{part_count}I", content[44 : 44 + part_count * 4]))
            points_offset = 44 + part_count * 4
            coordinates = [
                struct.unpack("<dd", content[points_offset + index * 16 : points_offset + (index + 1) * 16])
                for index in range(point_count)
            ]
            ends = part_starts[1:] + [point_count]
            yield [coordinates[start:end] for start, end in zip(part_starts, ends, strict=True)]


def signed_area(ring: list[tuple[float, float]]) -> float:
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True)
    ) / 2


def polygon_from_parts(parts: list[list[tuple[float, float]]]) -> Polygon | MultiPolygon:
    shells = [ring for ring in parts if signed_area(ring) < 0]
    holes = [ring for ring in parts if signed_area(ring) >= 0]
    if not shells:
        raise ValueError("Geometría sin anillos exteriores")
    grouped: list[tuple[list[tuple[float, float]], list[list[tuple[float, float]]]]] = [
        (shell, []) for shell in shells
    ]
    shell_polygons = [Polygon(shell) for shell in shells]
    for hole in holes:
        probe = Point(hole[0])
        containers = [
            (index, polygon.area)
            for index, polygon in enumerate(shell_polygons)
            if polygon.covers(probe)
        ]
        if not containers:
            raise ValueError("Anillo interior sin polígono contenedor")
        index = min(containers, key=lambda item: item[1])[0]
        grouped[index][1].append(hole)
    polygons = [Polygon(shell, interior) for shell, interior in grouped]
    geometry = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
    if not geometry.is_valid:
        raise ValueError("Geometría comunal inválida en la fuente")
    return geometry


def inspect(dbf_path: Path, encoding: str) -> None:
    fields, records = read_dbf(dbf_path, encoding)
    print("FIELDS", json.dumps([field.__dict__ for field in fields], ensure_ascii=False))
    print("RECORD_COUNT", len(records))
    for record in records:
        print(json.dumps(record, ensure_ascii=True, sort_keys=True))


def derive(
    *,
    shp_path: Path,
    dbf_path: Path,
    prj_path: Path,
    source_archive: Path,
    output_path: Path,
    encoding: str,
) -> None:
    source_hash = sha256(source_archive)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError(f"Hash SHA-256 inesperado para la fuente: {source_hash}")
    source_wkt = prj_path.read_text(encoding="utf-8").strip()
    source_crs = CRS.from_wkt(source_wkt)
    if source_crs.to_epsg() != 5360:
        raise ValueError(f"CRS fuente inesperado: {source_crs.to_string()}")
    transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)

    fields, records = read_dbf(dbf_path, encoding)
    if not {"CUT_COM", "COMUNA"}.issubset({field.name for field in fields}):
        raise ValueError("La tabla DBF no contiene CUT_COM y COMUNA")
    shapes = list(read_shp_parts(shp_path))
    if len(shapes) != len(records):
        raise ValueError("SHP y DBF tienen distinta cantidad de registros")

    selected: dict[str, tuple[dict[str, str], list[list[tuple[float, float]]]]] = {}
    for record, parts in zip(records, shapes, strict=True):
        code = record["CUT_COM"]
        if code not in APPROVED_COMMUNES:
            continue
        if code in selected:
            raise ValueError(f"CUT_COM duplicado en la fuente: {code}")
        if parts is None:
            raise ValueError(f"Geometría vacía para CUT_COM={code}")
        selected[code] = (record, parts)
    if set(selected) != set(APPROVED_COMMUNES):
        missing = sorted(set(APPROVED_COMMUNES) - set(selected))
        raise ValueError(f"Faltan comunas aprobadas en la fuente: {missing}")

    features = []
    for code in sorted(selected):
        record, parts = selected[code]
        expected_source_name, display_name = APPROVED_COMMUNES[code]
        if record["COMUNA"] != expected_source_name:
            raise ValueError(
                f"Nombre oficial inesperado para CUT_COM={code}: {record['COMUNA']!r}"
            )
        geometry = transform(transformer.transform, polygon_from_parts(parts))
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError(f"Geometría derivada inválida para CUT_COM={code}")
        min_lon, min_lat, max_lon, max_lat = geometry.bounds
        if not (-76 <= min_lon <= max_lon <= -66 and -56 <= min_lat <= max_lat <= -17):
            raise ValueError(f"Geometría fuera del rango esperado de Chile para CUT_COM={code}")
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "CUT_COM": code,
                    "nombre_oficial_fuente": expected_source_name,
                    "nombre_presentacion": display_name,
                },
                "geometry": mapping(geometry),
            }
        )

    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "División Político Administrativa 2023",
            "source_url": SOURCE_URL,
            "source_dataset_date": SOURCE_DATASET_DATE,
            "source_crs": SOURCE_CRS,
            "derived_crs": DERIVED_CRS,
            "derived_on": date.today().isoformat(),
            "geometry_version": GEOMETRY_VERSION,
            "source_sha256": source_hash,
        },
        "features": features,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    print(f"FEATURES={len(features)}")
    print(f"SOURCE_SHA256={payload['metadata']['source_sha256']}")
    print(f"GEOJSON_SHA256={sha256(output_path)}")
    print(f"GEOJSON_BYTES={output_path.stat().st_size}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbf", type=Path, required=True)
    parser.add_argument("--shp", type=Path)
    parser.add_argument("--prj", type=Path)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--inspect", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.inspect:
        inspect(args.dbf, args.encoding)
        return
    if not all((args.shp, args.prj, args.source_archive, args.output)):
        raise SystemExit("La derivación requiere --shp, --prj, --source-archive y --output")
    derive(
        shp_path=args.shp,
        dbf_path=args.dbf,
        prj_path=args.prj,
        source_archive=args.source_archive,
        output_path=args.output,
        encoding=args.encoding,
    )


if __name__ == "__main__":
    main()
