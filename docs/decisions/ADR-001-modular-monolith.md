# ADR-001: Monolito modular

**Status:** PROPOSED

## Context
El sistema ya es una aplicación FastAPI única y el equipo necesita velocidad y límites claros.
## Decision
Evolucionar por dominios dentro de un solo despliegue y PostgreSQL, con contratos internos y sin ciclos.
## Consequences
Operación simple y refactor incremental; exige disciplina de ownership.
## Alternatives
Monolito por capas actual; microservicios, rechazados por costo sin evidencia.
## Open Questions
Orden físico de extracción y reglas de importación automatizables.
