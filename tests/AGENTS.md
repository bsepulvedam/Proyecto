# Reglas de `tests/`

Aplican además las reglas raíz. Mantener aislamiento: SQLite o PostgreSQL desechable, variables restauradas y almacenamiento temporal. Cubrir éxito y rechazo, especialmente autenticación, roles, CSRF, ownership, stock y geolocalización. No depender del orden de ejecución, reloj real, red ni archivos privados. Reportar cuando la infraestructura local impida ejecutar la suite.
