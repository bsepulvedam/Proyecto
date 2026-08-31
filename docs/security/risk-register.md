# Registro inicial de riesgos de seguridad

| ID | Riesgo | Nivel | Tratamiento |
|---|---|---|---|
| SEC-001 | [RESUELTO 4A] bypass de auth limitado a development/test; default activo y validación de arranque | CRÍTICO original | conservar tests y exigir configuración/secretos productivos |
| SEC-002 | Sin rate limiting de login | ALTO | límite en proxy/app, alertas y pruebas |
| SEC-003 | Sin plataforma documentada de secretos/TLS | ALTO | proveedor de secretos, HTTPS y rotación |
| SEC-004 | GPS/documentos sin política de retención | ALTO | minimizar, RBAC y decisión legal/empresarial |
| SEC-005 | Sin auditoría privilegiada central | ALTO | eventos de auditoría con integridad/retención |
| SEC-006 | Cabeceras y confianza de proxy no definidas | MEDIO | baseline de cabeceras y proxy explícito |

No se explotaron vulnerabilidades. La aceptación de un riesgo requiere owner, plazo y evidencia; asuntos legales permanecen `[PENDIENTE]`.
