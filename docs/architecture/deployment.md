# Despliegue progresivo

Local: `.env` no versionado, PostgreSQL local, Alembic y Uvicorn. Staging propuesto: build inmutable, DB aislada, HTTPS, migraciones verificadas y smoke tests. Producción propuesta: una instancia o servicio con rollback, DB con backups PITR si está disponible, almacenamiento privado persistente y alertas.

Secuencia: backup verificado → desplegar artefacto → ejecutar migraciones compatibles una sola vez → readiness → smoke tests → habilitar tráfico. Nunca automatizar producción hasta probar el flujo y la reversión.
