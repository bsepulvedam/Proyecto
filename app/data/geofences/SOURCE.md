# Fuente de geocercas comunales de Asistencia

## Artefacto versionado

- Archivo: `subdere_dpa_2023_approved_communes.geojson`.
- Contenido: subconjunto de las 13 comunas aprobadas para Asistencia 4B-2B.
- Identidad territorial: `CUT_COM`; los nombres nunca se usan para seleccionar geometría.
- Versión: `SUBDERE_DPA_2023_2023-08-03`.
- CRS derivado: EPSG:4326.
- Fecha de derivación: 2026-09-01.
- Tamaño: 656212 bytes.
- SHA-256: `4962c9a4a931002a51872f0ef9dfbf541c088d8419fc671d02b3a304d213a638`.

## Fuente oficial

- Organismo: Subsecretaría de Desarrollo Regional y Administrativo (SUBDERE).
- Dataset: División Político Administrativa 2023, capa `COMUNAS_v1`.
- URL: `https://ide.subdere.gov.cl/descargas/SHP/Limite_DPA_03082023.rar`.
- Fecha de actualización declarada: 2023-08-03.
- Tamaño descargado: 262380302 bytes.
- SHA-256: `4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3`.
- CRS declarado por IDE SUBDERE: EPSG:5360.
- `pyproj.CRS.to_epsg()` sobre el `.prj`: `5360`.
- WKT original: `GEOGCS["GCS_SIRGAS-Chile",DATUM["D_SIRGAS-Chile",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]`.

La diferencia entre ese WKT ESRI y el WKT EPSG moderno fue revisada y autorizada: identifica el mismo CRS, por lo que la derivación transforma EPSG:5360 a EPSG:4326.

## Comunas y normalización

| CUT_COM | Nombre oficial fuente | Nombre de presentación |
| --- | --- | --- |
| 06110 | Mostazal | Mostazal |
| 08301 | Los Angeles | Los Ángeles |
| 13102 | Cerrillos | Cerrillos |
| 13103 | Cerro Navia | Cerro Navia |
| 13107 | Huechuraba | Huechuraba |
| 13110 | La Florida | La Florida |
| 13112 | La Pintana | La Pintana |
| 13117 | Lo Prado | Lo Prado |
| 13119 | Maipú | Maipú |
| 13121 | Pedro Aguirre Cerda | Pedro Aguirre Cerda |
| 13301 | Colina | Colina |
| 13404 | Paine | Paine |
| 16301 | San Carlos | San Carlos |

`08301` conserva `Los Angeles` como procedencia y usa `Los Ángeles` solo para presentación. La geometría se selecciona siempre por `CUT_COM=08301`.

## Reproducción

El archivo fuente y los wheels temporales no se versionan. Tras extraer la capa oficial, ejecutar:

```powershell
python -m app.scripts.derive_attendance_communes `
  --dbf <ruta>\COMUNAS_v1.dbf `
  --shp <ruta>\COMUNAS_v1.shp `
  --prj <ruta>\COMUNAS_v1.prj `
  --source-archive <ruta>\Limite_DPA_03082023.rar `
  --output app\data\geofences\subdere_dpa_2023_approved_communes.geojson
```

El script valida el hash de procedencia esperado, nombres oficiales por código, cantidad exacta, unicidad, geometrías, CRS y rangos geográficos antes de escribir el derivado.
