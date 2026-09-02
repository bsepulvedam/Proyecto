# Infraestructura

## Current state

[IMPLEMENTADO] Uvicorn/FastAPI, PostgreSQL configurable y storage privado local para justificantes. [IMPLEMENTADO] Existe un [procedimiento manual de backup/restore PostgreSQL](../operations/database-backup-restore.md) con un backup local pre-migración y restore desechable validados el 2026-09-02. [PENDIENTE] No hay Docker, proxy, TLS, CI/CD, staging, backups automáticos/copia externa, monitoreo, retención/RPO/RTO, métricas ni configuración de hosting en el repositorio.

## Target state

[PROPUESTO] despliegue de una aplicación detrás de reverse proxy con HTTPS, PostgreSQL administrado o respaldado, volumen privado persistente, secretos del proveedor, logs centralizados y health/readiness separados. Staging debe usar datos sintéticos.

## Next steps

Seleccionar proveedor y RPO/RTO; definir build reproducible, migración controlada, automatización/custodia de backups y rollback antes del primer release.
