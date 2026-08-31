# Reglas de Inventario

- [IMPLEMENTADO] SKU único global, factor positivo, stock mínimo no negativo y cantidades de movimiento positivas.
- [IMPLEMENTADO] recepciones validan empresa/unidad, conservan snapshots y se confirman atómicamente.
- [IMPLEMENTADO] tipos positivos y negativos determinan stock; número de movimiento usa secuencia PostgreSQL.
- [PROPUESTO] movimientos confirmados no se editan: corrección compensatoria con actor/motivo.
- [PENDIENTE] unicidad SKU por empresa, stock negativo, aprobación de ajustes, método de costo y reservas.
