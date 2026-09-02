# Modelo de datos de Asistencia

[IMPLEMENTADO] `LugarTrabajo`, `AsignacionTrabajadorLugar`, `Turno`, `JustificacionInasistencia`, `SesionTrabajo`, `MarcajeAsistencia`, `EvidenciaGPSMarcaje`, `EvaluacionGeograficaMarcaje`, `IncidenciaAsistencia` y `CorreccionMarcaje`.

[IMPLEMENTADO 4B-1] Una sesión pertenece al Worker de RRHH, conserva turno y fecha operacional, admite `ENTRADA`/`SALIDA` únicas y puede cruzar medianoche. El evento usa hora UTC del servidor; `APP_TIMEZONE` deriva la fecha operacional.

[IMPLEMENTADO 4B-1] Evidencia capturada y evaluación derivada están separadas; la evaluación conserva zona, distancia, radio, umbral y versión. Incidencias y correcciones no sobrescriben evidencia. [PENDIENTE] workflow administrativo y política de retención. `VALOR_DIA`/`TOTAL_PAGO` no forman parte de Asistencia.

[IMPLEMENTADO 4B-2A] El calendario es una proyección de lectura sobre las entidades existentes y no añade tablas: agrupa por `SesionTrabajo.fecha_operacional`, valida el par `ENTRADA`/`SALIDA`, conserva cantidad/detalle de sesiones y aplica incidencias como clasificación. No persiste ni infiere jornadas pagables.

[IMPLEMENTADO EN ÁRBOL 4B-2B] `LugarTrabajo` incorpora `tipo_geocerca`, `codigo_comuna` y `prioridad_geocerca`. Una zona `RADIO` exige centro y radio; una `COMUNA` exige `CUT_COM`, coordenadas de referencia y radio nulo. Solo puede existir una zona comunal activa por código.

[IMPLEMENTADO EN ÁRBOL 4B-2B] `EvaluacionGeograficaMarcaje` conserva el snapshot del tipo aplicado, distancia, radio o tolerancia, estado y `geometria_version`. La evaluación histórica no depende de que el lugar sea editado o desactivado después.
