# ADR-004: Geolocalización de asistencia

**Status:** ACCEPTED

## Context
Lugares admiten coordenada/radio, pero no hay marcajes. GPS es sensible e impreciso.
## Decision
Capturar únicamente al registrar `ENTRADA` o `SALIDA`, sin seguimiento continuo. El backend evaluará la captura contra el radio configurable de la zona. Un evento fuera de rango se conserva y genera incidencia/revisión. Guardar precisión y separar evidencia de la evaluación geográfica versionada.
## Consequences
Trazabilidad y recalculabilidad; aumenta deber de privacidad y seguridad.
## Alternatives
Guardar solo booleano; seguimiento continuo, rechazado por desproporción.
## Open Questions
Retención, radios, consentimiento, offline y excepciones.
