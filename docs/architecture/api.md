# API y rutas web

## Inventario actual

| Método y ruta | Área | Entrada/salida | Acceso |
|---|---|---|---|
| GET `/`, `/health` | sistema | JSON | público |
| GET `/api/productos/buscar` | inventario | query; JSON | `INVENTARIO_ACCESS` |
| POST `/api/ordenes` | OT | JSON; JSON | `OT_ACCESS` |
| GET `/login`; POST `/login`, `/logout`, `/cambiar-password` | identidad | formularios/HTML | flujo propio + CSRF |
| GET `/dashboard` | general | HTML | plataforma |
| GET/POST `/admin/trabajadores`, `/admin/usuarios`, `/admin/lugares`, `/admin/asignaciones` | administración | formularios/HTML | `ADMIN_ACCESS` |
| GET/POST `/mi-asistencia/...` | asistencia | formularios/HTML/archivo | trabajador activo |
| GET/POST `/productos...`, `/inventario...` | inventario | HTML | `INVENTARIO_ACCESS` |
| GET/POST `/ordenes-trabajo...` | OT | HTML | `OT_ACCESS` |

La lista detallada de rutas se obtiene de `app/main.py`, `app/api/*.py` y `app/web/*.py`; las rutas web devuelven errores mediante páginas o excepciones, mientras la API usa detalles JSON de FastAPI.

## Gaps

[DEUDA_TECNICA] No hay versionado `/api/v1`, contratos de error uniformes ni documentación explícita por endpoint. Búsquedas y listados carecen de paginación. `/health` no prueba dependencias. Parte de la validación de formularios se hace manualmente. Las rutas públicas raíz/salud deben revisarse contra el modelo de exposición.

## Target and next steps

[PROPUESTO] mantener rutas existentes y aplicar versionado solo a nuevas APIs públicas internas; definir envelope de error, paginación, schemas de salida, permisos nombrados y tests negativos. Documentar deprecaciones antes de cambiar contratos.
