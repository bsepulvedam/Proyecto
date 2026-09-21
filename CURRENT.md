# Estado actual y continuidad de Boliklor

*Propuesta de reemplazo del `CURRENT.md` sin comittear desde 2026-09-07. Conserva sus decisiones válidas, incorpora lo definido desde entonces (auditoría técnica, integración con el bot de Telegram, reconciliación con el inventario real). Revisar antes de reemplazar el archivo real y comittear.*

Fuente compacta de continuidad. Ante diferencias prevalecen código ejecutable, configuración efectiva, migraciones y tests. Estados usados: `[IMPLEMENTADO]`, `[CONFIRMADO]`, `[PARCIAL]`, `[PREVISTO]`, `[PENDIENTE]` y `[DEUDA_TECNICA]`.

**Documentos relacionados (fuente extendida):** `docs/audits/PROJECT_TECHNICAL_BASELINE.md`, `docs/audits/BOLIKLOR_TECHNICAL_AUDIT.md` (con 5 addenda), `docs/plans/active/BOLIKLOR_ROADMAP.md`, `docs/architecture/BOLIKLOR_BOT_API_DESIGN.md`.

## 1. Estado Git verificado

- [CONFIRMADO 2026-09-07] Rama `main`; `HEAD` real `e4251dc0f7a1085f4f24d64e92dfc6771755df3a` (`e4251dc`, `Actualizar cierre de Asistencia 4B-3`, 2026-09-03T17:14:54-04:00).
- [CONFIRMADO 2026-09-21] Se versionó por primera vez `docs/audits/PROJECT_TECHNICAL_BASELINE.md` (existía localmente pero nunca se había comiteado) junto con la auditoría técnica completa, el roadmap y el diseño de integración del bot.
- [PENDIENTE] Confirmar hash de HEAD tras el commit que incorpora esta actualización.

## 2. Base efectiva y Alembic

- [CONFIRMADO READ ONLY 2026-09-07] PostgreSQL 18.6, base `boliklor_ot`. `alembic current`/`heads`: `20260902_09 (head)`.
- [CONFIRMADO READ ONLY 2026-09-07] Inventario real antes de Fase 0: 2 empresas (`ALM`, `BOLIKLOR`), 7 unidades, 150 productos, 1 movimiento con 1 detalle, tipo `RECEPCION`. Sin `AJUSTE_INICIAL` → sigue en `MODO_TRANSICION`.
- [PENDIENTE — Fase 0] Agregar empresa `MASV` (Mas Vial), tabla `Bodega`, columnas `origen`/`actor_referencia` en `movimientos_inventario`, y tipo `TRANSFERENCIA_ENTRE_EMPRESAS`. Ver sección 6.

## 3. Fases cerradas: Asistencia

Sin cambios respecto a la versión anterior de este documento. Asistencia 4B-3 sigue cerrada; sus pendientes en backlog (política de retención GPS, planificación, offline/fraude, alertas, revisión de justificaciones, remuneración definitiva). No reabrir sin decisión expresa.

## 4. Fase activa

**INVENTARIO MVP + integración con el bot de Telegram (N8N/Gemini)** — ambas avanzan juntas, no por separado. La fuente operacional final sigue siendo PostgreSQL + ledger; el bot deja de escribir en Google Sheets como registro final y pasa a llamar una API nueva del ERP (`/api/bot/inventario/*`, ver `BOLIKLOR_BOT_API_DESIGN.md`) que reutiliza los mismos servicios que la interfaz web.

El primer gate ya no es "esperar el XLSX actualizado" — **ya se recibió y se analizó** (`Inventario_IA_-_PRUEBAS.xlsx`, verificado directamente). Sigue pendiente un segundo input: ejemplos reales de Guía de Despacho (ver sección 8).

## 5. Inventario existente y brechas

Se mantiene todo lo `[IMPLEMENTADO]`/`[PARCIAL]`/`[PENDIENTE]` de la versión anterior de este documento (catálogo, recepción, ledger técnico, stock por empresa). Se agrega:

- [CONFIRMADO 2026-09-21] Existe una tercera empresa real, **Mas Vial** (`MASV`, prefijo de SKU `MASV-*`), con 34 filas de stock activo en el inventario real del bot. No estaba contemplada — se agrega en Fase 0.
- [CONFIRMADO 2026-09-21] Costo fijo `= 1` para el 100% de los productos de ALM y Mas Vial en el inventario real — son bodegas/empresas sin costeo real, **definitivo**, no temporal. Sólo Boliklor tiene costeo real (promedio ponderado móvil).
- [DEUDA_TECNICA, confirmada en código el 2026-09-21] `/productos` lee stock legacy incondicionalmente sin consultar `inventory_mode`; otras pantallas sí usan el ledger. Resolver en Fase 0 como parte de la carga inicial.
- [CONFIRMADO 2026-09-21] Dashboard exponiendo KPIs/movimientos de Inventario a JEFATURA sin `INVENTARIO_ACCESS` es **intencional** (antes se trataba como posible bug). No modificar ese comportamiento.

## 6. Decisiones funcionales aprobadas para continuidad

Se mantienen íntegras las decisiones 1, 2 (revisada, ver abajo), 4 a 13 de la versión anterior de este documento (fuente de verdad PostgreSQL, movimientos inmutables, Guía SII, ajustes con motivo/actor, devoluciones relacionables, costo promedio ponderado móvil con costo histórico por despacho, exclusión de lotes/FIFO/FEFO, roles/permisos granulares, "Detalles y trabajos", exportaciones, preparación BI). Se actualiza:

3'. **[CONFIRMADO — REVISADO 2026-09-21] Stock negativo prohibido, con resolución explícita para transferencias:** se mantiene la prohibición original (ningún despacho/ajuste confirmado puede dejar saldo menor que cero). El caso real que generaba negativos (préstamos de material entre Boliklor/ALM/Mas Vial) se resuelve con un tipo de movimiento nuevo, **`TRANSFERENCIA_ENTRE_EMPRESAS`**: salida en la empresa que presta + entrada en la que recibe, en una sola transacción atómica. El caso ya existente (`BOL-12`, saldo -40) se reconcilia en la carga inicial como una transferencia retroactiva, no como un ajuste suelto.

10'. **[CONFIRMADO — REVISADO 2026-09-21] Roles/permisos:** se ratifica **no crear rol `BODEGA`** (el bot de Telegram usa ese nombre internamente; se mapea a los permisos granulares aprobados aquí — `INVENTARIO_VER` + `INVENTARIO_RECIBIR` + `INVENTARIO_DESPACHAR` por defecto — no a un rol nuevo del ERP).

14. **[CONFIRMADO 2026-09-21] Jerarquía Empresa → Bodega:** se construye la tabla `Bodega` (FK a `Empresa`) ya en Fase 0, no se pospone. Seed inicial: una bodega principal por empresa (Boliklor, ALM, Mas Vial), dejando espacio para múltiples bodegas por empresa sin migración estructural futura.

15. **[CONFIRMADO 2026-09-21] Integración con bot externo:** el bot de Telegram (N8N + Gemini) es la vía principal de consultas/actualizaciones rápidas de Inventario para el personal autorizado. Se autentica con una API key de servicio, con alcance limitado a `/api/bot/inventario/*`. El ERP nunca duplica lógica de negocio para el bot — el bot llama los mismos servicios que ya usa la interfaz web. Ver `BOLIKLOR_BOT_API_DESIGN.md` para el contrato completo, incluyendo las fases (lectura+recepción primero; despacho/devolución/ajuste sólo cuando el ERP los tenga operacionales).

16. **[CONFIRMADO 2026-09-21] Trazabilidad de origen:** todo movimiento de inventario registra `origen` (`ERP_WEB` | `BOT_TELEGRAM`) y `actor_referencia` (quién lo pidió), mapeando directo desde la columna `Usuario / Origen` que el bot ya mantiene.

## 7. Exclusiones y prohibiciones actuales

Sin cambios respecto a la versión anterior: no implementar aún despacho/devolución/ajuste operacional completo (eso es Fase 3, no Fase 0), no ejecutar migraciones contra `boliklor_ot`/`boliklor_ot_test` sin gate explícito, no ampliar OT, no hacer deploy sin autorización. La carga inicial de datos de Fase 0 SÍ está autorizada — es la tarea explícita de esta fase, con las decisiones ya tomadas como marco.

## 8. Próximos inputs necesarios

1. [RESUELTO 2026-09-21] ~~XLSX actualizado de Inventario~~ — recibido y analizado (`Inventario_IA_-_PRUEBAS.xlsx`).
2. [PENDIENTE] **Ejemplos reales de Guía de Despacho** (imágenes/PDF) — sigue bloqueando únicamente el contrato estructurado de despacho de Fase 3, no bloquea Fase 0 ni Fase 1.

## 9. Riesgos y documentación obsoleta

Se mantienen los riesgos de la versión anterior. Se agrega:
- [RIESGO MEDIO, mitigado por decisión] El stock negativo activo hoy (`BOL-12 = -40`) ya no es un riesgo abierto — tiene resolución de diseño (`TRANSFERENCIA_ENTRE_EMPRESAS`) y se reconcilia en Fase 0.
- [DEUDA_TECNICA DOCUMENTAL] `docs/decisions/ADR-005-inventory-stock-ledger.md` sigue sin actualizar formalmente; debe reflejar esta reconciliación (transferencias, no negativos sueltos) antes de marcarse ACCEPTED.

## 10. Próximo paso exacto

Ejecutar **Fase 0** de `BOLIKLOR_ROADMAP.md`: migración (empresa MASV, tabla Bodega + seeds, columnas `origen`/`actor_referencia`, tipo `TRANSFERENCIA_ENTRE_EMPRESAS`), servicio de carga inicial desde el inventario real del bot, y reconciliación de `BOL-12`. El subagente `database-postgresql-alembic` y `inventory-legacy-cutover` (en `.claude/agents/`) están preparados con este contexto. Ningún dato real se modifica sin ejecutar primero contra un entorno desechable.
