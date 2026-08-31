# Observabilidad

[IMPLEMENTADO] logging estándar puntual en inventario. `/health` responde sin consultar DB. [PROPUESTO] logs JSON con timestamp UTC, nivel, request/correlation ID, ruta, duración, resultado y actor pseudonimizado; readiness con DB; captura central de excepciones; métricas de latencia, errores, sesiones, marcajes y fallos de inventario.

Nunca registrar secretos, passwords, tokens, cookies, contenido de documentos, coordenadas exactas ni PII innecesaria. Auditoría de negocio y logs técnicos son flujos distintos, con retención aprobada. Crear runbooks para login, DB, migraciones, storage y stock inconsistente.
