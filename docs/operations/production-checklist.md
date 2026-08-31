# Checklist operacional de producción

- Artefacto/version y owner identificados; variables validadas sin secretos en Git.
- Backup reciente y restore ensayado; migración revisada y ejecución única.
- `APP_ENV=production`, HTTPS, cookie Secure, auth obligatoria, proxy confiable y límites de upload/request.
- Readiness DB/storage; logs y alertas disponibles; dashboards sin PII.
- Smoke tests de login, permisos, trabajador, asistencia e inventario.
- Rollback de aplicación y estrategia de esquema compatibles.
- Soporte, escalamiento, RPO/RTO y ventana comunicados.
