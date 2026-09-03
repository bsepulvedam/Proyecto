# Estado actual y continuidad de Boliklor

Este documento describe el estado verificable del repositorio y el punto exacto para continuar. Prevalecen código, configuración, migraciones y tests.

## 1. Identificación

- **Proyecto:** Boliklor.
- **Fecha de actualización:** 2026-09-03 (`America/Santiago`).
- **Rama:** `main`, con seguimiento de `origin/main`.
- **Último commit base:** `72534f5`, `Implementar portal de supervisión de Asistencia 4B-3C`.
- **Sincronía conocida:** `HEAD` y la referencia local `origin/main` están 0/0; no se ejecutó `fetch`.
- **Estado del árbol:** 4B-3A/3B están integradas en `aea9c32` y 4B-3C en `72534f5`. Asistencia 4B-3D está implementada y testeada en el árbol, todavía sin commit/push. No se ejecutaron `git add`, commit, push, deploy ni migración real durante 4B-3D.

## 2. Estado funcional

- [IMPLEMENTADO Y CONFIRMADO] Identidad/acceso, RRHH básico, Inventario parcial y Órdenes de trabajo heredadas conservan su alcance previo.
- [IMPLEMENTADO, INTEGRADO Y VALIDADO MANUALMENTE] Asistencia 4B-2 registra `ENTRADA`/`SALIDA` con GPS puntual, usa hora del servidor y exige 5 minutos mínimos antes de SALIDA.
- [IMPLEMENTADO, INTEGRADO Y VALIDADO MANUALMENTE] Asistencia 4B-2A proyecta sesiones cerradas en el calendario personal, ofrece detalle diario y clasificación visual de revisión/fuera de rango.
- [IMPLEMENTADO, MIGRADO Y VALIDADO 4B-2B] Geocercas `RADIO` y `COMUNA`, administración por ADMIN, detección automática entre todas las zonas activas, tolerancia comunal y persistencia del snapshot geográfico. Gates automatizado, PostgreSQL desechable, manual, backup/restore y migración real aprobados.
- [IMPLEMENTADO, TESTEADO Y COMMIT 4B-3A] Motor de dominio común para actividad, incompletos, situación horaria, jornadas pagables, doble turno, tarifa efectiva versionada y total provisional. El calendario personal explicita sesiones incompletas.
- [IMPLEMENTADO, TESTEADO, VALIDADO EN POSTGRESQL DESECHABLE Y COMMIT 4B-3B] Persistencia auditable de SALIDA administrativa, decisiones finales de incidencias, tarifas globales/individuales versionadas y migración candidata `20260902_09`.
- [IMPLEMENTADO, TESTEADO, VALIDADO MANUALMENTE Y COMMIT 4B-3C] Portal de supervisión ADMIN/JEFATURA bajo `/asistencia/supervision`, búsqueda/filtros, resumen paginado, calendario individual, detalle diario y acciones web auditadas para completar SALIDA y decidir incidencias.
- [IMPLEMENTADO Y TESTEADO EN ÁRBOL 4B-3D] Administración web append-only de tarifas exclusivamente ADMIN y exportación XLSX conjunta/individual para ADMIN/JEFATURA con filtros, paridad de proyección, neutralización de fórmulas y omisión de GPS.

## 3. Asistencia 4B-2B integrada

- [IMPLEMENTADO 4B-2B] `LugarTrabajo` admite geocerca opcional `RADIO` o `COMUNA`, `codigo_comuna` y prioridad positiva. Una sola zona comunal puede estar activa por `CUT_COM`.
- [IMPLEMENTADO 4B-2B] `RADIO` usa Haversine contra centro/radio. `COMUNA` usa el polígono oficial, considera el borde dentro de rango y aplica `ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS=100` como valor provisional configurable.
- [IMPLEMENTADO 4B-2B] Estados: `DENTRO_RANGO`, `DENTRO_TOLERANCIA`, `FUERA_RANGO` y `SIN_ZONA_CONFIGURADA`.
- [IMPLEMENTADO 4B-2B] La selección automática evalúa todas las zonas activas y ordena por estado, prioridad administrativa ascendente, mejor margen y finalmente ID ascendente.
- [IMPLEMENTADO 4B-2B] No se usan asignaciones trabajador-lugar para detectar la zona y el trabajador no puede elegirla.
- [IMPLEMENTADO 4B-2B] `DENTRO_TOLERANCIA` se persiste con tolerancia/tipo/versión geométrica, no genera incidencia automática y queda disponible para futura supervisión ADMIN/JEFATURA.
- [IMPLEMENTADO 4B-2B] `FUERA_RANGO` y `GPS_BAJA_PRECISION` conservan el comportamiento de incidencia. Fallas del catálogo comunal revierten el marcaje con un mensaje seguro.
- [IMPLEMENTADO 4B-2B] La evaluación histórica conserva lugar, distancia, radio o tolerancia, tipo de geocerca, versión geométrica y versión de regla; editar o desactivar un lugar no reescribe la evidencia.
- [IMPLEMENTADO 4B-2B] ADMIN crea, edita, activa/desactiva y prioriza lugares/geocercas. Las comunas se eligen por código del catálogo autorizado.
- [IMPLEMENTADO 4B-2B] `/admin/lugares` confirma activar/desactivar mediante un modal que identifica la zona real. Tras la respuesta confirmada por backend muestra un toast temporal, cerrable y accesible; los errores no muestran éxito ni exponen detalles internos.
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

- [IMPLEMENTADO 4B-2B] `requirements.txt` fija `shapely==2.1.2` y `pyproj==3.7.2`; ya no se depende solo de instalaciones manuales.
- [CONFIRMADO LOCALMENTE] Ambas importan en Python 3.14.7, la suite completa pasa y `pip check` no detecta dependencias rotas.
- [IMPLEMENTADO 4B-2B] Revisión Alembic `20260901_08`, hija lineal de `20260831_07`; mantiene 22 tablas y amplía lugares/evaluaciones.
- [IMPLEMENTADO 4B-2B] La revisión carga las 13 zonas comunales, migra radios preexistentes no ambiguos y agrega constraints/índices de coherencia.
- [CONFIRMADO ONLINE 2026-09-01] `boliklor_ot_test`, configurada mediante `.env.test.local` ignorado, migró desde base vacía hasta `20260901_08`; `alembic check` informó `No new upgrade operations detected`.
- [CONFIRMADO ONLINE 2026-09-01] El gate detectó y corrigió en la revisión candidata una inferencia ambigua de parámetros PostgreSQL durante el backfill. El primer upgrade fallido revirtió la cadena completa sin dejar esquema parcial; el segundo completó `empty → head`.
- [CONFIRMADO ONLINE 2026-09-01] Downgrade limpio a `20260831_07` y re-upgrade funcionan. Con evaluaciones COMUNA presentes, el downgrade se rechaza deliberadamente antes de modificar esquema o datos y la base permanece en head.
- [IMPLEMENTADO] Procedimiento operacional de backup/restore PostgreSQL documentado en `docs/operations/database-backup-restore.md`, con guardas de identidad, secretos, restore desechable y recuperación conceptual.
- [CONFIRMADO OPERACIONAL 2026-09-02] Backup real previo a migración creado mediante `pg_dump -Fc` fuera del repositorio: `boliklor_ot_pre_4b2b_20260902_143950Z.dump`, 105041 bytes, SHA-256 `bdae960d9d7e0e96b2cede78d5df8f627723d2e67112000abc3d0f7b07c0110e`; `pg_dump` y `pg_restore --list` finalizaron con exit code `0`.
- [CONFIRMADO OPERACIONAL 2026-09-02] Restore probado en `boliklor_ot_restore_test`: revisión `20260831_07`, 23 tablas públicas, conteos por tabla, constraints, 88 índices, 24 secuencias y 28 FKs sin huérfanos coincidieron con el origen. La base desechable se eliminó después del éxito.
- [CONFIRMADO PRE-MIGRACIÓN 2026-09-02] Antes del gate final, `boliklor_ot` permanecía en `20260831_07`; el backup/restore se completó sin ejecutar Alembic ni modificar manualmente datos reales.
- [CONFIRMADO MIGRACIÓN REAL 2026-09-02] `alembic upgrade head` aplicó `20260901_08` sobre `boliklor_ot` con salida `0`. `alembic current` y `heads` informan `20260901_08 (head)` y `alembic check` informa `No new upgrade operations detected`.
- [CONFIRMADO POST-MIGRACIÓN 2026-09-02] Se preservaron los 14 IDs históricos de lugares y los conteos/IDs de Identidad, RRHH, Asistencia, Inventario y OT. Quedaron 13 geocercas COMUNA activas con CUT únicos, La Pintana única, sin duplicados comunales activos; Base y Taller continúan sin geocerca y no existían zonas RADIO históricas que reclasificar.
- [IMPLEMENTADO EN ÁRBOL 4B-3B] Revisión candidata `20260902_09`, hija lineal de `20260901_08`; agrega dos tablas, migra estados de incidencias con precheck y crea el seed global exacto de $30.000 vigente desde `2026-09-01`.
- [VALIDADO POSTGRESQL DESECHABLE 2026-09-02] `boliklor_ot_test` aprobó `empty → 20260902_09`, `20260901_08 → 20260902_09`, downgrade/re-upgrade, mapeo histórico, paridad ORM, seed, constraints/FKs/índices, locks y concurrencia. El downgrade se rechaza antes de perder intervenciones o versiones nuevas de tarifas.
- [NO MIGRADO REAL] `boliklor_ot` permanece en `20260901_08`; no se ejecutó `20260902_09` ni se modificaron esquema/datos reales durante 4B-3B.

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
- 4B-3A focalizada: 88/88 tests de reglas, calendario, marcajes, geocercas y estructura aprobados.
- 4B-3A suite completa aislada: 181/181 aprobados con `APP_ENV=test` y `AUTH_ENFORCED=false`; la primera ejecución sin ese aislamiento produjo 20 redirecciones 303 heredadas en tests de Inventario/OT y no se contabiliza como aprobación.
- 4B-3A `python -m compileall -q app tests alembic`: aprobado; `pip check`: `No broken requirements found`; `git diff --check`: aprobado.
- 4B-3B focalizada SQLite/PostgreSQL: 13/13 aprobadas para salida administrativa, decisiones de incidencia, tarifas y carreras concurrentes.
- 4B-3B regresión completa de Asistencia: 101/101 aprobadas.
- 4B-3B suite completa con `APP_ENV=test`, `AUTH_ENFORCED=false` y `TEST_DATABASE_URL` desechable: 194/194 aprobadas. La primera ejecución sin el aislamiento de autenticación produjo 20 redirecciones 303 heredadas; las otras 174 pruebas pasaron y la repetición correctamente aislada quedó verde.
- 4B-3B Alembic/PostgreSQL: `empty → head` en esquema temporal eliminado tras validar; salto desde `20260901_08`, downgrade/re-upgrade, mapeos, seed global, tres índices de tarifa, FK compuesta de SALIDA, dos rechazos defensivos de downgrade y `alembic check` aprobados.
- 4B-3B `python -m compileall -q app tests alembic`: aprobado; `pip check`: `No broken requirements found`; `git diff --check`: aprobado.
- 4B-3C focalizada: 8/8 aprobadas para consultas/proyección, período/búsqueda, tarifa ausente, RBAC, CSRF, privacidad, SALIDA administrativa e incidencias desde HTTP.
- 4B-3C regresión completa de Asistencia con `TEST_DATABASE_URL` desechable: 109/109 aprobadas, incluidas 3/3 de locks/concurrencia PostgreSQL sobre `boliklor_ot_test` en `20260902_09`.
- 4B-3C suite completa aislada con `APP_ENV=test`, `AUTH_ENFORCED=false` y `TEST_DATABASE_URL` desechable: 202/202 aprobadas.
- 4B-3C `python -m compileall -q app tests alembic`: aprobado; `pip check`: `No broken requirements found`; `git diff --check`: aprobado.
- 4B-3D focalizada web/servicios: 24/24 aprobadas para tarifas, RBAC, CSRF, versionado, precedencia, conflictos, Excel conjunto/individual, privacidad y paridad.
- 4B-3D PostgreSQL desechable: `boliklor_ot_test` confirmada en `20260902_09 (head)`; 3/3 pruebas de locks/concurrencia y unicidad de tarifas aprobadas sin usar la base real.
- 4B-3D regresión completa de Asistencia con `TEST_DATABASE_URL` desechable: 116/116 aprobadas.
- 4B-3D suite completa aislada con `APP_ENV=test`, `AUTH_ENFORCED=false` y `TEST_DATABASE_URL` desechable: 209/209 aprobadas.
- 4B-3D `python -m compileall -q app tests alembic`: aprobado; `pip check`: `No broken requirements found`; `git diff --check`: aprobado.

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
- tarifa provisional `$30.000 CLP` por jornada pagable: regla/proyección implementada en 4B-3A y persistencia global/individual versionada implementada en 4B-3B; administración web pendiente;
- horas extra y días extra pendientes de definición posterior.

## 9. Asistencia 4B-3A integrada en `aea9c32`

- [CONFIRMADO] referencias horarias: `DIURNO 09:00–18:00` y `NOCTURNO 19:00–05:00` del día siguiente. `SesionTrabajo.turno_id` y `fecha_operacional` permanecen como hechos y las horas originales no se alteran.
- [IMPLEMENTADO Y TESTEADO] `attendance_rules_service.py` proyecta sesión, día y período, distingue actividad/incompleto y deriva situaciones horarias con la tolerancia configurada de 10 minutos.
- [IMPLEMENTADO Y TESTEADO] Por fecha operacional se paga provisionalmente como máximo una jornada `DIURNO` y una `NOCTURNO`; varias sesiones del mismo turno no multiplican jornadas y ambos turnos forman un doble turno.
- [IMPLEMENTADO Y TESTEADO] Incompletos e incidencias conservan pagabilidad provisional. Un turno sin regla aprobada falla de forma explícita para evitar cálculos silenciosos.
- [IMPLEMENTADO Y TESTEADO] La tarifa individual versionada prevalece sobre la global vigente para cada fecha; el total provisional se deriva y no se persiste.
- [IMPLEMENTADO Y TESTEADO] El calendario personal reutiliza la proyección común de sesión y muestra `Actividad registrada · incompleta` / `Jornada incompleta: falta SALIDA` sin convertirla en ausencia.
- [IMPLEMENTADO EN 4B-3B] La persistencia de tarifas adapta filas ORM a `ProvisionalRateVersion` y reutiliza `resolve_effective_rate`; no existe una segunda regla de precedencia.

## 10. Asistencia 4B-3B integrada en `aea9c32`

- [IMPLEMENTADO Y TESTEADO] `IntervencionSalidaAdministrativa` expresa estructuralmente una SALIDA originalmente ausente y enlaza sesión, SALIDA administrativa, hora introducida, actor, motivo y timestamp. La FK compuesta exige mismo marcaje/sesión/tipo SALIDA y las unicidades impiden duplicados.
- [IMPLEMENTADO Y TESTEADO] `complete_administrative_exit` bloquea la sesión, revalida ENTRADA/ausencia de SALIDA, exige datetime con zona, orden temporal, mínimo de cinco minutos y motivo. SALIDA, auditoría y cierre se confirman o revierten juntos; no crea GPS ni evaluación geográfica.
- [IMPLEMENTADO Y TESTEADO] Incidencias usan `PENDIENTE/APROBADA/RECHAZADA`. `decide_attendance_incident` bloquea, permite una sola decisión final y conserva marcaje, GPS, geocerca, turno, fecha operacional y pagabilidad.
- [IMPLEMENTADO Y TESTEADO] `TarifaProvisionalAsistencia` conserva monto `Numeric(12,0)` positivo, fecha operacional de vigencia, alcance global/Worker, origen, actor y timestamp. Los índices parciales únicos evitan dos versiones del mismo alcance/fecha; individual prevalece sobre global mediante el motor común 4B-3A.
- [IMPLEMENTADO EN MIGRACIÓN CANDIDATA] `20260902_09` prechequea estados/coherencia, mapea `RESUELTA→APROBADA` y `DESCARTADA→RECHAZADA`, y siembra global $30.000 desde la primera fecha operacional real verificada (`2026-09-01`). El downgrade traduce estados de vuelta cuando es seguro y aborta ante intervenciones o tarifas posteriores.
- [IMPLEMENTADO EN 4B-3C/3D] Existen rutas/UI para las acciones de supervisión y tarifas. `ASISTENCIA_SUPERVISAR` autoriza portal/exportaciones y `ADMIN_ACCESS` protege consulta y mutación de tarifas; todos los POST conservan CSRF.

## 11. Asistencia 4B-3C integrada en `72534f5`

- [IMPLEMENTADO Y TESTEADO] Router separado bajo `/asistencia/supervision`, protegido por `ASISTENCIA_SUPERVISAR`; ADMIN y JEFATURA acceden, TRABAJADOR recibe 403 y el anónimo redirección segura a login.
- [IMPLEMENTADO Y TESTEADO] El listado usa período inclusivo, búsqueda por nombre/apellido/código, máximo de 366 días y paginación de 25. Incluye Workers activos aunque no tengan actividad e inactivos cuando conservan sesiones en el período.
- [IMPLEMENTADO Y TESTEADO] `attendance_supervision_service.py` carga Workers, sesiones, turnos, marcajes, snapshots geográficos, incidencias, intervenciones y tarifas por lotes; reutiliza la proyección 4B-3A y no ejecuta una consulta por Worker.
- [IMPLEMENTADO Y TESTEADO] Resumen y calendario muestran días trabajados, actividad, jornadas pagables, dobles turnos, incidencias y total provisional. Los estados se expresan con texto y color; el detalle conserva turno factual, cruces de medianoche, geocerca histórica y decisión administrativa.
- [IMPLEMENTADO Y TESTEADO] Las fechas previas a la primera tarifa muestran `Sin tarifa configurada para la fecha`; no existe fallback retroactivo y el total queda indeterminado.
- [IMPLEMENTADO Y TESTEADO] Completar SALIDA y decidir incidencias usan los servicios transaccionales 4B-3B, actor autenticado, CSRF, mensajes seguros y respuesta 409 para estados concurrentemente finalizados. La SALIDA administrativa queda identificada y no fabrica GPS/geocerca.
- [PRIVACIDAD VALIDADA] Las vistas no incluyen latitud ni longitud exactas; solo lugar, tipo/estado de geocerca y estado de precisión históricos.
- [SIN CAMBIO DE ESQUEMA] 4B-3C no añade migraciones. El head de código continúa en `20260902_09` y `boliklor_ot` real permanece en `20260901_08`.

## 12. Asistencia 4B-3D implementada en el árbol

- [IMPLEMENTADO Y TESTEADO] `/admin/asistencia/tarifas` muestra historial global, actor/origen y creación; permite al ADMIN crear nuevas vigencias globales sin editar/eliminar versiones previas.
- [IMPLEMENTADO Y TESTEADO] El detalle de Worker muestra tarifa efectiva `GLOBAL`/`INDIVIDUAL`, historial exclusivo de overrides y permite nuevas versiones individuales. No copia automáticamente la tarifa global.
- [IMPLEMENTADO Y TESTEADO] Monto entero positivo, fecha, Worker, confirmación, duplicados y campos extra se validan en backend. Los duplicados son 409 controlados; el resto de formularios inválidos es 422. CSRF faltante/inválido es 403.
- [RBAC VALIDADO] ADMIN consulta/muta tarifas; JEFATURA consulta tarifa/total en Supervisión pero recibe 403 en rutas de tarifa; TRABAJADOR recibe 403 y anónimo redirección a login. Las exportaciones usan `ASISTENCIA_SUPERVISAR` para ADMIN/JEFATURA.
- [IMPLEMENTADO Y TESTEADO] XLSX conjunto respeta período y búsqueda, incluye todas las filas filtradas en lotes y reproduce días trabajados, jornadas pagables, dobles turnos, incidencias y total de la proyección compartida.
- [IMPLEMENTADO Y TESTEADO] XLSX individual contiene `Resumen` y `Detalle diario`, incluidos nocturno, incompleto, doble turno, tarifa/origen e incidencias. Una tarifa ausente se expresa como `Sin tarifa configurada` sin fallback ni total inventado.
- [SEGURIDAD/PRIVACIDAD VALIDADA] Toda cadena se neutraliza ante prefijos de fórmula y caracteres XML de control; los nombres de archivo son constantes/seguros y los libros no contienen latitud, longitud ni coordenadas.
- [SIN CAMBIO DE ESQUEMA] 4B-3D no añade migraciones. `boliklor_ot_test` permanece en `20260902_09`; `boliklor_ot` real continúa en `20260901_08` y no fue mutada.
- [PENDIENTE MANUAL] El checklist reproducible para navegador y Excel/LibreOffice está en `docs/operations/attendance-4b3d-manual-validation.md`; no se declara ejecutado en este gate automatizado.

## 13. Punto exacto de continuidad

**Fase activa:** Asistencia 4B-3. Las subfases 4B-3A/3B están integradas en `aea9c32` y 4B-3C en `72534f5`; 4B-3D está implementada y testeada en el árbol sobre esa base. No se marca 4B-3 completa.

**Estado de cierre:** gate automatizado 4B-3D aprobado en pruebas focalizadas, PostgreSQL desechable, regresión de Asistencia y suite completa; todavía sin `git add`, commit o push. La validación manual en navegador/Excel está preparada pero pendiente de ejecución. La base real `boliklor_ot` permanece en `20260901_08` y no recibió ninguna mutación.

**Siguiente gate propuesto:** revisión humana del diff y ejecución del checklist manual 4B-3D contra `boliklor_ot_test`. Después, solo con autorización expresa, decidir commit/push y el gate separado de migración real `20260902_09`. No se avanzó automáticamente.

**Prohibiciones vigentes:** no ejecutar nuevas mutaciones de esquema/datos reales fuera de un gate explícito; no incluir backups, fuentes masivas, wheels, secretos, documentos laborales ni coordenadas exactas en Git o logs/UI no autorizada.
