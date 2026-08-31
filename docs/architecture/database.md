# Base de datos

## Current data model

Las migraciones `20260826_01` a `20260831_07` forman una cadena lineal de siete revisiones y 22 tablas. Asistencia 4B-1 añade `sesiones_trabajo`, `marcajes_asistencia`, `evidencias_gps_marcaje`, `evaluaciones_geograficas_marcaje`, `incidencias_asistencia` y `correcciones_marcaje` sobre las 16 tablas previas.

Cardinalidades clave: empresa 1—N productos/trabajadores/movimientos; movimiento 1—N detalles; usuario N—M roles y 0..1 trabajador; trabajador 1—N asignaciones/justificaciones; lugar 1—N asignaciones. Hay FKs, uniques, checks e índices relevantes. Los estados son `String` con checks en varias tablas, no enums PostgreSQL.

Hallazgos: `updated_at` depende de `onupdate` ORM y no de trigger; los downgrades de la revisión de asistencia omiten drops explícitos de índices (PostgreSQL los elimina con las tablas); falta actor/auditoría en inventario; no existen lotes, bodegas ni ledger de reservas; el stock se calcula recorriendo movimientos en aplicación.

## Target data model

[IMPLEMENTADO] Asistencia conserva timestamps UTC, Worker como propietario, evidencia GPS separada de la evaluación derivada y un índice parcial PostgreSQL que limita a una sesión abierta por trabajador. [PROPUESTO] conservar IDs enteros, constraints en DB y registros auditables; no implementar soft delete universal sin decisión por entidad.

## Gaps and next steps

[CONFIRMADO GATE 4B-1 2026-08-31] La cadena completa, el rollback a `20260830_06`, el re-upgrade, constraints, índice parcial y concurrencia fueron probados en PostgreSQL desechable. [CONFIRMADO 2026-08-31] La paridad global ORM–Alembic quedó limpia al declarar en metadata los nombres históricos `ix_detalle_movimientos_movimiento_id` e `ix_detalle_movimientos_producto_id`; no se modificó `20260827_03` ni fue necesaria otra migración. Definir además retención y eliminación de datos laborales/geográficos. Para inventario, decidir costo y política FEFO antes de modelar lotes.
