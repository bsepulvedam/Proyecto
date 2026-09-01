# Modelo de datos de Asistencia

[IMPLEMENTADO] `LugarTrabajo`, `AsignacionTrabajadorLugar`, `Turno`, `JustificacionInasistencia`, `SesionTrabajo`, `MarcajeAsistencia`, `EvidenciaGPSMarcaje`, `EvaluacionGeograficaMarcaje`, `IncidenciaAsistencia` y `CorreccionMarcaje`.

[IMPLEMENTADO 4B-1] Una sesión pertenece al Worker de RRHH, conserva turno y fecha operacional, admite `ENTRADA`/`SALIDA` únicas y puede cruzar medianoche. El evento usa hora UTC del servidor; `APP_TIMEZONE` deriva la fecha operacional.

[IMPLEMENTADO 4B-1] Evidencia capturada y evaluación derivada están separadas; la evaluación conserva zona, distancia, radio, umbral y versión. Incidencias y correcciones no sobrescriben evidencia. [PENDIENTE] workflow administrativo y política de retención. `VALOR_DIA`/`TOTAL_PAGO` no forman parte de Asistencia.

[IMPLEMENTADO 4B-2A] El calendario es una proyección de lectura sobre las entidades existentes y no añade tablas: agrupa por `SesionTrabajo.fecha_operacional`, valida el par `ENTRADA`/`SALIDA`, conserva cantidad/detalle de sesiones y aplica incidencias como clasificación. No persiste ni infiere jornadas pagables.
