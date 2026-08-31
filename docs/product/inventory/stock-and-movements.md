# Stock y movimientos

`movimientos_inventario` y sus detalles son el ledger. `calculate_stock_from_movements` suma presentaciones con signo por tipo. Existe modo transición mientras no haya `AJUSTE_INICIAL`; puede mostrar stock legacy de un Excel.

[DEUDA_TECNICA] el cálculo recorre todos los movimientos y no bloquea concurrencia para despachos futuros. [PROPUESTO] validar disponibilidad y escribir salida en una sola transacción; optimizar con agregación SQL o proyección reconciliable, nunca con un contador sin ledger.
