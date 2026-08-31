# Modelo de datos de Asistencia

[IMPLEMENTADO] `LugarTrabajo`, `AsignacionTrabajadorLugar`, `Turno`, `JustificacionInasistencia`; [PENDIENTE] no hay sesión de trabajo, relación de turno seleccionada ni tabla de marcaje.

[CONFIRMADO] El objetivo conceptual separa sesión de trabajo, eventos `ENTRADA`/`SALIDA`, captura GPS, evaluación de rango, incidencia y corrección auditada. Una sesión pertenece al trabajador de RRHH, conserva la jornada elegida y puede cruzar medianoche; el día operacional se deriva con `APP_TIMEZONE` y hora autoritativa del servidor.

[PROPUESTO] Persistir evidencia capturada y evaluación derivada por separado, con versión de regla/radio suficiente para auditoría. Evitar snapshots personales salvo mínimos necesarios. Una futura exportación podrá entregar datos a remuneraciones, pero `VALOR_DIA`/`TOTAL_PAGO` no forman parte del modelo 4B confirmado ni se calculan en Asistencia.
