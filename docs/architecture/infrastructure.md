# Infraestructura

## Current state

[IMPLEMENTADO] Uvicorn/FastAPI, PostgreSQL configurable y storage privado local para justificantes. [PENDIENTE] No hay Docker, proxy, TLS, CI/CD, staging, backups, restore probado, métricas ni configuración de hosting en el repositorio.

## Target state

[PROPUESTO] despliegue de una aplicación detrás de reverse proxy con HTTPS, PostgreSQL administrado o respaldado, volumen privado persistente, secretos del proveedor, logs centralizados y health/readiness separados. Staging debe usar datos sintéticos.

## Next steps

Seleccionar proveedor y RPO/RTO; definir build reproducible, migración controlada, backup y rollback antes del primer release.
