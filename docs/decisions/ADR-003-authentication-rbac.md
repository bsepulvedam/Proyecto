# ADR-003: Autenticación y RBAC

**Status:** ACCEPTED

## Context
Hay sesiones seguras básicas y permisos hardcodeados; el modo desarrollo puede omitir auth.
## Decision
Producción y staging fail-closed, sesión opaca con CSRF y RBAC central por capacidades. `AUTH_ENFORCED` es verdadero por defecto y solo puede desactivarse con `APP_ENV=development|test`. Mantener Argon2id.
## Consequences
Operación segura requiere validación de entorno y matriz de permisos.
## Alternatives
JWT stateless o proveedor externo; sin necesidad actual demostrada.
## Open Questions
MFA, recuperación, rate limits y alcance de Jefatura.
