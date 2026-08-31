# Flujos de Asistencia

Actual: trabajador consulta calendario → crea justificación → consulta/descarga su archivo. ADMIN administra lugares y asignaciones.

[CONFIRMADO] Flujo conceptual de sesión: resolver trabajador y jornada elegida → abrir sesión con `ENTRADA` y GPS → impedir entrada duplicada → cerrar con `SALIDA` y GPS después del intervalo mínimo configurable → impedir salida duplicada → permitir una nueva sesión. Un turno nocturno puede cerrar en el día calendario siguiente; `APP_TIMEZONE` determina el día operacional.

[CONFIRMADO] Flujo geográfico conceptual: capturar solo al marcar → evaluar radio de zona en backend → persistir captura y resultado → si está fuera de rango, conservar evento y abrir incidencia/revisión. Fallos GPS o falta de marcaje no se convierten automáticamente en ausencia.

[PROPUESTO] Flujo administrativo: JEFATURA/ADMIN revisa incidencia según alcance → corrige mediante acción auditada. [PENDIENTE] fuente de hora esperada, revisión final, exportación mensual Excel/PDF y detalle de errores/offline.
