# Asistencia

[IMPLEMENTADO] lugares, asignaciones históricas, turnos catálogo, calendario personal neutro, justificaciones y archivos privados. [CONFIRMADO] Asistencia depende de RRHH y referencia trabajador. [PENDIENTE] sesiones/marcajes, GPS, evaluación de radio, atraso, ausencia, incidencias, planificación, alertas, exportación y supervisión completa.

[CONFIRMADO] Un día puede contener múltiples sesiones, cada una con `ENTRADA`/`SALIDA`. `DIURNO`/`NOCTURNO` es la jornada elegida y puede cruzar medianoche; no es tipo de marcaje ni planificación rígida. Un día sin registros no implica ausencia y pasa por revisión antes de cualquier ausencia confirmada.

[PENDIENTE] Asistencia 4B implementará únicamente después de diseñar persistencia, atomicidad, auditoría, permisos y privacidad a partir de estas reglas. Asistencia 4A no añadió tablas, rutas ni comportamiento de marcaje.
