# Asistencia

[IMPLEMENTADO] lugares, asignaciones históricas, turnos catálogo, justificaciones y archivos privados. [IMPLEMENTADO 4B-1] modelo y servicio transaccional de sesiones/marcajes, evidencia GPS, evaluación de radio e incidencias. [IMPLEMENTADO 4B-2] ruta web protegida, estado de sesión y captura GPS puntual para ENTRADA/SALIDA. [IMPLEMENTADO 4B-2A] calendario personal derivado de sesiones reales, con detalle mínimo por fecha y estados trabajado/revisión/fuera de rango/neutral. Asistencia referencia al Worker de RRHH. [PENDIENTE] revisión/corrección administrativa, ausencia confirmada, planificación, alertas, exportación, jornadas pagables y supervisión UI 4B-3.

[CONFIRMADO] Un día puede contener múltiples sesiones, cada una con `ENTRADA`/`SALIDA`. `DIURNO`/`NOCTURNO` es la jornada elegida y puede cruzar medianoche; no es tipo de marcaje ni planificación rígida. Un día sin registros no implica ausencia y pasa por revisión antes de cualquier ausencia confirmada.

[IMPLEMENTADO 4B-1] La persistencia separa evidencia capturada y evaluación derivada, usa hora del servidor y protege una sesión abierta por trabajador mediante bloqueo e índice parcial PostgreSQL. [IMPLEMENTADO 4B-2] `/mi-asistencia/registrar` deriva el Worker desde la sesión autenticada, conserva CSRF/RBAC y usa `navigator.geolocation.getCurrentPosition` solo al enviar cada marcaje, sin seguimiento continuo.

[IMPLEMENTADO 4B-2A] Una fecha trabajada exige al menos una sesión `CERRADA` con `ENTRADA` y `SALIDA` coherentes. Varias sesiones en la misma fecha siguen siendo una fecha trabajada, aunque el detalle conserva su cantidad. Días trabajados, sesiones y futuras jornadas pagables permanecen separados; no se calcula remuneración.
