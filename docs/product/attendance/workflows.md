# Flujos de Asistencia

Actual: trabajador consulta calendario → crea justificación → consulta/descarga su archivo. ADMIN administra lugares y asignaciones.

[IMPLEMENTADO 4B-1 backend] resolver Worker y turno → validar GPS → abrir con `ENTRADA` → impedir duplicado → cerrar con `SALIDA` después de 5 minutos → impedir salida duplicada → permitir otra sesión. Un turno nocturno cruza medianoche sin cierre automático; `APP_TIMEZONE` fija el día operacional.

[IMPLEMENTADO 4B-1 backend] validar evidencia → evaluar todas las zonas activas configuradas → elegir la más cercana → persistir evidencia y evaluación → abrir incidencia por fuera de rango o baja precisión. [PENDIENTE 4B-2] captura GPS y envío desde navegador. Fallos GPS o falta de marcaje no se convierten automáticamente en ausencia.

[PROPUESTO] Flujo administrativo: JEFATURA/ADMIN revisa incidencia según alcance → corrige mediante acción auditada. [PENDIENTE] fuente de hora esperada, revisión final, exportación mensual Excel/PDF y detalle de errores/offline.
