# ADR-004: Geolocalización de asistencia

**Status:** ACCEPTED

## Context
Lugares admiten coordenada/radio, pero no hay marcajes. GPS es sensible e impreciso.
## Decision
Capturar únicamente al registrar `ENTRADA` o `SALIDA`, sin seguimiento continuo. El backend evaluará la captura contra el radio configurable de la zona. Un evento fuera de rango se conserva y genera incidencia/revisión. Guardar precisión y separar evidencia de la evaluación geográfica versionada.

Extensión aceptada para 4B-2B: soportar conjuntamente geocercas `RADIO` y `COMUNA`, evaluar todas las zonas activas sin asignación ni elección del trabajador y resolver solapamientos por estado, prioridad, margen e ID. Las comunas usan el subconjunto versionado de SUBDERE DPA 2023, seleccionado siempre por `CUT_COM`, transformado de EPSG:5360 a EPSG:4326. Los primeros 100 m exteriores configurables se persisten como `DENTRO_TOLERANCIA` sin incidencia automática.
## Consequences
Trazabilidad y recalculabilidad; aumenta deber de privacidad y seguridad. El runtime depende de Shapely, pyproj y del GeoJSON versionado; debe fallar de forma segura si el catálogo no puede validarse. Cambiar una zona no reescribe la evaluación histórica, que conserva tipo, tolerancia y versión geométrica aplicados.
## Alternatives
Guardar solo booleano; seguimiento continuo, rechazado por desproporción.
## Open Questions
Retención, consentimiento, offline, excepciones y política futura de supervisión para `DENTRO_TOLERANCIA`.
