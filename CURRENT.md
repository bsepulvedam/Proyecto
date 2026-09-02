# Estado actual y continuidad de Boliklor

Este documento describe el estado verificable del repositorio y el punto exacto para continuar. Prevalecen código, configuración, migraciones y tests.

## 1. Identificación

- **Proyecto:** Boliklor.
- **Fecha de actualización:** 2026-09-02 (`America/Santiago`).
- **Rama:** `main`, con seguimiento de `origin/main`.
- **Último commit base:** `1b7b6f99bc5399ede32dd5df4009d1189498cdc7` (`1b7b6f9`), `Completar marcaje web y calendario real de Asistencia`.
- **Sincronía conocida:** `HEAD` y la referencia local `origin/main` están 0/0; no se ejecutó `fetch`.
- **Estado del árbol:** Asistencia 4B-2B está implementada en el árbol y todavía sin commit/push. No se ejecutaron `git add`, commit, push ni deploy.

## 2. Estado funcional

- [IMPLEMENTADO Y CONFIRMADO] Identidad/acceso, RRHH básico, Inventario parcial y Órdenes de trabajo heredadas conservan su alcance previo.
- [IMPLEMENTADO, INTEGRADO Y VALIDADO MANUALMENTE] Asistencia 4B-2 registra `ENTRADA`/`SALIDA` con GPS puntual, usa hora del servidor y exige 5 minutos mínimos antes de SALIDA.
- [IMPLEMENTADO, INTEGRADO Y VALIDADO MANUALMENTE] Asistencia 4B-2A proyecta sesiones cerradas en el calendario personal, ofrece detalle diario y clasificación visual de revisión/fuera de rango.
- [IMPLEMENTADO, MIGRADO Y VALIDADO 4B-2B] Geocercas `RADIO` y `COMUNA`, administración por ADMIN, detección automática entre todas las zonas activas, tolerancia comunal y persistencia del snapshot geográfico. Gates automatizado, PostgreSQL desechable, manual, backup/restore y migración real aprobados.
- [PENDIENTE] Asistencia 4B-3: portal de supervisión ADMIN/JEFATURA y reportes.

## 3. Asistencia 4B-2B implementada en el árbol

- [IMPLEMENTADO EN ÁRBOL] `LugarTrabajo` admite geocerca opcional `RADIO` o `COMUNA`, `codigo_comuna` y prioridad positiva. Una sola zona comunal puede estar activa por `CUT_COM`.
- [IMPLEMENTADO EN ÁRBOL] `RADIO` usa Haversine contra centro/radio. `COMUNA` usa el polígono oficial, considera el borde dentro de rango y aplica `ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS=100` como valor provisional configurable.
- [IMPLEMENTADO EN ÁRBOL] Estados: `DENTRO_RANGO`, `DENTRO_TOLERANCIA`, `FUERA_RANGO` y `SIN_ZONA_CONFIGURADA`.
- [IMPLEMENTADO EN ÁRBOL] La selección automática evalúa todas las zonas activas y ordena por estado, prioridad administrativa ascendente, mejor margen y finalmente ID ascendente.
- [IMPLEMENTADO EN ÁRBOL] No se usan asignaciones trabajador-lugar para detectar la zona y el trabajador no puede elegirla.
- [IMPLEMENTADO EN ÁRBOL] `DENTRO_TOLERANCIA` se persiste con tolerancia/tipo/versión geométrica, no genera incidencia automática y queda disponible para futura supervisión ADMIN/JEFATURA.
- [IMPLEMENTADO EN ÁRBOL] `FUERA_RANGO` y `GPS_BAJA_PRECISION` conservan el comportamiento de incidencia. Fallas del catálogo comunal revierten el marcaje con un mensaje seguro.
- [IMPLEMENTADO EN ÁRBOL] La evaluación histórica conserva lugar, distancia, radio o tolerancia, tipo de geocerca, versión geométrica y versión de regla; editar o desactivar un lugar no reescribe la evidencia.
- [IMPLEMENTADO EN ÁRBOL] ADMIN crea, edita, activa/desactiva y prioriza lugares/geocercas. Las comunas se eligen por código del catálogo autorizado.
- [IMPLEMENTADO EN ÁRBOL] `/admin/lugares` confirma activar/desactivar mediante un modal que identifica la zona real. Tras la respuesta confirmada por backend muestra un toast temporal, cerrable y accesible; los errores no muestran éxito ni exponen detalles internos.
- [CONFIRMADO MANUALMENTE 2026-09-02] Las 13 zonas COMUNA, administración RADIO/COMUNA, desactivación/reactivación y persistencia, marcaje, detección automática, ausencia de selección manual, mínimo de 5 minutos, calendario y detalle funcionan en navegador sin regresiones detectadas.

## 4. Catálogo geográfico y procedencia

- **Fuente oficial:** SUBDERE, División Político Administrativa 2023, capa `COMUNAS_v1`, actualización declarada 2023-08-03.
- **URL:** `https://ide.subdere.gov.cl/descargas/SHP/Limite_DPA_03082023.rar`.
- **Archivo fuente:** 262380302 bytes; SHA-256 `4c8dd01ca4ca7d8b111dac78b88cc8ac64c1af7b8ebe0c85a21eaab337ae3fd3`.
- **CRS:** la fuente IDE declara EPSG:5360; `pyproj.CRS.to_epsg()` sobre el WKT ESRI original devuelve `5360`; el subconjunto se transforma a EPSG:4326.
- **GeoJSON versionable:** `app/data/geofences/subdere_dpa_2023_approved_communes.geojson`.
- **GeoJSON final:** 13 features, 656212 bytes; SHA-256 `4962c9a4a931002a51872f0ef9dfbf541c088d8419fc671d02b3a304d213a638`.
- **Identidad territorial:** siempre `CUT_COM`; nunca coincidencia textual del nombre.
- **Normalización explícita:** `08301` conserva `Los Angeles` como `nombre_oficial_fuente` y usa `Los Ángeles` como presentación. El resto conserva el nombre fuente como presentación.
- **Reproducibilidad:** `app/scripts/derive_attendance_communes.py` valida el hash fuente, EPSG:5360, nombres por código, exactamente 13 códigos únicos, geometrías válidas/no vacías y rangos de Chile antes de escribir EPSG:4326.
- **Runtime/cache:** el proceso valida el GeoJSON y cachea por ruta el catálogo, las geometrías WGS84, las transformaciones UTM locales y las geometrías métricas.
- **Temporales:** `.tmp_dpa_2023/` y `.tmp_wheels/` fueron eliminados. No permanece el archivo fuente de 262 MB ni wheels dentro del árbol.

Comunas aprobadas:

| CUT_COM | Nombre oficial fuente | Presentación |
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

## 5. Dependencias y migración

- [IMPLEMENTADO EN ÁRBOL] `requirements.txt` fija `shapely==2.1.2` y `pyproj==3.7.2`; ya no se depende solo de instalaciones manuales.
- [CONFIRMADO LOCALMENTE] Ambas importan en Python 3.14.7, la suite completa pasa y `pip check` no detecta dependencias rotas.
- [IMPLEMENTADO EN ÁRBOL] Nueva revisión Alembic `20260901_08`, hija lineal de `20260831_07`; mantiene 22 tablas y amplía lugares/evaluaciones.
- [IMPLEMENTADO EN ÁRBOL] La revisión carga las 13 zonas comunales, migra radios preexistentes no ambiguos y agrega constraints/índices de coherencia.
- [CONFIRMADO ONLINE 2026-09-01] `boliklor_ot_test`, configurada mediante `.env.test.local` ignorado, migró desde base vacía hasta `20260901_08`; `alembic check` informó `No new upgrade operations detected`.
- [CONFIRMADO ONLINE 2026-09-01] El gate detectó y corrigió en la revisión candidata una inferencia ambigua de parámetros PostgreSQL durante el backfill. El primer upgrade fallido revirtió la cadena completa sin dejar esquema parcial; el segundo completó `empty → head`.
- [CONFIRMADO ONLINE 2026-09-01] Downgrade limpio a `20260831_07` y re-upgrade funcionan. Con evaluaciones COMUNA presentes, el downgrade se rechaza deliberadamente antes de modificar esquema o datos y la base permanece en head.
- [IMPLEMENTADO] Procedimiento operacional de backup/restore PostgreSQL documentado en `docs/operations/database-backup-restore.md`, con guardas de identidad, secretos, restore desechable y recuperación conceptual.
- [CONFIRMADO OPERACIONAL 2026-09-02] Backup real previo a migración creado mediante `pg_dump -Fc` fuera del repositorio: `boliklor_ot_pre_4b2b_20260902_143950Z.dump`, 105041 bytes, SHA-256 `bdae960d9d7e0e96b2cede78d5df8f627723d2e67112000abc3d0f7b07c0110e`; `pg_dump` y `pg_restore --list` finalizaron con exit code `0`.
- [CONFIRMADO OPERACIONAL 2026-09-02] Restore probado en `boliklor_ot_restore_test`: revisión `20260831_07`, 23 tablas públicas, conteos por tabla, constraints, 88 índices, 24 secuencias y 28 FKs sin huérfanos coincidieron con el origen. La base desechable se eliminó después del éxito.
- [CONFIRMADO PRE-MIGRACIÓN 2026-09-02] Antes del gate final, `boliklor_ot` permanecía en `20260831_07`; el backup/restore se completó sin ejecutar Alembic ni modificar manualmente datos reales.
- [CONFIRMADO MIGRACIÓN REAL 2026-09-02] `alembic upgrade head` aplicó `20260901_08` sobre `boliklor_ot` con salida `0`. `alembic current` y `heads` informan `20260901_08 (head)` y `alembic check` informa `No new upgrade operations detected`.
- [CONFIRMADO POST-MIGRACIÓN 2026-09-02] Se preservaron los 14 IDs históricos de lugares y los conteos/IDs de Identidad, RRHH, Asistencia, Inventario y OT. Quedaron 13 geocercas COMUNA activas con CUT únicos, La Pintana única, sin duplicados comunales activos; Base y Taller continúan sin geocerca y no existían zonas RADIO históricas que reclasificar.

## 6. Validaciones ejecutadas hasta el 2026-09-02

- `compileall -q app tests`: aprobado.
- `pip check`: aprobado, `No broken requirements found`.
- suite focalizada de Asistencia, incluida la UX administrativa: 75/75 aprobadas.
- suite completa aislada con SQLite en memoria: 168/168 aprobadas, 0 fallas y 0 errores.
- derivación reproducible: 13 features, hash fuente esperado y hash/tamaño final verificados.
- tests geográficos: borde, dentro de tolerancia, fuera, zonas inactivas, RADIO+COMUNA, solapamientos, prioridad/margen/ID, identidad por código, catálogo ausente/corrupto y código desconocido.
- tests de persistencia: no asignación, snapshot comunal, tolerancia sin incidencia, fuera de rango con incidencia y rollback seguro.
- regresión conservada: ownership, CSRF/RBAC, GPS puntual/privacidad, mínimo de sesión, múltiples sesiones, calendario personal y administración de lugares.
- Alembic estático/offline: head/historia aprobados y SQL de upgrade completo generado sin conexión.
- Alembic PostgreSQL online sobre `boliklor_ot_test`: `empty → head`, paridad ORM, esquema real, constraints, FKs, índices, seeds/backfill, downgrade/re-upgrade y protección de downgrade aprobados.
- PostgreSQL 4B-2B: RADIO/COMUNA, cuatro estados, trabajador sin asignación, selección automática/prioridad, concurrencia de comuna activa única, incidencias, múltiples sesiones, mínimo de 5 minutos y rollback por GeoJSON inválido aprobados.
- UX administrativa: activación/desactivación ADMIN, denegación no ADMIN, CSRF, nombre real en confirmación y mensajes, éxito diferenciado, cancelación sin submit y error sin falso éxito aprobados.
- validación manual 4B-2B en navegador: aprobada sin regresiones funcionales detectadas.
- backup/restore operacional: `pg_dump -Fc` y catálogo aprobados; restore desechable comparado contra el origen y eliminado tras validar, sin ejecutar migraciones.
- migración real: `20260831_07 → 20260901_08 (head)` aprobada; 23 tablas públicas, 15 lugares totales, 13 COMUNA, siete constraints y tres índices 4B-2B verificados, 28 FKs sin huérfanos y `alembic check` sin drift.
- smoke post-migración sobre Uvicorn conectado a `boliklor_ot`: `/health` 200, `/login` 200 y `/admin/lugares` mantiene redirección 303 sin sesión. La capa de aplicación renderizó el listado real con los 15 lugares, 13 COMUNA y todos los CUT; modal/toast se verificaron estructuralmente sin mutar zonas reales.

## 7. Riesgos y pendientes

- [PENDIENTE] Política legal/de negocio de retención y acceso a GPS/datos laborales.
- [DEUDA_TECNICA] El backup/restore manual ya está documentado y ensayado, pero no hay CI/CD, proxy/TLS, backups automáticos/copia externa, retención/RPO/RTO, monitorización ni evidencia de despliegue productivo.
- [DEUDA_TECNICA] RBAC sigue hardcodeado; faltan rate limit, MFA/recuperación y auditoría privilegiada.

## 8. Alcance confirmado de Asistencia 4B-3

- portal ADMIN/JEFATURA;
- listado de todos los trabajadores y búsqueda/filtro por nombre;
- filtro por período;
- calendario y detalle individual;
- días trabajados;
- jornadas pagables;
- doble turno diferenciable;
- incidencias;
- exportación individual y conjunta a Excel;
- tarifa provisional `$30.000 CLP` por jornada pagable, todavía no implementada;
- horas extra y días extra pendientes de definición posterior.

## 9. Punto exacto de continuidad

**Fase activa:** Asistencia 4B-2B completada: implementación, tests automatizados, PostgreSQL desechable, validación manual, UX de confirmación/toast, backup real, restore desechable, migración real y smoke post-migración aprobados. La base real está en `20260901_08 (head)` y el árbol continúa sin commit/push.

**Estado de cierre:** 4B-2B lista para commit/push.

**Siguiente gate:** revisión final del diff y luego stage, commit y push de los artefactos deliberados de 4B-2B. La próxima fase funcional es Asistencia 4B-3 — Portal ADMIN/JEFATURA dentro del alcance confirmado.

**Prohibiciones vigentes:** no ejecutar nuevas mutaciones de esquema/datos reales fuera de un gate explícito; no incluir backups, fuentes masivas, wheels, secretos, documentos laborales ni coordenadas exactas en Git o logs/UI no autorizada.
