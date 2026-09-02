# Sistema web Boliklor

Aplicación web interna de Boliklor para administrar progresivamente autenticación, usuarios, trabajadores, inventario, productos, movimientos, recepciones, stock, costos, órdenes de trabajo y asistencia.

El sistema se ejecuta como una aplicación web servida por FastAPI. No depende de una aplicación Android.

## Estado actual

Actualmente están implementados:

- autenticación, sesiones, CSRF y autorización por roles;
- administración de usuarios y trabajadores;
- catálogo e importación de productos;
- recepción y movimientos de inventario;
- consulta de stock por empresa, inicialización y costos;
- creación, revisión, confirmación e historial de órdenes de trabajo;
- base estructural de Asistencia: lugares, asignaciones históricas, turnos, calendario personal y justificaciones.

Asistencia 4B-1 implementa el modelo y servicio interno de sesiones, marcajes y evidencia GPS. Asistencia 4B-2 incorpora el flujo web protegido para ENTRADA/SALIDA y solicita geolocalización únicamente al pulsar el botón de marcaje. Consulta [Estado del módulo Asistencia](#estado-del-módulo-asistencia) para conocer el alcance exacto.

Asistencia 4B-2A conecta el calendario personal con sesiones y marcajes reales. Una fecha se muestra como trabajada cuando contiene al menos una sesión cerrada con `ENTRADA` y `SALIDA`; varias sesiones conservan su detalle, pero cuentan como una sola fecha trabajada. Incidencias y fuera de rango cambian la clasificación visual sin borrar el hecho registrado.

Asistencia 4B-2B, implementada actualmente en el árbol, incorpora geocercas `RADIO` y `COMUNA`, detección automática entre todas las zonas activas y una tolerancia comunal configurable. El catálogo versionado contiene únicamente las 13 comunas aprobadas y usa `CUT_COM` como identidad territorial.

## Tecnologías

- **Backend:** Python y FastAPI
- **Servidor ASGI:** Uvicorn
- **Base de datos:** PostgreSQL
- **ORM:** SQLAlchemy 2
- **Migraciones:** Alembic
- **Frontend integrado:** HTML, CSS, JavaScript y Jinja2
- **Validación:** Pydantic
- **Acceso PostgreSQL:** Psycopg 3
- **Seguridad:** sesiones revocables, cookies HttpOnly, CSRF, Argon2id y autorización por roles
- **Archivos Excel:** OpenPyXL
- **Geometría geográfica:** Shapely 2.1.2 y pyproj 3.7.2
- **Pruebas:** biblioteca estándar `unittest`

Las dependencias y los rangos actualmente definidos por el proyecto se encuentran en `requirements.txt`; algunas dependencias todavía no están fijadas a una versión exacta.

## Arquitectura y estructura

```text
.
|-- alembic/             # Entorno y revisiones de migración
|-- app/
|   |-- api/             # Endpoints JSON
|   |-- core/            # Configuración, seguridad y manejo horario
|   |-- database/        # Engine, sesiones y Base de SQLAlchemy
|   |-- models/          # Modelos ORM
|   |-- schemas/         # Validación y contratos de entrada
|   |-- scripts/         # Utilidades administrativas
|   |-- services/        # Reglas de negocio
|   |-- static/          # CSS y JavaScript de la aplicación
|   |-- templates/       # Plantillas Jinja2
|   |-- web/             # Rutas HTML
|   `-- main.py          # Aplicación FastAPI
|-- docs/                # Decisiones y documentación complementaria
|-- frontend/            # Prototipo estático histórico/de referencia
|-- output/              # Salidas locales; no se versiona
|-- tests/               # Suite automatizada
|-- .env.example         # Plantilla pública de configuración
|-- alembic.ini
`-- requirements.txt
```

La interfaz operativa está integrada en `app/templates` y `app/static` y se sirve desde FastAPI. El directorio `frontend/` contiene un prototipo estático de referencia; no es necesario levantarlo con Live Server para utilizar la aplicación actual.

## Instalación en un equipo nuevo

### Requisitos previos

En Windows instala:

- Git;
- Python 3;
- PostgreSQL;
- Visual Studio Code, recomendado.

Comprueba las herramientas desde PowerShell:

```powershell
git --version
python --version
psql --version
```

### 1. Clonar

```powershell
git clone https://github.com/bsepulvedam/Proyecto.git
cd Proyecto
```

Los comandos restantes deben ejecutarse desde la raíz que contiene `app/`, `alembic.ini` y `requirements.txt`.

### 2. Crear y activar el entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, habilítala solo para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## PostgreSQL

Cada desarrollador necesita una instancia PostgreSQL accesible. Para desarrollo local puede crear la base `boliklor_ot` mediante pgAdmin o PowerShell:

```powershell
psql -U postgres -c "CREATE DATABASE boliklor_ot;"
```

No crees las tablas manualmente: Alembic se encarga del esquema. El usuario, contraseña, host, puerto y base se configuran mediante `DATABASE_URL` en el archivo local `.env`.

## Configuración de .env

`.env` contiene configuración local y **no se versiona**. `.env.example` sí se versiona porque solo sirve como plantilla.

```powershell
Copy-Item .env.example .env
```

Edita tu copia de `.env` sin compartirla ni subirla a Git. Las variables actuales son:

| Variable | Propósito |
|---|---|
| `DATABASE_URL` | URL SQLAlchemy de la instancia PostgreSQL del desarrollador. |
| `SESSION_SECRET` | Secreto aleatorio usado para proteger sesiones. |
| `APP_ENV` | Entorno explícito: `development`, `test`, `staging` o `production`. |
| `AUTH_ENFORCED` | Activa la autenticación y autorización de la plataforma. |
| `COOKIE_SECURE` | Exige HTTPS para enviar cookies cuando está activo. |
| `SESSION_HOURS` | Duración de las sesiones. |
| `APP_TIMEZONE` | Zona horaria operacional, normalmente `America/Santiago`. |
| `ATTENDANCE_MIN_SESSION_MINUTES` | Intervalo mínimo entre ENTRADA y SALIDA; valor confirmado: 5. |
| `ATTENDANCE_MAX_GPS_ACCURACY_METERS` | Umbral que genera incidencia de baja precisión; valor confirmado: 100. |
| `ATTENDANCE_COMMUNE_BOUNDARY_TOLERANCE_METERS` | Tolerancia exterior para geocercas comunales; valor provisional: 100 m. |
| `ATTENDANCE_DAY_SHIFT_START` | Inicio base del turno diurno; valor confirmado: `09:00`. |
| `ATTENDANCE_DAY_SHIFT_END` | Fin base del turno diurno; valor confirmado: `18:00`. |
| `ATTENDANCE_NIGHT_SHIFT_START` | Inicio base de la ventana nocturna; valor confirmado: `19:00`. |
| `ATTENDANCE_NIGHT_SHIFT_END` | Fin base de la ventana nocturna del día siguiente; valor confirmado: `06:00`. |
| `ATTENDANCE_LATE_TOLERANCE_MINUTES` | Tolerancia base para clasificación derivada de tardanza; valor confirmado: 10. |
| `ATTENDANCE_DAILY_RATE_CLP` | Tarifa provisional para la futura 4B-3; default `30000`, actualmente no interviene en cálculos. |
| `JUSTIFICATION_STORAGE_DIR` | Directorio privado de archivos de justificación. |
| `JUSTIFICATION_MAX_MB` | Tamaño máximo permitido para cada archivo. El valor de referencia actual es 8 MB. |
| `PRODUCT_IMPORT_FILE` | Ruta opcional al Excel legacy usado por importación y stock transitorio. |

Genera un `SESSION_SECRET` propio:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Para desarrollo local por HTTP, una configuración coherente incluye:

```dotenv
APP_ENV=development
APP_TIMEZONE=America/Santiago
AUTH_ENFORCED=true
COOKIE_SECURE=false
```

`COOKIE_SECURE=false` es únicamente apropiado para HTTP local. En producción debe utilizarse HTTPS y configurarse `COOKIE_SECURE=true`. Nunca copies contraseñas, credenciales, API keys o secretos reales al README, a `.env.example` o al repositorio.

La autenticación está activa por defecto. `AUTH_ENFORCED=false` solo se acepta cuando `APP_ENV` es explícitamente `development` o `test`; `staging`, `production`, un entorno ausente o un booleano inválido fallan de forma segura.

## Migraciones

Después de crear PostgreSQL y configurar `.env`:

```powershell
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
```

El HEAD actual del código es:

```text
20260901_08
```

En un clon nuevo, `alembic upgrade head` crea y actualiza todas las tablas hasta esa revisión.

La cadena estática se valida en la suite. Las pruebas destructivas de upgrade/downgrade deben usar exclusivamente una PostgreSQL desechable según [Validación segura de migraciones](docs/operations/migration-validation.md), nunca la base local con datos reales.

## Crear el primer ADMIN

Después de aplicar las migraciones:

```powershell
python -m app.scripts.create_admin
```

El script solicita interactivamente el username o email, la contraseña y su confirmación. Crea una cuenta con rol `ADMIN` y exige una contraseña de al menos 12 caracteres. No existe una contraseña predeterminada.

No compartas la contraseña ni la guardes en este documento. Si ya existe un ADMIN inicial, no es necesario repetir este paso.

## Ejecutar la aplicación

```powershell
python -m uvicorn app.main:app --reload
```

Abre:

- aplicación: <http://127.0.0.1:8000>
- login: <http://127.0.0.1:8000/login>
- Swagger: <http://127.0.0.1:8000/docs>
- salud del servicio: <http://127.0.0.1:8000/health>

Detén el servidor con `Ctrl+C`.

## URLs principales

El acceso efectivo depende del rol y de la autorización backend.

| Área | Ruta | Estado actual |
|---|---|---|
| Autenticación | `/login` | Inicio de sesión |
| General | `/dashboard` | Dashboard administrativo/operacional |
| Productos | `/productos` | Catálogo y filtros |
| Inventario | `/inventario/recepcion` | Registro de recepciones |
| Inventario | `/inventario/movimientos` | Historial y detalle de movimientos |
| Inventario | `/inventario/stock/boliklor` | Stock Boliklor |
| Inventario | `/inventario/stock/alm` | Stock ALM |
| Inventario | `/inventario/costos` | Consulta de costos |
| Inventario | `/inventario/inicializacion` | Inicialización administrativa |
| OT | `/ordenes-trabajo` | Historial de órdenes |
| OT | `/ordenes-trabajo/nueva` | Nueva orden |
| Administración | `/admin/trabajadores` | Trabajadores |
| Administración | `/admin/usuarios` | Usuarios |
| Administración | `/admin/lugares` | Lugares de trabajo |
| Administración | `/admin/asignaciones` | Asignaciones históricas |
| Trabajador | `/mi-asistencia` | Calendario personal |
| Trabajador | `/mi-asistencia/registrar` | Estado y registro personal de ENTRADA/SALIDA con GPS puntual |
| Trabajador | `/mi-asistencia/justificaciones` | Listado personal |
| Trabajador | `/mi-asistencia/justificar` | Nueva justificación |

## Roles

- **ADMIN:** accede a los módulos operacionales autorizados y administra trabajadores, usuarios, lugares y asignaciones.
- **JEFATURA:** rol preparado para la futura supervisión. Actualmente no debe interpretarse como un panel completo de asistencia.
- **TRABAJADOR:** aterriza en `/mi-asistencia` y utiliza un sidebar reducido con Días trabajados, Registrar asistencia y Justificar inasistencia.

Ocultar enlaces en el sidebar no sustituye la seguridad: las rutas mantienen autorización backend.

## Usuarios y contraseñas

No existe auto-registro público. El flujo administrado es:

```text
ADMIN crea la cuenta
  -> se genera una contraseña temporal
  -> el usuario inicia sesión
  -> debe reemplazarla obligatoriamente
```

Un ADMIN puede restablecer la contraseña de una cuenta. El restablecimiento genera una nueva contraseña temporal, revoca las sesiones existentes y obliga a cambiarla nuevamente.

El ADMIN no puede recuperar ni visualizar la contraseña personal del usuario. Las contraseñas se almacenan mediante hash Argon2id.

## Estado del módulo Asistencia

### Implementado

- trabajadores, usuarios y roles;
- catálogo de lugares de trabajo;
- Base Boliklor - La Pintana;
- Taller Boliklor - La Pintana;
- zonas `RADIO` o `COMUNA` administrables por ADMIN;
- catálogo versionado de 13 comunas SUBDERE DPA 2023, seleccionadas exclusivamente por `CUT_COM`;
- direcciones, coordenadas de referencia, radios y prioridades configurables;
- asignaciones históricas trabajador-lugar;
- turnos `DIURNO` y `NOCTURNO`;
- landing, calendario mensual y navegación personal del trabajador;
- creación y listado personal de justificaciones;
- carga privada y validada de documentos;
- estados `PENDIENTE`, `APROBADA` y `RECHAZADA`.
- modelo de sesiones con múltiples jornadas por día operacional;
- eventos únicos `ENTRADA`/`SALIDA` con hora oficial del servidor;
- evidencia GPS separada de evaluación geográfica;
- evaluación automática de todas las zonas activas, sin asignación ni selección del trabajador;
- selección determinística por estado, prioridad, margen e ID;
- resultados `DENTRO_RANGO`, `DENTRO_TOLERANCIA`, `FUERA_RANGO` y `SIN_ZONA_CONFIGURADA`, con snapshot de tipo/tolerancia/versión geométrica;
- incidencias `FUERA_RANGO` y `GPS_BAJA_PRECISION`;
- servicio transaccional interno reutilizado por la ruta web protegida;
- endpoint web autenticado con ownership derivado de la sesión, permiso backend y CSRF;
- pantalla de estado con sesión abierta, turno, hora de entrada y única acción disponible;
- captura GPS del navegador solo al marcar, sin tracking continuo, y evaluación de geocerca en backend;
- mensajes seguros para éxito, fuera de rango, baja precisión y ausencia de zonas configuradas.
- calendario mensual derivado de sesiones/marcajes reales, con una sola fecha trabajada aunque existan varias sesiones;
- detalle personal por fecha con turno, entrada, salida, duración, número de sesiones e incidencias, sin exponer GPS exacto;
- clasificación verde para fecha trabajada, amarilla para revisión/tardanza, naranja para fuera de rango y neutral cuando no hay información suficiente.

### Todavía no implementado

- mapas o visualización de coordenadas;
- workflow administrativo de revisión/corrección;
- alertas de asistencia;
- planificación diaria previa;
- supervisión completa de JEFATURA;
- interfaz completa de aprobación/rechazo de justificaciones para ADMIN/JEFATURA.
- jornadas pagables, dobles turnos pagables, horas extra, días extra, remuneración y reportes/exportación 4B-3.

La ruta `/mi-asistencia/registrar` muestra el estado de la sesión y permite registrar ENTRADA o SALIDA. El cliente no elige trabajador, sesión, zona, fecha ni hora oficial; el servidor deriva ownership y conserva la autoridad temporal.

### Decisiones arquitectónicas

- `DIURNO` y `NOCTURNO` son turnos, no tipos de marcaje.
- Un trabajador podrá tener múltiples sesiones en un mismo día operacional y abrir otra después de cerrar la anterior, incluido un turno nocturno que cruce medianoche.
- Cada sesión tiene `ENTRADA` y `SALIDA`; se impiden duplicados y una salida antes de 5 minutos. El valor está centralizado en `ATTENDANCE_MIN_SESSION_MINUTES`.
- Base y Taller de La Pintana son conceptos diferentes aunque compartan o tengan una ubicación física cercana.
- La hora del servidor será autoritativa y `APP_TIMEZONE` determinará el día operacional.
- Entrada y salida usan evidencia de ubicación obligatoria en el servicio; el backend evalúa geocercas `RADIO`/`COMUNA`. Fuera de rango y precisión mayor a 100 m se conservan como incidencias, no como rechazo; `DENTRO_TOLERANCIA` se persiste sin incidencia automática.
- No se genera una ausencia automática por falta de marcaje: primero será `PENDIENTE_DE_REVISION` y solo podrá calcularse atraso con una hora esperada válida.
- Actualmente no existe planificación diaria que determine que una persona debía asistir.
- Un día neutro en el calendario significa “sin registros”, no “ausente”.
- Una sesión abierta no constituye todavía una fecha completamente trabajada.
- La salida diurna entre `18:01` y `18:59` no genera horas extra, recargos ni incidencias automáticas.
- Días trabajados, sesiones y futuras jornadas pagables son conceptos distintos; 4B-2A no calcula pagos.
- Las 13 comunas iniciales son zonas amplias derivadas de la fuente oficial y podrán refinarse posteriormente en lugares o faenas específicos. La geometría se identifica por `CUT_COM`, no por nombre.

## Justificaciones

El trabajador debe ingresar al menos una observación o un archivo. Se permiten archivos PDF, JPG/JPEG y PNG, validados por contenido y no solamente por extensión.

Los archivos:

- tienen un límite configurable mediante `JUSTIFICATION_MAX_MB`;
- reciben un nombre interno seguro;
- se almacenan fuera de los archivos públicos;
- no se guardan como binarios grandes en PostgreSQL;
- solo pueden descargarse mediante una ruta que comprueba al trabajador propietario.

Una justificación nueva queda en estado `PENDIENTE`. El modelo también contempla `APROBADA` y `RECHAZADA`, pero la interfaz completa de revisión por ADMIN/JEFATURA sigue pendiente.

## Pruebas

Desde la raíz, con el entorno virtual activo:

```powershell
$env:APP_ENV = "test"
$env:AUTH_ENFORCED = "false"
$env:DATABASE_URL = "sqlite+pysqlite:///:memory:"
python -m compileall -q app tests alembic
python -m unittest discover -s tests -v
```

La validación local posterior a Asistencia 4B-2B ejecutó **166 pruebas: 166 OK**. Incluye la regresión de 4B-2/4B-2A y casos de RADIO/COMUNA, borde/tolerancia/fuera, catálogo oficial por código, solapamientos, prioridad determinística, ausencia de asignación, persistencia sin incidencia automática y fallas seguras del dataset.

La URL SQLite del comando impide que la suite use accidentalmente PostgreSQL local. Las pruebas que necesitan persistencia crean su propio esquema/sesión desechable y restauran overrides. `APP_ENV=test` y `AUTH_ENFORCED=false` son exclusivos del proceso de test y no son una recomendación para ejecutar la aplicación real.

## Git y archivos locales

No deben versionarse:

- `.env`;
- `.venv/`;
- cachés de Python y archivos `*.pyc`;
- `output/`;
- `storage/` y documentos cargados por usuarios;
- archivos temporales;
- contraseñas, secretos, credenciales o API keys.

Antes de confirmar cambios:

```powershell
git pull
git status
git add <archivos-revisados>
git commit -m "Descripción breve del cambio"
git push
```

Revisa siempre `git status` para evitar incluir configuración o información privada.

## Checklist para otro desarrollador

1. Clonar el repositorio.
2. Crear y activar `.venv`.
3. Instalar `requirements.txt`.
4. Crear `.env` desde `.env.example`.
5. Crear o configurar su PostgreSQL.
6. Configurar `DATABASE_URL` y generar su propio `SESSION_SECRET`.
7. Ejecutar `python -m alembic upgrade head`.
8. Crear el primer ADMIN con `python -m app.scripts.create_admin`, si corresponde.
9. Ejecutar `python -m uvicorn app.main:app --reload`.
10. Abrir <http://127.0.0.1:8000/login>.

Con este flujo no es necesario conocer ninguna contraseña ni secreto de otro equipo.
