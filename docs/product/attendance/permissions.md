# Permisos de Asistencia

[IMPLEMENTADO] TRABAJADOR accede solo a su contexto; ADMIN administra lugares/asignaciones; JEFATURA posee permiso conceptual de supervisión sin UI completa.

[CONFIRMADO] TRABAJADOR verá solo su asistencia/calendario, marcará solo su propia asistencia y no modificará marcajes. JEFATURA y ADMIN podrán revisar trabajadores/asistencia y corregir según permisos; toda corrección deberá quedar auditada.

[IMPLEMENTADO 4B-1] El servicio recibe un Worker resuelto por backend y nunca un `worker_id` libre del cliente; una sesión solo puede cerrarse por su Worker propietario. [IMPLEMENTADO 4B-2] el POST personal exige autenticación, permiso `ASISTENCIA_PROPIA`, rol TRABAJADOR, Worker activo y CSRF; rechaza campos de ownership, sesión, zona y tiempo oficial. [CONFIRMADO MVP] ADMIN y JEFATURA tendrán revisión completa inicial. [PENDIENTE] endpoints de revisión/corrección, alcance posterior de JEFATURA y exposición concreta de coordenadas/documentos.

[IMPLEMENTADO 4B-2A] el calendario usa exclusivamente el `worker.id` resuelto en backend y no admite otro trabajador por query/formulario. El detalle personal omite coordenadas exactas. [PENDIENTE 4B-3] ADMIN/JEFATURA podrán seleccionar trabajadores sólo en rutas de supervisión con permisos explícitos.
