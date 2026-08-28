# Decisiones confirmadas para la siguiente fase de Asistencia

Este documento registra reglas acordadas, pero no implementadas en la Fase Asistencia 2.

- No existe planificación diaria previa; la ausencia de un marcaje no significa automáticamente ausencia laboral.
- No deben generarse estados `AUSENTE`, `SIN MARCA` o `TRABAJADOR ESPERADO` sin una fuente posterior de planificación.
- Los turnos iniciales serán `DIURNO` y `NOCTURNO`.
- El trabajador seleccionará el turno al registrar asistencia.
- Un trabajador podrá trabajar excepcionalmente ambos turnos el mismo día, previa coordinación con jefatura.
- `turno` y `tipo_marcaje` son conceptos distintos.
- Los tipos de marcaje futuros serán `ENTRADA` y `SALIDA`.
- Un mismo día podrá contener entrada y salida para turno diurno, y entrada y salida para turno nocturno.
- Esta fase no crea tablas ni rutas de turnos, GPS, lugares o marcajes.
