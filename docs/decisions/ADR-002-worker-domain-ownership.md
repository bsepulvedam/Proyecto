# ADR-002: Ownership de Trabajador

**Status:** PROPOSED

## Context
`Trabajador` está implementado junto a identidad, pero representa la ficha laboral y asistencia lo referencia.
## Decision
RRHH será dueño conceptual de Trabajador; Identidad mantiene cuenta/credencial; Asistencia usa `trabajador_id`.
## Consequences
Evita duplicación y permite trabajadores sin cuenta. La migración física será posterior y compatible.
## Alternatives
Cuenta=trabajador; copia en asistencia, ambas rechazadas.
## Open Questions
Identificador canónico y ciclo laboral mínimo.
