# Visión general del sistema

## Current state

[IMPLEMENTADO] Aplicación FastAPI única con dos interfaces: HTML/Jinja2 y una API JSON pequeña. PostgreSQL es el destino real; SQLAlchemy administra sesiones y Alembic seis revisiones lineales. Dominios prioritarios conviven en carpetas por capa. Órdenes de trabajo sigue presente aunque no es prioridad de evolución.

## Target state

[PROPUESTO] Monolito modular con módulos `identity`, `human_resources`, `attendance` e `inventory`, y capacidades transversales explícitas. Un proceso desplegable, una base PostgreSQL y contratos internos claros.

## Gaps

[DEUDA_TECNICA] Ownership de trabajador no se refleja en el empaquetado. Configuración no está validada centralmente al arranque. No existen auditoría empresarial, observabilidad ni pipeline.

## Next steps

Cerrar bloqueadores de producción; después extraer límites módulo a módulo manteniendo rutas y tablas compatibles.
