# ADR-003: Autenticación y RBAC

**Status:** PROPOSED

## Context
Hay sesiones seguras básicas y permisos hardcodeados; el modo desarrollo puede omitir auth.
## Decision
Producción fail-closed, sesión opaca con CSRF y RBAC central por capacidades. Mantener Argon2id.
## Consequences
Operación segura requiere validación de entorno y matriz de permisos.
## Alternatives
JWT stateless o proveedor externo; sin necesidad actual demostrada.
## Open Questions
MFA, recuperación, rate limits y alcance de Jefatura.
