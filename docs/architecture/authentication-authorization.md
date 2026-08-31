# Autenticación y autorización

## Current state

[IMPLEMENTADO] Usuarios y trabajadores son entidades distintas con relación opcional uno-a-uno. Contraseñas Argon2id (mínimo 12), comparación dummy contra enumeración básica, sesiones opacas revocables con hash HMAC, expiración, cambio obligatorio de temporal, logout, CSRF y cookies HttpOnly/SameSite Lax. Roles: `ADMIN`, `JEFATURA`, `TRABAJADOR`.

[IMPLEMENTADO] Permisos están en `ROLE_PERMISSIONS` de `auth_service.py`. ADMIN tiene wildcard; JEFATURA solo `ASISTENCIA_SUPERVISAR`; TRABAJADOR `ASISTENCIA_PROPIA`. Routers tienen dependencias backend. `AUTH_ENFORCED` es verdadero por defecto; `AUTH_ENFORCED=false` exige `APP_ENV=development|test`, y la composición de la aplicación valida secreto y configuración. [DEUDA_TECNICA] No hay recuperación autoservicio, MFA, bloqueo/rate limiting, rotación explícita de sesión ni persistencia de permisos.

## Target state

[IMPLEMENTADO] autenticación obligatoria y fail-closed en entornos no locales. [PROPUESTO] RBAC con catálogo central de permisos y matriz aprobada; auditoría de acciones privilegiadas; rate limiting en el borde; expiración/rotación definidas. Mantener cuenta separada del trabajador.

## Open questions

[PENDIENTE] Política de contraseñas, MFA, duración de sesión, roles de Jefatura, acceso de soporte y proceso de recuperación requieren aprobación empresarial.
