# Modelo de datos de Asistencia

[IMPLEMENTADO] `LugarTrabajo`, `AsignacionTrabajadorLugar`, `Turno`, `JustificacionInasistencia`; [PENDIENTE] no hay relación de turno con trabajador ni tabla de marcaje.

Objetivo conceptual: planificación/jornada, evento de asistencia inmutable, captura de ubicación, evaluación geográfica, incidencia y decisión administrativa, todos referenciando trabajador. Evitar guardar snapshots personales salvo mínimos necesarios para auditoría.
