# Base de datos

## Current data model

Las migraciones `20260826_01` a `20260830_06` forman una cadena lineal. Tablas: `ordenes_trabajo`, `productos_ot`, `empresas`, `unidades_medida`, `productos`, `movimientos_inventario`, `detalle_movimientos_inventario`, `roles`, `usuarios`, `usuarios_roles`, `trabajadores`, `sesiones_usuario`, `lugares_trabajo`, `turnos`, `asignaciones_trabajador_lugar` y `justificaciones_inasistencia`.

Cardinalidades clave: empresa 1—N productos/trabajadores/movimientos; movimiento 1—N detalles; usuario N—M roles y 0..1 trabajador; trabajador 1—N asignaciones/justificaciones; lugar 1—N asignaciones. Hay FKs, uniques, checks e índices relevantes. Los estados son `String` con checks en varias tablas, no enums PostgreSQL.

Hallazgos: `updated_at` depende de `onupdate` ORM y no de trigger; los downgrades de la revisión de asistencia omiten drops explícitos de índices (PostgreSQL los elimina con las tablas); falta actor/auditoría en inventario; no existen lotes, bodegas ni ledger de reservas; el stock se calcula recorriendo movimientos en aplicación.

## Target data model

[PROPUESTO] conservar IDs enteros inicialmente, timestamps UTC, constraints en DB y movimientos auditables. Añadir solo mediante decisiones aprobadas: identidad del actor, bodegas/ubicaciones, lotes con vencimiento y costo, y eventos de asistencia con captura y evaluación geográfica separadas. No implementar soft delete universal: decidir por entidad.

## Gaps and next steps

Verificar paridad ORM–Alembic automáticamente en CI y probar migraciones en PostgreSQL desechable. Definir retención y eliminación de datos laborales/geográficos. Para inventario, decidir costo y política FEFO antes de modelar lotes.
