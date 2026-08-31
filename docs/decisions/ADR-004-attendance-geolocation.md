# ADR-004: Geolocalización de asistencia

**Status:** PROPOSED

## Context
Lugares admiten coordenada/radio, pero no hay marcajes. GPS es sensible e impreciso.
## Decision
Capturar solo por evento, guardar precisión y separar evidencia de la evaluación geográfica versionada.
## Consequences
Trazabilidad y recalculabilidad; aumenta deber de privacidad y seguridad.
## Alternatives
Guardar solo booleano; seguimiento continuo, rechazado por desproporción.
## Open Questions
Retención, radios, consentimiento, offline y excepciones.
