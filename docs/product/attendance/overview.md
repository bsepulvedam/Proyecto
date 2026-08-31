# Asistencia

[IMPLEMENTADO] lugares, asignaciones históricas, turnos catálogo, calendario personal neutro, justificaciones y archivos privados. [IMPLEMENTADO 4B-1] modelo y servicio transaccional de sesiones/marcajes, evidencia GPS, evaluación de radio e incidencias. Asistencia referencia al Worker de RRHH. [PENDIENTE] captura GPS web, rutas de marcaje, revisión/corrección administrativa, atraso, ausencia, planificación, alertas, exportación y supervisión UI.

[CONFIRMADO] Un día puede contener múltiples sesiones, cada una con `ENTRADA`/`SALIDA`. `DIURNO`/`NOCTURNO` es la jornada elegida y puede cruzar medianoche; no es tipo de marcaje ni planificación rígida. Un día sin registros no implica ausencia y pasa por revisión antes de cualquier ausencia confirmada.

[IMPLEMENTADO 4B-1] La persistencia separa evidencia capturada y evaluación derivada, usa hora del servidor y protege una sesión abierta por trabajador mediante bloqueo e índice parcial PostgreSQL. [PENDIENTE 4B-2] No existe endpoint ni captura `navigator.geolocation`; la pantalla actual continúa sin crear marcajes.
