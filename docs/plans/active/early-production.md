# Plan de producción temprana

## BLOCKER

- Hacer autenticación fail-closed por entorno; secret y cookie Secure obligatorios en producción.
- Completar y aprobar MVP: RRHH base, marcaje real/geolocalización y administración de asistencia; salidas/ajustes y lotes si los productos lo requieren.
- Ejecutar suite y migraciones desde cero/sobre copia anonimizada en PostgreSQL; añadir tests de permisos, concurrencia y flujos críticos.
- Proveer HTTPS, dominio/proxy, DB y storage persistentes, backups automáticos y restore probado.
- Definir acceso/retención de GPS, justificantes y datos laborales.

## REQUIRED

- Build reproducible, staging, variables `DATABASE_URL`, `SESSION_SECRET`, `AUTH_ENFORCED=true`, `COOKIE_SECURE=true`, `SESSION_HOURS`, `APP_TIMEZONE`, storage y límite de upload.
- Readiness DB, logs estructurados, captura de errores, auditoría mínima, runbooks, migración controlada y rollback.
- Rate limit login, cabeceras proxy/seguridad y matriz RBAC aprobada.

## RECOMMENDED

- CI con compile/tests/migration verification y escaneo razonable; smoke/E2E; métricas y alertas; PostgreSQL administrado y despliegue inmutable.

## LATER

- Granularidad avanzada RRHH, reservas, BI, automatización y demás extensiones ERP.

## Criterio mínimo de go-live

Todos los blockers cerrados con evidencia; restore ensayado; cero hallazgos críticos/altos sin aceptación explícita; suite verde en artefacto desplegable; smoke test de login, trabajador, marcaje, inventario y autorización; owner operativo y rollback definidos.
