# Estado actual y continuidad de Boliklor

Este documento es el punto operativo de continuidad del repositorio. Describe el estado verificable del código y reemplaza información obsoleta cuando cambia la fase activa; Git conserva el historial detallado.

## 1. Identificación

- **Proyecto:** Boliklor.
- **Fecha de última actualización:** 2026-09-01 (`America/Santiago`).
- **Rama Git actual:** `main`, con seguimiento de `origin/main`; no se ejecutó `fetch`, por lo que la sincronía remota solo refleja la referencia local.
- **Último commit conocido:** `e9b7ee981445a1ebcd41e63478e14b91f86d7820` (`e9b7ee9`, 2026-08-31), `Implementar base de marcajes geolocalizados de Asistencia 4B-1`.
- **Estado del árbol de trabajo:** con cambios sin commit de Asistencia 4B-2 y 4B-2A, además de documentación operativa. No asumir que estos cambios están integrados en `origin/main`.

Cambios funcionales preexistentes al crear este documento:

- modificados: `ARCHITECTURE.md`, `README.md`, `app/schemas/attendance.py`, `app/services/attendance_marking_service.py`, `app/static/css/styles.css`, `app/templates/attendance/register.html`, `app/web/attendance.py`, `docs/architecture/api.md`, `docs/architecture/frontend.md`, cinco documentos de `docs/product/attendance/` y `tests/test_attendance_structure.py`;
- nuevos: `app/static/js/attendance-register.js` y `tests/test_attendance_web_marking.py`.

## 2. Objetivo actual del sistema

[IMPLEMENTADO] Boliklor es una aplicación web interna para autenticación y administración de usuarios/trabajadores, catálogo e inventario, órdenes de trabajo heredadas y asistencia personal. 4B-2 registra `ENTRADA`/`SALIDA` con GPS puntual; 4B-2A conecta esos eventos reales con el calendario mensual y centraliza parámetros horarios base.

No existe evidencia versionada de un despliegue productivo. Compras, remuneraciones, BI y otros módulos ERP no forman parte del sistema actual.

## 3. Arquitectura actual

- **Forma de despliegue:** una aplicación FastAPI; organización actual por capas con dirección objetivo de monolito modular.
- **Backend:** Python, FastAPI y Uvicorn.
- **Frontend operativo:** Jinja2, HTML, CSS y JavaScript en `app/templates` y `app/static`, servido por FastAPI. `frontend/` es un prototipo histórico y no la UI activa.
- **Base de datos prevista por configuración:** PostgreSQL mediante `DATABASE_URL`.
- **ORM y driver:** SQLAlchemy 2 y Psycopg 3.
- **Migraciones:** Alembic, con una cadena lineal de siete revisiones.
- **Validación:** Pydantic en schemas y formularios seleccionados.
- **Autenticación:** contraseñas Argon2id, sesiones opacas revocables, cookies HttpOnly/SameSite Lax, CSRF y RBAC por capacidades en código. Auth está activa por defecto y solo puede desactivarse en `development` o `test`.
- **Archivos:** OpenPyXL para importación Excel; justificantes en almacenamiento privado configurable.
- **Tiempo:** timestamps persistidos con zona/UTC y conversión operacional mediante `APP_TIMEZONE`.
- **Testing:** `unittest`, SQLite aislada para la suite funcional y PostgreSQL local sólo para verificaciones Alembic de lectura/paridad autorizadas.

Flujo predominante: `app/web` o `app/api` -> `app/services` -> `app/models`/`app/database`. `app/core` contiene configuración, seguridad y tiempo transversales.

## 4. Estructura relevante del proyecto

```text
.
|-- AGENTS.md                     # Contrato de trabajo y continuidad
|-- ARCHITECTURE.md               # Arquitectura vigente/objetivo
|-- CURRENT.md                    # Punto operativo de continuidad
|-- README.md                     # Instalación y uso general
|-- requirements.txt              # Dependencias Python
|-- alembic/
|   |-- env.py
|   `-- versions/                 # Siete revisiones lineales
|-- app/
|   |-- api/                      # API JSON de productos y OT
|   |-- core/                     # Configuración, seguridad, tiempo
|   |-- database/                 # Engine, sesiones y Base ORM
|   |-- models/                   # 22 modelos/tablas ORM
|   |-- schemas/                  # Contratos Pydantic
|   |-- services/                 # Casos de uso y reglas
|   |-- web/                      # Rutas server-rendered
|   |-- templates/                # UI Jinja2 activa
|   |-- static/                   # CSS, JS e imagen activa
|   |-- scripts/create_admin.py   # Alta interactiva del primer ADMIN
|   `-- main.py                   # Composición FastAPI
|-- docs/
|   |-- architecture/             # Arquitectura por tema
|   |-- decisions/                # ADR-001 a ADR-005
|   |-- product/                  # Asistencia, RRHH e Inventario
|   |-- standards/                # Estándares técnicos
|   |-- audit/                    # Baselines/auditorías históricas
|   `-- plans/active/             # Roadmap y producción temprana
|-- tests/                        # 14 archivos de pruebas
`-- frontend/                     # Prototipo estático histórico
```

## 5. Módulos del sistema

| Módulo | Estado | Observaciones |
| --- | --- | --- |
| Identidad y acceso | FUNCIONAL | Login/logout, sesiones, CSRF, roles, alta administrativa, activación y restablecimiento con contraseña temporal. Faltan rate limit, MFA/recuperación y auditoría privilegiada para producción. |
| Recursos Humanos | FUNCIONAL PARCIAL | CRUD básico de `Trabajador`, empresa, estado y cuenta opcional. `Trabajador` sigue alojado físicamente en `identity.py`; no existe ciclo laboral completo. |
| Asistencia | FUNCIONAL PARCIAL | 4B-2 y 4B-2A están automatizada y manualmente validadas en navegador, pero siguen sin commit/push. Faltan zonas reales verificadas y supervisión 4B-3, jornadas pagables, revisión/corrección, planificación, ausencia confirmada y exportación. |
| Inventario | FUNCIONAL PARCIAL | Catálogo/importación, recepciones, ledger, stock, inicialización y costos. No hay flujo completo de salidas/ajustes ni lotes/vencimientos/bodegas. |
| Órdenes de trabajo | FUNCIONAL | Creación, revisión, confirmación, historial y detalle; es funcionalidad heredada fuera de expansión sin decisión expresa. |

## 6. Funcionalidades implementadas

### Identidad y acceso

- [IMPLEMENTADO] Login, logout, cambio obligatorio de contraseña temporal y sesiones revocables.
- [IMPLEMENTADO] CSRF para mutaciones con cookie y autorización backend por módulo/capacidad.
- [IMPLEMENTADO] Roles `ADMIN`, `JEFATURA` y `TRABAJADOR`.
- [IMPLEMENTADO] ADMIN lista/crea/edita trabajadores; crea usuarios, cambia su estado y restablece contraseñas.
- [IMPLEMENTADO] Separación 0..1 entre `Usuario` y `Trabajador`.

### Recursos Humanos

- [IMPLEMENTADO] Ficha laboral mínima con nombres, apellidos, código interno, empresa y estado activo.
- [DEUDA_TECNICA] El ownership conceptual es RRHH, pero el modelo y la administración continúan combinados con Identidad.

### Asistencia

- [IMPLEMENTADO] Lugares `BASE`/`TALLER`/`TERRENO`, coordenadas/radio opcionales y asignaciones históricas trabajador-lugar.
- [IMPLEMENTADO] Turnos de catálogo, calendario personal neutro, justificantes y descarga privada con ownership.
- [IMPLEMENTADO 4B-1] Sesiones de trabajo con varias jornadas por día, eventos únicos `ENTRADA`/`SALIDA`, intervalo mínimo configurable, cierre por propietario y hora oficial del servidor.
- [IMPLEMENTADO 4B-1] Evidencia GPS separada de la evaluación; Haversine contra la zona activa más cercana; incidencias `FUERA_RANGO` y `GPS_BAJA_PRECISION`; registro permitido cuando no hay zona configurada.
- [IMPLEMENTADO EN ÁRBOL 4B-2] GET/POST `/mi-asistencia/registrar`, estado de sesión, turno solo para entrada, sesión abierta derivada para salida, ownership desde la sesión, rol trabajador, CSRF y mensajes seguros.
- [IMPLEMENTADO EN ÁRBOL 4B-2] `getCurrentPosition` se invoca solo al enviar el formulario; no hay `watchPosition`, tracking continuo ni persistencia cliente.
- [IMPLEMENTADO EN ÁRBOL 4B-2A] Calendario mensual derivado de sesiones, marcajes, evaluaciones e incidencias del Worker autenticado.
- [IMPLEMENTADO EN ÁRBOL 4B-2A] Una fecha exige al menos una sesión cerrada con entrada/salida; varias sesiones siguen siendo una fecha y conservan detalle.
- [IMPLEMENTADO EN ÁRBOL 4B-2A] Verde trabajado, amarillo revisión/tardanza, naranja fuera de rango y neutral sin información suficiente; no se infiere ausencia ni día no laboral.
- [IMPLEMENTADO EN ÁRBOL 4B-2A] Horarios `09:00`–`18:00` y `19:00`–`06:00`, tolerancia 10 minutos y tarifa provisional `30000` centralizados, sin cálculo de pagos u horas extra.

### Inventario

- [IMPLEMENTADO] Empresas, unidades de medida, productos, alta y filtros.
- [IMPLEMENTADO] Análisis/importación Excel y corrección previa de productos.
- [IMPLEMENTADO] Recepciones transaccionales, movimientos/detalles, historial y detalle.
- [IMPLEMENTADO] Stock derivado del ledger por empresa, modo de transición/inicialización y consulta de costos.

### Órdenes de trabajo

- [IMPLEMENTADO] Flujos web de nueva OT, revisión, confirmación, historial y detalle.
- [IMPLEMENTADO] API JSON para crear, listar y obtener OT.

## 7. Base de datos y migraciones

El ORM declara 22 tablas:

- **Identidad/RRHH:** `usuarios`, `roles`, `usuarios_roles`, `trabajadores`, `sesiones_usuario`.
- **Inventario:** `empresas`, `unidades_medida`, `productos`, `movimientos_inventario`, `detalle_movimientos_inventario`.
- **OT heredada:** `ordenes_trabajo`, `productos_ot`.
- **Asistencia:** `lugares_trabajo`, `asignaciones_trabajador_lugar`, `turnos`, `justificaciones_inasistencia`, `sesiones_trabajo`, `marcajes_asistencia`, `evidencias_gps_marcaje`, `evaluaciones_geograficas_marcaje`, `incidencias_asistencia`, `correcciones_marcaje`.

Relaciones importantes:

- `Usuario` tiene roles N:M, sesiones y un `Trabajador` opcional; `Trabajador` puede existir sin cuenta.
- `Trabajador` referencia empresa y es referenciado por asignaciones, justificaciones y sesiones de asistencia.
- `SesionTrabajo` pertenece a trabajador/turno y contiene marcajes; cada marcaje tiene una evidencia y evaluación geográfica, y puede generar incidencias/correcciones.
- `Producto` pertenece a empresa y unidades; movimiento/detalle forma el ledger del cual se deriva stock.
- `OrdenTrabajo` contiene `ProductoOT` con borrado en cascada.

Cadena Alembic verificada estáticamente:

1. `20260826_01`: persistencia inicial de OT.
2. `20260826_02`: base de inventario.
3. `20260827_03`: movimientos de inventario.
4. `20260828_04`: identidad, autenticación y roles.
5. `20260829_05`: contraseña temporal.
6. `20260830_06`: estructura de asistencia.
7. `20260831_07`: sesiones, marcajes, GPS, evaluaciones, incidencias y correcciones.

- **Head conocido del código:** `20260831_07`.
- **Migraciones creadas no aplicadas:** ninguna detectada. El 2026-09-01, `alembic current` confirmó `20260831_07 (head)` y `alembic check` informó `No new upgrade operations detected`. No se ejecutó upgrade/downgrade ni se modificaron datos.
- [CONFIRMADO EN DOCUMENTACIÓN PREVIA] 4B-1 registró pruebas sobre PostgreSQL desechable de upgrade, downgrade/re-upgrade, constraints, índice parcial, locks, concurrencia, rollback y `alembic check`. No se repitieron en esta sesión.

## 8. API y rutas principales

- **Sistema:** `GET /` y `GET /health` (liveness superficial).
- **Autenticación:** `GET/POST /login`, `POST /logout`, `GET/POST /cambiar-password`.
- **Dashboard:** `GET /dashboard`.
- **Administración:** `/admin/trabajadores`, `/admin/usuarios`, `/admin/lugares` y `/admin/asignaciones`, con GET/POST de sus flujos.
- **Asistencia personal:** `GET /mi-asistencia`, `GET/POST /mi-asistencia/registrar`, `GET /mi-asistencia/justificaciones`, `GET/POST /mi-asistencia/justificar` y descarga del archivo propio.
- **Productos web:** `/productos`, `/productos/nuevo` y flujo de importación/análisis/corrección.
- **Inventario web:** `/inventario/recepcion`, `/inventario/movimientos`, detalle, `/inventario/stock/boliklor`, `/inventario/stock/alm`, `/inventario/inicializacion` y `/inventario/costos`.
- **OT web:** `/ordenes-trabajo`, nueva, revisar, confirmar y detalle.
- **API productos:** `GET /api/productos/buscar`, limitada por empresa y a 12 resultados activos.
- **API OT:** `POST/GET /api/ordenes-trabajo` y `GET /api/ordenes-trabajo/{orden_id}`.

Los routers se protegen en `app/main.py` por acceso de plataforma o módulo; las mutaciones web conservan CSRF mediante la capa de seguridad.

## 9. Tests y validaciones

Existen 14 archivos y 154 métodos `test_`. Cubren web general/OT, identidad y administración, inventario, importación, baseline Alembic y Asistencia estructural, marcajes, flujo web 4B-2 y calendario 4B-2A.

Comando ejecutado el 2026-09-01 con SQLite en memoria:

```powershell
$env:APP_ENV='test'
$env:AUTH_ENFORCED='false'
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m compileall -q app tests alembic
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado:

- compilación: aprobada;
- `pip check`: aprobado, `No broken requirements found`;
- suite completa: `Ran 154 tests` — 154 aprobadas, 0 fallidas y 0 errores;
- suite focalizada de calendario/estructura/marcaje web: 43 aprobadas;
- Alembic: `heads` y `current` en `20260831_07`; `check` sin operaciones nuevas.

[CONFIRMADO 2026-09-01] El bloqueo previo de la DLL Argon2 no se reprodujo. El usuario validó manualmente 4B-2 y 4B-2A en navegador: ENTRADA, geolocalización puntual, rechazo de SALIDA antes de 5 minutos, SALIDA posterior correcta, sesión cerrada reflejada en calendario, detalle diario y clasificación de un marcaje fuera del horario normal como revisión. El resto del flujo probado funcionó correctamente.

## 10. Problemas conocidos

### Problemas confirmados

- [DEUDA_TECNICA] No hay CI/CD, contenedores, proxy/TLS, backups/restore, monitorización ni artefactos de despliegue versionados; `/health` no valida DB ni dependencias.
- [DEUDA_TECNICA] RBAC permanece hardcodeado; faltan rate limit de login, cabeceras de seguridad/proxy y auditoría privilegiada.
- [DEUDA_TECNICA] `Trabajador` pertenece conceptualmente a RRHH pero reside en `app/models/identity.py`.
- [DEUDA_TECNICA] Stock se calcula recorriendo el ledger; faltan salidas/ajustes operativos completos y lotes/vencimientos.
- [PENDIENTE] No existe política de negocio/legal aprobada para retención y exposición de GPS, justificantes y datos laborales.
- [PENDIENTE] Los cambios funcional y manualmente validados de 4B-2 + 4B-2A aún deben revisarse, stagearse, commitearse y pushearse.
- [PENDIENTE] Configurar y validar posteriormente las zonas reales de trabajo, sus coordenadas y radios autorizados.

### Pendiente de investigación

- [PENDIENTE] Estado aplicado de Alembic en entornos distintos de la PostgreSQL local verificada.
- [PENDIENTE] Compatibilidad efectiva de geolocalización con los navegadores/dispositivos del piloto y su configuración HTTPS.

## 11. Trabajo realizado en la última fase

- **Objetivo de la fase:** Asistencia 4B-2A, calendario real y parámetros horarios base.
- **Cambios implementados en el árbol:** proyección mensual sobre sesiones/marcajes/incidencias, detalle por fecha, clasificación visual, parámetros horarios/tolerancia/tarifa provisional y documentación de 4B-3.
- **Archivos principales:** `app/services/attendance_calendar_service.py`, `app/core/config.py`, `app/web/attendance.py`, `app/templates/attendance/calendar.html`, `app/static/css/styles.css` y `.env.example`.
- **Tests relacionados:** nuevo `tests/test_attendance_calendar.py` y regresión web en `tests/test_attendance_structure.py`.
- **Resultado:** [CONFIRMADO 2026-09-01] 154/154 tests aprobados, Alembic en head y sin drift, y 4B-2 + 4B-2A validadas manualmente en navegador. Pendiente consolidar los cambios en Git.

## 12. Punto EXACTO de continuidad

**Módulo actual:** Asistencia.

**Fase actual:** 4B-2A, calendario real y parámetros horarios base.

**Último paso completado:** validación manual de 4B-2 + 4B-2A: ENTRADA/GPS, mínimo de 5 minutos, SALIDA, calendario real, detalle diario y clasificación visual de revisión; previamente se aprobaron 154/154 tests y Alembic sin drift.

**Estado actual:** 4B-2 y 4B-2A están funcionales y validadas automática y manualmente, pero permanecen en un árbol sin commit/push; 4B-1 sigue siendo el último commit.

**Problema actual, si existe:** no hay un problema funcional confirmado en el flujo validado. Falta consolidar 4B-2 + 4B-2A en Git y después configurar/validar las zonas reales de trabajo.

**Siguiente paso recomendado:** revisar el diff completo, stagear los archivos aprobados, crear el commit y hacer push. Después configurar/validar zonas reales de trabajo y recién entonces continuar con Asistencia 4B-3.

**Archivos que probablemente deben revisarse primero:**

1. `app/services/attendance_calendar_service.py`
2. `app/templates/attendance/calendar.html`
3. `app/web/attendance.py`
4. `app/core/config.py`
5. `tests/test_attendance_calendar.py`
6. `tests/test_attendance_structure.py`

**Prueba o comando que debería ejecutarse antes de continuar:**

```powershell
$env:APP_ENV='test'
$env:AUTH_ENFORCED='false'
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
.\.venv\Scripts\python.exe -m compileall -q app tests alembic
if ($LASTEXITCODE -eq 0) { .\.venv\Scripts\python.exe -m unittest discover -s tests -v }
```

## 13. Próximos pasos

### Inmediato

1. Revisar y aprobar el diff completo de 4B-2 + 4B-2A.
2. Stagear únicamente los archivos aprobados, crear el commit y hacer push.
3. Confirmar que el repositorio remoto contenga la fase validada.

### Después

1. Configurar las zonas reales de trabajo con coordenadas/radios autorizados y validar dentro/fuera de rango.
2. Continuar con **Asistencia 4B-3 — Supervisión, reportes y jornadas pagables**, cuyo alcance confirmado incluye:
   - portal para ADMIN/JEFATURA;
   - listado de todos los trabajadores;
   - búsqueda/filtro por nombre y filtro por período;
   - calendario y detalle individual;
   - días trabajados y jornadas pagables como conceptos distintos;
   - doble turno diferenciable e incidencias;
   - exportación individual y conjunta a Excel;
   - tarifa provisional de `$30.000 CLP` por jornada pagable, todavía no implementada;
   - horas extra y días extra pendientes de definición posterior.
3. Cerrar decisiones de planificación, ausencia, aprobación de jornadas, permisos de JEFATURA y retención GPS.

### Futuro

- Exportación mensual de Asistencia, alertas y mejoras de RRHH.
- OT, compras, BI u otros módulos solo después de discovery y decisión explícita.

## 14. Decisiones que NO deben cambiarse sin revisión

- Mantener una sola aplicación y una sola PostgreSQL, evolucionando incrementalmente hacia monolito modular; no introducir microservicios sin evidencia/ADR.
- Respetar `web/api -> services -> models/database`; evitar reglas de negocio en templates y SQL directo fuera de persistencia.
- Identidad es dueña de cuenta/credencial/sesión; RRHH es dueño conceptual de `Trabajador`; Asistencia lo referencia sin duplicarlo.
- Auth debe fallar cerrada en staging/producción; conservar Argon2id, sesiones opacas, CSRF y autorización backend.
- La UI activa está en `app/templates`/`app/static`; `frontend/` no debe tratarse como aplicación activa ni introducirse un framework cliente sin decisión arquitectónica.
- GPS de asistencia se captura solo al marcar, nunca en seguimiento continuo; la hora del servidor es autoritativa y la evaluación derivada permanece separada de la evidencia.
- Stock deriva del ledger y las correcciones deben ser compensatorias/auditables; no sustituirlo por un saldo mutable sin decisión.
- Todo cambio de esquema requiere una migración Alembic nueva; no editar historial compartido ni aplicar migraciones sin entorno y autorización confirmados.
- Fechas persistidas en UTC y se interpretan operacionalmente con `APP_TIMEZONE`.
- No ampliar Órdenes de trabajo ni diseñar otros módulos ERP sin aprobación explícita.

## 15. Comandos útiles para retomar

Desde PowerShell:

```powershell
Set-Location 'C:\Users\soporte\Desktop\Backend\boliklor_ot_backend'

# Activar el entorno existente
.\.venv\Scripts\Activate.ps1

# Crear entorno e instalar dependencias en un equipo nuevo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Preparar configuración local; completar solo en .env y no versionarla
Copy-Item .env.example .env

# Ejecutar la aplicación una vez configurado .env
python -m uvicorn app.main:app --reload

# Validación aislada; no usa PostgreSQL real
$env:APP_ENV='test'
$env:AUTH_ENFORCED='false'
$env:DATABASE_URL='sqlite+pysqlite:///:memory:'
python -m compileall -q app tests alembic
python -m pip check
python -m unittest discover -s tests -v

# Revisar migraciones solo después de confirmar la DB configurada
python -m alembic current
python -m alembic heads

# Revisar Git
git status --short --branch
git diff --stat
git diff
git log -5 --oneline --decorate
```

No hay contraseñas, tokens, claves, URLs de DB ni coordenadas reales en este documento.
