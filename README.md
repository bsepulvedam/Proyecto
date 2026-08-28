# Sistema web Boliklor

Sistema web de Boliklor para la gestión de inventario y órdenes de trabajo.

## Tecnologías

- **Backend:** Python 3 + FastAPI
- **Base de datos:** PostgreSQL
- **ORM y migraciones:** SQLAlchemy + Alembic
- **Frontend:** HTML, CSS y JavaScript
- **Plantillas web:** Jinja2

## Estructura principal

```text
.
├── alembic/              # Configuración y versiones de migraciones
├── app/
│   ├── api/              # Endpoints de la API
│   ├── database/         # Conexión y configuración de SQLAlchemy
│   ├── models/           # Modelos ORM
│   ├── schemas/          # Esquemas de validación
│   ├── services/         # Reglas de negocio
│   ├── static/           # CSS y JavaScript de las vistas integradas
│   ├── templates/        # Plantillas HTML Jinja2
│   ├── web/              # Rutas de la interfaz web
│   └── main.py           # Punto de entrada de FastAPI
├── frontend/             # Prototipo/frontend estático para Live Server
├── tests/                # Pruebas automatizadas
├── .env.example          # Referencia de variables de entorno
├── alembic.ini           # Configuración de Alembic
└── requirements.txt      # Dependencias de Python
```

## Requisitos previos

Instala estas herramientas en el equipo Windows:

- [Git](https://git-scm.com/download/win)
- [Python 3](https://www.python.org/downloads/windows/)
- [PostgreSQL](https://www.postgresql.org/download/windows/)
- Visual Studio Code (recomendado)
- Extensión **Live Server** para Visual Studio Code, si utilizarás el frontend estático

Comprueba las instalaciones desde PowerShell:

```powershell
git --version
python --version
psql --version
```

## Clonar el repositorio

```powershell
git clone https://github.com/bsepulvedam/Proyecto.git
cd Proyecto
```

## Crear el entorno virtual

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, habilítala solamente para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Instalar dependencias

Con el entorno virtual activo:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Crear la base de datos PostgreSQL

Puedes crear la base mediante pgAdmin o desde PowerShell con `psql`:

```powershell
psql -U postgres -c "CREATE DATABASE boliklor_ot;"
```

PostgreSQL solicitará la contraseña del usuario local `postgres`.

## Configurar variables de entorno

Copia el archivo de referencia:

```powershell
Copy-Item .env.example .env
```

Abre `.env` localmente y configura la conexión a `boliklor_ot`. Cada desarrollador debe colocar su propio usuario y su propia contraseña de PostgreSQL.

El archivo `.env.example` contiene solamente la estructura de referencia. Nunca agregues a Git contraseñas, credenciales, tokens ni API keys reales. Tampoco compartas el contenido de tu archivo `.env`.

## Ejecutar migraciones

Con PostgreSQL activo, la base creada y `.env` configurado:

```powershell
alembic upgrade head
```

Este comando crea o actualiza las tablas hasta la última versión disponible.

## Levantar el backend

```powershell
uvicorn app.main:app --reload
```

La aplicación estará disponible en:

- Web/API: <http://127.0.0.1:8000>
- Swagger: <http://127.0.0.1:8000/docs>

Detén el servidor con `Ctrl+C`.

## Frontend

La interfaz integrada con FastAPI se encuentra en:

- `app/templates/`: vistas HTML Jinja2
- `app/static/css/`: estilos
- `app/static/js/`: comportamiento JavaScript

Estas vistas se sirven automáticamente al ejecutar FastAPI; no requieren Live Server.

El frontend estático independiente se encuentra en `frontend/`. Para verlo con Live Server:

1. Abre la carpeta del repositorio en Visual Studio Code.
2. Abre `frontend/login.html` o `frontend/dashboard.html`.
3. Haz clic derecho sobre el archivo.
4. Selecciona **Open with Live Server**.

Live Server sirve únicamente los archivos estáticos. Para utilizar endpoints o datos reales, también debes mantener el backend FastAPI y PostgreSQL en ejecución.

## Flujo básico de trabajo con Git

Antes de comenzar una tarea:

```powershell
git pull
git status
```

Después de realizar y comprobar tus cambios:

```powershell
git status
git add README.md
git commit -m "Documentar instalación y ejecución en Windows"
git push
```

Sustituye `README.md` por los archivos correspondientes cuando trabajes en otras funcionalidades. Revisa siempre `git status` antes de confirmar para evitar incluir `.env`, credenciales o archivos locales.
