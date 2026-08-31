# Gobernanza de datos

- [PROPUESTO] IDs internos estables; códigos de negocio con unique cuando sean identidad real.
- [IMPLEMENTADO] timestamps con zona en tablas principales; [PROPUESTO] guardar UTC y presentar `APP_TIMEZONE`.
- [PROPUESTO] nombres snake_case en DB/Python y estados con catálogo/check documentado.
- Ownership: RRHH trabajador; Identidad cuenta; Asistencia eventos/justificaciones; Inventario producto/ledger/lote.
- No borrar historial transaccional; correcciones mediante eventos compensatorios auditables.
- Soft delete no es regla universal: aplicar solo tras definir semántica y FKs.
- [PENDIENTE] retención, derechos de acceso, eliminación y precisión de geolocalización requieren política empresarial/legal. Minimizar captura y limitar acceso.
