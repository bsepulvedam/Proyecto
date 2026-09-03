# Modelo de datos de Asistencia

[IMPLEMENTADO] `LugarTrabajo`, `AsignacionTrabajadorLugar`, `Turno`, `JustificacionInasistencia`, `SesionTrabajo`, `MarcajeAsistencia`, `EvidenciaGPSMarcaje`, `EvaluacionGeograficaMarcaje`, `IncidenciaAsistencia` y `CorreccionMarcaje`.

[IMPLEMENTADO 4B-1] Una sesión pertenece al Worker de RRHH, conserva turno y fecha operacional, admite `ENTRADA`/`SALIDA` únicas y puede cruzar medianoche. El evento usa hora UTC del servidor; `APP_TIMEZONE` deriva la fecha operacional.

[IMPLEMENTADO 4B-1] Evidencia capturada y evaluación derivada están separadas; la evaluación conserva zona, distancia, radio, umbral y versión. Incidencias y correcciones no sobrescriben evidencia. [PENDIENTE] workflow administrativo y política de retención. `VALOR_DIA`/`TOTAL_PAGO` no forman parte de Asistencia.

[IMPLEMENTADO 4B-2A] El calendario es una proyección de lectura sobre las entidades existentes y no añade tablas: agrupa por `SesionTrabajo.fecha_operacional`, valida el par `ENTRADA`/`SALIDA`, conserva cantidad/detalle de sesiones y aplica incidencias como clasificación. No persiste ni infiere jornadas pagables.

[IMPLEMENTADO EN ÁRBOL 4B-2B] `LugarTrabajo` incorpora `tipo_geocerca`, `codigo_comuna` y `prioridad_geocerca`. Una zona `RADIO` exige centro y radio; una `COMUNA` exige `CUT_COM`, coordenadas de referencia y radio nulo. Solo puede existir una zona comunal activa por código.

[IMPLEMENTADO EN ÁRBOL 4B-2B] `EvaluacionGeograficaMarcaje` conserva el snapshot del tipo aplicado, distancia, radio o tolerancia, estado y `geometria_version`. La evaluación histórica no depende de que el lugar sea editado o desactivado después.

[IMPLEMENTADO EN ÁRBOL 4B-3A] La proyección común de dominio no añade tablas. `AttendanceSessionFacts` transporta hechos existentes y `AttendanceSessionProjection`, `AttendanceDayProjection` y `AttendancePeriodProjection` derivan actividad, incompleto, situaciones horarias, pagabilidad, doble turno y totales sin modificar ORM ni evidencia.

[IMPLEMENTADO EN ÁRBOL 4B-3A] `ProvisionalRateVersion` y `EffectiveProvisionalRate` expresan vigencia, precedencia individual/global y monto CLP como conceptos inmutables. No se persisten agregados ni totales.

[IMPLEMENTADO Y TESTEADO EN ÁRBOL 4B-3B] `IntervencionSalidaAdministrativa` enlaza una sesión y su SALIDA administrativa, exige tipo `COMPLETAR_SALIDA`, expresa la ausencia original mediante `salida_original_ausente=true` y conserva hora laboral introducida, actor, motivo y timestamp. Una FK compuesta garantiza que el marcaje enlazado pertenece a la misma sesión y es de tipo `SALIDA`; las unicidades limitan una intervención por sesión y por marcaje.

[IMPLEMENTADO Y TESTEADO EN ÁRBOL 4B-3B] `TarifaProvisionalAsistencia` guarda monto CLP exacto positivo, `vigente_desde` como `date` operacional, alcance global (`trabajador_id=NULL`) o individual, origen, actor y timestamp. Índices parciales únicos eliminan ambigüedad por alcance/fecha. La versión inicial de sistema es $30.000 desde `2026-09-01`, primera fecha operacional verificada antes de crear la migración.

[IMPLEMENTADO EN MIGRACIÓN CANDIDATA 4B-3B] `20260902_09` cambia incidencias a `PENDIENTE/APROBADA/RECHAZADA`, con precheck y mapeo `RESUELTA→APROBADA`, `DESCARTADA→RECHAZADA`. Exige actor/timestamp en estados finales y ausencia de ambos en pendientes. No está aplicada a `boliklor_ot` real.
