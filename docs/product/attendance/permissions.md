# Permisos de Asistencia

[IMPLEMENTADO EN ÁRBOL 4B-2B] TRABAJADOR accede solo a su contexto; ADMIN administra lugares y geocercas por código comunal oficial; JEFATURA posee permiso conceptual de supervisión sin UI completa. Ni el trabajador ni su asignación histórica seleccionan la zona evaluada.

[CONFIRMADO] TRABAJADOR verá solo su asistencia/calendario, marcará solo su propia asistencia y no modificará marcajes. JEFATURA y ADMIN podrán revisar trabajadores/asistencia y corregir según permisos; toda corrección deberá quedar auditada.

[IMPLEMENTADO 4B-1] El servicio recibe un Worker resuelto por backend y nunca un `worker_id` libre del cliente; una sesión solo puede cerrarse por su Worker propietario. [IMPLEMENTADO 4B-2] el POST personal exige autenticación, permiso `ASISTENCIA_PROPIA`, rol TRABAJADOR, Worker activo y CSRF; rechaza campos de ownership, sesión, zona y tiempo oficial. [CONFIRMADO MVP] ADMIN y JEFATURA tendrán revisión completa inicial. [PENDIENTE] endpoints de revisión/corrección, alcance posterior de JEFATURA y exposición concreta de coordenadas/documentos.

[IMPLEMENTADO 4B-2A] el calendario usa exclusivamente el `worker.id` resuelto en backend y no admite otro trabajador por query/formulario. El detalle personal omite coordenadas exactas. [PENDIENTE 4B-3] ADMIN/JEFATURA podrán seleccionar trabajadores sólo en rutas de supervisión con permisos explícitos.

[IMPLEMENTADO EN ÁRBOL 4B-3C] ADMIN y JEFATURA supervisan, resuelven incidencias y completan SALIDAS mediante `ASISTENCIA_SUPERVISAR`; todas las mutaciones conservan CSRF y auditoría. TRABAJADOR y anónimo permanecen denegados. Solo ADMIN podrá modificar tarifas en una subfase posterior, sin ampliar `ADMIN_ACCESS`; JEFATURA solo consulta la tarifa efectiva proyectada.
