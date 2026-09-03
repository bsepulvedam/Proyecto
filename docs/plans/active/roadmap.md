# Roadmap recomendado

1. Fase 0: cerrar auditoría, contratos, baseline reproducible y decisiones de negocio urgentes.
2. Fundaciones de release: fail-closed, CI, PostgreSQL/migraciones, staging, logging, backup/restore.
3. Identidad + RRHH base: ownership, matriz RBAC y ciclo mínimo sin ampliar ficha innecesariamente.
4. Asistencia MVP: planificación mínima, eventos, GPS/geocerca, incidencias, revisión y privacidad.
5. Inventario MVP: salidas/ajustes, concurrencia, auditoría; lotes/vencimiento solo tras confirmar necesidad.
6. Producción inicial: piloto limitado, observación, rollback y soporte; luego expansión gradual.
7. Mejoras RRHH/operacionales. Futuro: OT, compras, BI u otros módulos solo mediante discovery y ADR.

Staging y operación se construyen en paralelo a las fases 3–5, no como tarea final aislada.

## Continuidad acordada de Asistencia

- [IMPLEMENTADO 4B-2A] Calendario personal derivado de sesiones/marcajes, parámetros horarios base y separación entre fecha trabajada, sesión y futura jornada pagable.
- [EN PROGRESO 4B-3] [IMPLEMENTADO EN ÁRBOL 4B-3A] El dominio proyecta actividad, incompletos, situaciones horarias, jornadas pagables, doble turno, tarifa efectiva versionada y total provisional. [IMPLEMENTADO Y VALIDADO EN POSTGRESQL DESECHABLE 4B-3B] Persistencia auditable de SALIDA administrativa, estados/decisión de incidencias y tarifas globales/individuales versionadas. [PENDIENTE 4B-3C+] listado/búsqueda, filtros, vista individual, rutas/UI administrativas y exportación Excel individual/conjunta.
