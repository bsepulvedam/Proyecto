# Estándares de base de datos

snake_case, PK explícita, FKs con política `ondelete`, constraints nombrados e índices guiados por consultas. `created_at`/`updated_at` con zona y UTC. Dinero/cantidad usa `Numeric`, nunca float. Estados críticos tienen check o catálogo. Historial transaccional se corrige con compensación. Cada cambio usa migración nueva, reversible cuando sea seguro y probada desde cero y desde versión previa.
