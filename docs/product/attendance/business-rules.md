# Reglas de Asistencia

- [IMPLEMENTADO] lugar tipo BASE/TALLER/TERRENO, coordenadas/radio opcionales y asignaciones con vigencia válida.
- [IMPLEMENTADO] justificación requiere observación o archivo; tipos y estados están restringidos.
- [CONFIRMADO] un trabajador puede tener múltiples sesiones en un mismo día operacional. Cada sesión tiene conceptualmente una `ENTRADA` y una `SALIDA`; tras cerrarla puede iniciar otra, permitiendo doble turno.
- [CONFIRMADO] `DIURNO`/`NOCTURNO` identifica la jornada elegida por el trabajador y no constituye planificación rígida. Un turno nocturno puede cruzar medianoche.
- [CONFIRMADO] no se permite una entrada duplicada en una sesión abierta ni una salida duplicada. Una salida inmediatamente posterior a la entrada se rechaza; el intervalo mínimo será configurable y su valor exacto está [PENDIENTE].
- [CONFIRMADO] la hora del servidor es autoritativa y `APP_TIMEZONE` determina la fecha/día operacional; no se debe usar `date.today()` del servidor para esa decisión.
- [CONFIRMADO] entrada y salida usarán geolocalización. El radio es configurable por zona y el backend calcula dentro/fuera de rango. Un evento fuera de rango se conserva y genera incidencia/revisión.
- [CONFIRMADO] no existe tracking continuo: GPS se solicita únicamente al marcar.
- [CONFIRMADO] una falta de marcaje queda `PENDIENTE_DE_REVISION` antes de una ausencia definitiva. Sin una fuente válida de planificación no se infiere ausencia.
- [CONFIRMADO] la tolerancia de atraso es inicialmente 10 minutos y será configurable globalmente; solo se calcula cuando exista una hora esperada válida.
- [CONFIRMADO] colores futuros: verde correcto, rojo ausencia confirmada, amarillo atraso/incidencia, naranja fuera de rango, gris no laboral y neutral futuro/sin estado.
- [CONFIRMADO] una exportación mensual futura contemplará Excel y PDF. No se calculan remuneraciones; la futura integración podrá consumir `VALOR_DIA`/`TOTAL_PAGO` sin convertir Asistencia en dueña de remuneraciones.
- [PROPUESTO] eventos inmutables, correcciones auditadas y evaluación geográfica reproducible.
- [PENDIENTE] valor del intervalo mínimo entrada/salida, fuente de horario esperado, offline/fraude, flujo de aprobación y retención GPS.
