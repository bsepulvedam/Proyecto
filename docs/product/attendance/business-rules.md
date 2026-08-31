# Reglas de Asistencia

- [IMPLEMENTADO] lugar tipo BASE/TALLER/TERRENO, coordenadas/radio opcionales y asignaciones con vigencia válida.
- [IMPLEMENTADO] justificación requiere observación o archivo; tipos y estados están restringidos.
- [CONFIRMADO] un trabajador puede tener múltiples sesiones en un mismo día operacional. Cada sesión tiene conceptualmente una `ENTRADA` y una `SALIDA`; tras cerrarla puede iniciar otra, permitiendo doble turno.
- [CONFIRMADO] `DIURNO`/`NOCTURNO` identifica la jornada elegida por el trabajador y no constituye planificación rígida. Un turno nocturno puede cruzar medianoche.
- [IMPLEMENTADO 4B-1] no se permite entrada duplicada, salida sin sesión, salida duplicada ni salida antes de 5 minutos. `ATTENDANCE_MIN_SESSION_MINUTES` centraliza el valor.
- [CONFIRMADO] la hora del servidor es autoritativa y `APP_TIMEZONE` determina la fecha/día operacional; no se debe usar `date.today()` del servidor para esa decisión.
- [IMPLEMENTADO 4B-1] el servicio exige GPS válido, selecciona automáticamente la zona activa configurada más cercana mediante Haversine y conserva distancia/radio. Fuera de rango se registra y genera incidencia.
- [IMPLEMENTADO 4B-1] precisión mayor a 100 m genera `GPS_BAJA_PRECISION` sin rechazar el marcaje; `ATTENDANCE_MAX_GPS_ACCURACY_METERS` centraliza el umbral.
- [CONFIRMADO] no existe tracking continuo: GPS se solicita únicamente al marcar.
- [CONFIRMADO] una falta de marcaje queda `PENDIENTE_DE_REVISION` antes de una ausencia definitiva. Sin una fuente válida de planificación no se infiere ausencia.
- [CONFIRMADO] la tolerancia de atraso es inicialmente 10 minutos y será configurable globalmente; solo se calcula cuando exista una hora esperada válida.
- [CONFIRMADO] colores futuros: verde correcto, rojo ausencia confirmada, amarillo atraso/incidencia, naranja fuera de rango, gris no laboral y neutral futuro/sin estado.
- [CONFIRMADO] una exportación mensual futura contemplará Excel y PDF. No se calculan remuneraciones; la futura integración podrá consumir `VALOR_DIA`/`TOTAL_PAGO` sin convertir Asistencia en dueña de remuneraciones.
- [IMPLEMENTADO 4B-1] eventos y evidencia original no se sobrescriben; existe estructura para correcciones auditadas y evaluación reproducible/versionada.
- [PENDIENTE] endpoint/UI, fuente de horario esperado, offline/fraude, workflow de corrección/aprobación y retención GPS.
