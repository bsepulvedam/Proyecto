# Backend

## Current state

FastAPI compone routers HTML y JSON. SQLAlchemy 2 y sesiones síncronas acceden a PostgreSQL. Services encapsulan autenticación, administración, asistencia, catálogo, importación, movimientos, stock y OT. [IMPLEMENTADO 4B-2A] la proyección mensual de Asistencia vive en `attendance_calendar_service.py` y consulta únicamente el Worker autenticado. Varias rutas aún parsean formularios y construyen respuestas directamente.

## Gaps

Separación por capas parcial; módulos de dominio no son paquetes autónomos. Hay commits dentro de servicios, errores heterogéneos y consultas/listados que cargarán datasets completos. Configuración se lee mediante funciones y variables de módulo.

## Target and next steps

Conservar sync y monolito. Introducir límites por dominio, unidades de trabajo por caso de uso, excepciones tipadas y configuración validada. Medir antes de cambiar a async o añadir caché.

[IMPLEMENTADO EN ÁRBOL 4B-3D] La administración web de tarifas usa el servicio append-only existente y autorización ADMIN. Las descargas XLSX conjunta e individual consumen `attendance_supervision_service` y el motor común; el listado conjunto carga sesiones y tarifas por lotes para evitar N+1.
