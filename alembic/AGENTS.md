# Reglas de `alembic/`

Aplican además las reglas raíz. No modificar revisiones existentes. Una revisión nueva debe tener un único `down_revision`, upgrade/downgrade revisados, nombres explícitos para constraints e índices y estrategia para datos preexistentes. Comparar el esquema con modelos, probar en una base desechable y documentar riesgos de bloqueo o pérdida. Nunca aplicar una migración sin confirmar entorno y autorización.
