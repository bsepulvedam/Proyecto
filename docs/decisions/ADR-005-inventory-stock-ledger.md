# ADR-005: Ledger de stock

**Status:** PROPOSED

## Context
El stock ya se deriva de movimientos con snapshots; faltan lotes y salidas maduras.
## Decision
Mantener movimientos auditables como verdad; correcciones compensatorias. Proyecciones de saldo deben reconciliarse con ledger.
## Consequences
Trazabilidad fuerte; requiere transacciones y estrategia de escala.
## Alternatives
Saldo mutable único, rechazado; event sourcing completo, excesivo.
## Open Questions
Lotes, FEFO/FIFO, costo, stock negativo y aprobación de ajustes.
