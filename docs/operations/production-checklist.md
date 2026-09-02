# Checklist operacional de producción

- Artefacto/version y owner identificados; variables validadas sin secretos en Git.
- Backup reciente y restore ensayado según [Backup y restore de PostgreSQL](database-backup-restore.md); registrar hash, revisión, conteos y responsable antes de migrar.
- `APP_ENV=production`, HTTPS, cookie Secure, auth obligatoria, proxy confiable y límites de upload/request.
- Readiness DB/storage; logs y alertas disponibles; dashboards sin PII.
- Smoke tests de login, permisos, trabajador, asistencia e inventario.
- Rollback de aplicación y estrategia de esquema compatibles.
- Soporte, escalamiento, RPO/RTO y ventana comunicados.

[CONFIRMADO LOCALMENTE 2026-09-02] El backup previo a 4B-2B y su restore desechable tienen evidencia aprobada. [PENDIENTE] Esto no reemplaza backups automáticos, copia externa, monitoreo, retención ni RPO/RTO de producción.
