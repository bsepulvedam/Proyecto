# Estado actual y continuidad de Boliklor


Fuente compacta de continuidad. Ante diferencias prevalecen código ejecutable, configuración efectiva, migraciones y tests. Estados usados: `[IMPLEMENTADO]`, `[CONFIRMADO]`, `[PARCIAL]`, `[PREVISTO]`, `[PENDIENTE]` y `[DEUDA_TECNICA]`.

**Documentos relacionados (fuente extendida):** `docs/audits/PROJECT_TECHNICAL_BASELINE.md`, `docs/audits/BOLIKLOR_TECHNICAL_AUDIT.md` (con 5 addenda), `docs/plans/active/BOLIKLOR_ROADMAP.md`, `docs/architecture/BOLIKLOR_BOT_API_DESIGN.md`.

## 1. Estado Git verificado

- [CONFIRMADO 2026-09-07] Rama `main`; `HEAD` real `e4251dc0f7a1085f4f24d64e92dfc6771755df3a` (`e4251dc`, `Actualizar cierre de Asistencia 4B-3`, 2026-09-03T17:14:54-04:00).
- [CONFIRMADO 2026-09-21] Se versionó por primera vez `docs/audits/PROJECT_TECHNICAL_BASELINE.md` (existía localmente pero nunca se había comiteado) junto con la auditoría técnica completa, el roadmap y el diseño de integración del bot.
- [PENDIENTE] Confirmar hash de HEAD tras el commit que incorpora esta actualización.

## 2. Base efectiva y Alembic

- [CONFIRMADO 2026-09-21] PostgreSQL 18.6, base `boliklor_ot`. Migración de Fase 0 (`20260921_10_inventario_fase0_fundacion`) aplicada contra producción, probada dos veces (`upgrade`/`downgrade`) contra bases desechables antes de aplicarse.
- [CONFIRMADO 2026-09-22] `alembic current`/`heads`: `20260922_11 (head)` — migración `20260922_11_idempotencia_bot` (tabla `claves_idempotencia_bot` para `Idempotency-Key` de la API del bot, Fase 1 tarea 2) aplicada contra `boliklor_ot`. Probada contra base desechable antes de aplicarse: `upgrade`/`downgrade` limpios sin filas, y el guard de downgrade verificado explícitamente (rechaza si hay claves registradas, sin dejar estado intermedio). Tabla vacía tras aplicar; datos preexistentes verificados sin cambios (3 empresas, 206 productos, 263 movimientos, 3 bodegas).
- [CONFIRMADO 2026-09-21] Inventario real tras Fase 0 (Tareas 1, 2, 3, 4): 3 empresas (`ALM`, `BOLIKLOR`, `MASV`), 3 bodegas `PRINCIPAL` (una por empresa), 206 productos (150 previos + 56 nuevos de la carga), 263 movimientos (1 previo + 261 del `Registro de Movimientos` real + 1 `AJUSTE_POSITIVO` de corrección de `BOL-12`). Sigue en `MODO_TRANSICION` — ningún movimiento cargado es `AJUSTE_INICIAL`, así que el switch a `MODO_OPERATIVO` no ocurrió (ver punto abierto INV-002 en sección 9).
- [CONFIRMADO READ ONLY 2026-09-07, histórico] Inventario real antes de Fase 0: 2 empresas (`ALM`, `BOLIKLOR`), 7 unidades, 150 productos, 1 movimiento con 1 detalle, tipo `RECEPCION`.

## 3. Fases cerradas: Asistencia

Sin cambios respecto a la versión anterior de este documento. Asistencia 4B-3 sigue cerrada; sus pendientes en backlog (política de retención GPS, planificación, offline/fraude, alertas, revisión de justificaciones, remuneración definitiva). No reabrir sin decisión expresa.

## 4. Fase activa

**Fase 0 — Fundación de datos e integridad: Tareas 1, 2, 3 y 4 completas y ejecutadas contra `boliklor_ot` (2026-09-21).** Falta únicamente cerrar Tarea 5 (tests incrementales — parcialmente ya cubierta durante las Tareas 1/2/4; pendiente cobertura específica de `inventory_sync_service.py`) y decidir el backlog abierto en sección 9 antes de dar la fase por cerrada al 100%. Próxima fase: **Fase 1 — API del bot (solo lectura + recepción)**, según `BOLIKLOR_ROADMAP.md`.

**INVENTARIO MVP + integración con el bot de Telegram (N8N/Gemini)** — ambas avanzan juntas, no por separado. La fuente operacional final sigue siendo PostgreSQL + ledger; el bot deja de escribir en Google Sheets como registro final y pasa a llamar una API nueva del ERP (`/api/bot/inventario/*`, ver `BOLIKLOR_BOT_API_DESIGN.md`) que reutiliza los mismos servicios que la interfaz web.

El primer gate ya no es "esperar el XLSX actualizado" — **ya se recibió, se analizó y se cargó** (`data/inventario_sync/Inventario IA - PRUEBAS.xlsx`, gitignored, verificado directamente y ejecutado contra producción). Sigue pendiente un segundo input: ejemplos reales de Guía de Despacho (ver sección 8).

## 5. Inventario existente y brechas

Se mantiene todo lo `[IMPLEMENTADO]`/`[PARCIAL]`/`[PENDIENTE]` de la versión anterior de este documento (catálogo, recepción, ledger técnico, stock por empresa). Se agrega:

- [IMPLEMENTADO 2026-09-21] Existe una tercera empresa real, **Mas Vial** (`MASV`, prefijo de SKU `MASV-*`), cargada en Fase 0 con 34 filas de stock activo del inventario real del bot.
- [CONFIRMADO 2026-09-21] Costo fijo `= 1` para el 100% de los productos de ALM y Mas Vial en el inventario real — son bodegas/empresas sin costeo real, **definitivo**, no temporal. Sólo Boliklor tiene costeo real (promedio ponderado móvil).
- [IMPLEMENTADO 2026-09-21] INV-001 resuelto: `/productos` ya no lee `_legacy_stock_values` de forma incondicional. Se eliminó esa función y se creó `inventory_stock_service.stock_values_by_sku`, que delega en `inventory_stock_rows` (la misma fuente que ya usan `/inventario/stock/*`) y respeta `inventory_mode`. Verificado con dos tests de paridad en `test_inventory_phase9.py` (modo transición y modo operativo).
- [CONFIRMADO 2026-09-21] Dashboard exponiendo KPIs/movimientos de Inventario a JEFATURA sin `INVENTARIO_ACCESS` es **intencional** (antes se trataba como posible bug). No modificar ese comportamiento.
- [IMPLEMENTADO 2026-09-21] Servicio de carga inicial `app/services/inventory_sync_service.py`: lee `data/inventario_sync/Inventario IA - PRUEBAS.xlsx` (Maestro de Productos + Stock Consolidado + Registro de Movimientos), concilia catálogo sin sobreescribir productos existentes (conflictos reportados, no resueltos silenciosamente) y carga movimientos con idempotencia por `ID Transacción` (reutilizado directamente como `numero_documento`, cabe en `VARCHAR(30)`). Ejecutado contra `boliklor_ot` el 2026-09-21: 56 productos nuevos, 135 ya existían, 15 conflictos de `stock_minimo` (no sobreescritos), 9 productos rechazados por unidad no reconocida; 261 movimientos cargados, 17 rechazados. Detalle completo del backlog resultante en sección 9.

## 6. Decisiones funcionales aprobadas para continuidad

Se mantienen íntegras las decisiones 1, 2 (revisada, ver abajo), 4 a 13 de la versión anterior de este documento (fuente de verdad PostgreSQL, movimientos inmutables, Guía SII, ajustes con motivo/actor, devoluciones relacionables, costo promedio ponderado móvil con costo histórico por despacho, exclusión de lotes/FIFO/FEFO, roles/permisos granulares, "Detalles y trabajos", exportaciones, preparación BI). Se actualiza:

3'. **[CONFIRMADO — REVISADO 2026-09-21] Stock negativo prohibido, con resolución explícita para transferencias:** se mantiene la prohibición original (ningún despacho/ajuste confirmado puede dejar saldo menor que cero) como regla general hacia adelante. El tipo de movimiento **`TRANSFERENCIA_ENTRE_EMPRESAS`** (salida en la empresa que presta + entrada en la que recibe, atómico) queda implementado en el modelo/migración para el caso general de préstamos entre empresas.

3''. **[CONFIRMADO — EXCEPCIÓN DOCUMENTADA 2026-09-21] `BOL-12` NO se reconcilió como transferencia y NO quedó en saldo cero.** El usuario confirmó que el material (microesferas de vidrio) sí llegó a Boliklor — no fue un préstamo a otra empresa, fue un error de registro durante pruebas del bot — por lo que se cargó como `AJUSTE_POSITIVO` (no `TRANSFERENCIA_ENTRE_EMPRESAS`). Al calcular el saldo real desde los 278 movimientos de `Registro de Movimientos`, el neto de `BOL-12` da **-60**, no los -40 que muestra la hoja `Stock Consolidado` (esa hoja incluye una operación de prueba del bot — `Operaciones_Pendientes`, estado `CONFIRMADA_PRUEBA` — que nunca quedó registrada como movimiento formal). El usuario, ya informado de esta discrepancia dos veces, autorizó explícitamente aplicar el ajuste con el monto original de **+40** en vez de +60. **Resultado real en `boliklor_ot`: `BOL-12` quedó en -20**, el único saldo negativo de toda la base tras la carga. Esto es una excepción autorizada y documentada a la regla 3', no un bug ni un incumplimiento silencioso — sigue en backlog (sección 9) como pendiente de decidir si se corrige con un ajuste adicional de +20 o se deja así intencionalmente.

10'. **[CONFIRMADO — REVISADO 2026-09-21] Roles/permisos:** se ratifica **no crear rol `BODEGA`** (el bot de Telegram usa ese nombre internamente; se mapea a los permisos granulares aprobados aquí — `INVENTARIO_VER` + `INVENTARIO_RECIBIR` + `INVENTARIO_DESPACHAR` por defecto — no a un rol nuevo del ERP).

14. **[CONFIRMADO 2026-09-21] Jerarquía Empresa → Bodega:** se construye la tabla `Bodega` (FK a `Empresa`) ya en Fase 0, no se pospone. Seed inicial: una bodega principal por empresa (Boliklor, ALM, Mas Vial), dejando espacio para múltiples bodegas por empresa sin migración estructural futura.

15. **[CONFIRMADO 2026-09-21] Integración con bot externo:** el bot de Telegram (N8N + Gemini) es la vía principal de consultas/actualizaciones rápidas de Inventario para el personal autorizado. Se autentica con una API key de servicio, con alcance limitado a `/api/bot/inventario/*`. El ERP nunca duplica lógica de negocio para el bot — el bot llama los mismos servicios que ya usa la interfaz web. Ver `BOLIKLOR_BOT_API_DESIGN.md` para el contrato completo, incluyendo las fases (lectura+recepción primero; despacho/devolución/ajuste sólo cuando el ERP los tenga operacionales).

16. **[CONFIRMADO 2026-09-21] Trazabilidad de origen:** todo movimiento de inventario registra `origen` (`ERP_WEB` | `BOT_TELEGRAM`) y `actor_referencia` (quién lo pidió), mapeando directo desde la columna `Usuario / Origen` que el bot ya mantiene.

## 7. Exclusiones y prohibiciones actuales

Sin cambios respecto a la versión anterior: no implementar aún despacho/devolución/ajuste operacional completo (eso es Fase 3, no Fase 0), no ejecutar migraciones contra `boliklor_ot`/`boliklor_ot_test` sin gate explícito, no ampliar OT, no hacer deploy sin autorización. La carga inicial de datos de Fase 0 SÍ está autorizada — es la tarea explícita de esta fase, con las decisiones ya tomadas como marco.

## 8. Próximos inputs necesarios

1. [RESUELTO 2026-09-21] ~~XLSX actualizado de Inventario~~ — recibido, analizado y cargado contra `boliklor_ot` (`data/inventario_sync/Inventario IA - PRUEBAS.xlsx`, gitignored).
2. [PENDIENTE] **Ejemplos reales de Guía de Despacho** (imágenes/PDF) — sigue bloqueando únicamente el contrato estructurado de despacho de Fase 3, no bloquea Fase 0 ni Fase 1.

## 9. Riesgos y documentación obsoleta

Se mantienen los riesgos de la versión anterior. Se agrega:
- [RIESGO ABIERTO, NO resuelto — revisar decisión 3'' sección 6] `BOL-12` sigue en saldo negativo real (**-20**) en `boliklor_ot` tras la carga de Fase 0. No es un bug del servicio de carga (el cálculo es correcto y fue verificado dos veces); es el resultado de una decisión de negocio explícita de aplicar un ajuste de +40 sabiendo que el déficit real era de 60. Pendiente decidir si se aplica un segundo `AJUSTE_POSITIVO` de +20 para cerrar en cero, o si se deja así intencionalmente con una observación registrada.
- [DEUDA_TECNICA DOCUMENTAL] `docs/decisions/ADR-005-inventory-stock-ledger.md` sigue sin actualizar formalmente; debe reflejar la reconciliación real de `BOL-12` (AJUSTE_POSITIVO parcial, no transferencia, no saldo cero) antes de marcarse ACCEPTED.
- [DEUDA_TECNICA, confirmada 2026-09-21] tests/test_work_orders_web.py y
  tests/test_inventory_base.py no configuran AUTH_ENFORCED/SESSION_SECRET
  en setUp — todas sus requests reciben 303 de redirect a /login en vez del
  código esperado. Son 20 fallos pre-existentes en main que no tienen relación
  con la Tarea 2. El fix sigue el patrón de test_identity_auth.py líneas 92-93.
  No se corrige en Fase 0 para no mezclar alcances — queda como Tarea 5
  (testing-quality). [ACTUALIZACIÓN 2026-09-21] Durante la Tarea 3 se detectó
  que `app/core/config.py`, `app/main.py` y estos mismos dos archivos de test
  fueron modificados en paralelo (fuera de esta sesión) — aparenta ser trabajo
  en curso de Fase 2 (hardening `COOKIE_SECURE`/`SESSION_SECRET` en producción)
  y/o del propio fix de este ítem. No verificado ni tocado por Fase 0; revisar
  su estado antes de asumir que sigue siendo exactamente este mismo hallazgo.
- [PENDIENTE — hallazgo nuevo, carga de Fase 0] 3 movimientos históricos rechazados por inconsistencia de empresa: `TX-0163` (ALM-52), `TX-0164` (ALM-53), `TX-0230` (MASV-24) — todos registrados con bodega "Boliklor" pero producto de otra empresa, mismo patrón que originó el caso `BOL-12`. Confirmado por el usuario: no tocar por ahora, quedan sin cargar hasta decidir si son errores de digitación o préstamos reales (candidatos a `TRANSFERENCIA_ENTRE_EMPRESAS`).
- [PENDIENTE — hallazgo nuevo, carga de Fase 0] 9 productos con unidad no reconocida en `unidades_medida` (`LT` ×6, `METRO` ×2, 1 vacío/"nan"): `BOL-11`, `BOL-13`, `BOL-57`, `BOL-97`, `BOL-105`, `ALM-11`, `ALM-13`, `MASV-11`, `MASV-13`. No creados; sus movimientos asociados (14 filas de `Registro de Movimientos`) tampoco se cargaron. Confirmado por el usuario: revisar después.
- [PENDIENTE — hallazgo nuevo, carga de Fase 0] 3 SKUs en `Stock Consolidado` sin fila en `Maestro de Productos` (`ALM-54`, `ALM-55`, `ALM-56`) — sin nombre/unidad/familia disponible para crearlos. Confirmado por el usuario: dejar sin cargar.
- [INFORMATIVO] 15 productos con `stock_minimo` distinto entre Postgres y `Stock Consolidado` (todos `BOL-*`, ya existían antes de Fase 0): `BOL-28, BOL-29, BOL-30, BOL-39, BOL-40, BOL-62, BOL-68, BOL-69, BOL-70, BOL-71, BOL-76, BOL-78, BOL-80, BOL-85, BOL-114`. Reportados como conflicto por `inventory_sync_service`, no sobreescritos. Pendiente decidir cuál valor es el vigente.

## 10. Próximo paso exacto

**Fase 0 — Tareas 1, 2, 3 y 4 completas y ejecutadas contra `boliklor_ot` (2026-09-21).** Pendiente antes de cerrar la fase al 100%:
1. Tarea 5: sumar cobertura de test específica para `inventory_sync_service.py` (se validó manualmente contra bases desechables y contra producción, pero no quedó como test automatizado en `tests/`).
2. Resolver el backlog de sección 9: saldo residual de `BOL-12` (-20), los 3 movimientos de empresa cruzada, las 9 unidades no reconocidas, los 3 SKUs sin Maestro, y los 15 conflictos de `stock_minimo`.
3. Confirmar el estado real de los archivos modificados en paralelo (`app/core/config.py`, `app/main.py`, `tests/test_inventory_base.py`, `tests/test_work_orders_web.py`) antes de asumir que el hallazgo de aislamiento de tests sigue vigente tal cual se documentó.

Con eso resuelto, sigue **Fase 1 — API del bot (solo lectura + recepción)** según `BOLIKLOR_ROADMAP.md`. El subagente `database-postgresql-alembic` y `inventory-legacy-cutover` (en `.claude/agents/`) siguen preparados con este contexto para lo que falte de Fase 0.

**[CONFIRMADO 2026-09-22] Fase 1 ya arrancó en paralelo al backlog pendiente de Fase 0** (decisión del usuario, no bloqueada por lo anterior). Avance según diseño de `BOLIKLOR_BOT_API_DESIGN.md`:
1. [IMPLEMENTADO] Mecanismo de API key de servicio: `app/core/service_auth.py` (`require_service_key`, digest SHA-256, deniega por defecto), router `app/api/bot_inventario.py` montado en `app/main.py` fuera de `require_platform_access`, config `BOT_SERVICE_KEY_HASH` con validación de formato al arranque, script `app/scripts/generate_bot_service_key.py`.
2. [IMPLEMENTADO] `create_receipt` extendido con `origen_bot: OrigenMovimientoBot | None = None` (schema nuevo en `app/schemas/bot_inventario.py`), retrocompatible — la web sigue llamándolo con dos argumentos. Modelo/migración `20260922_11_idempotencia_bot` (tabla `claves_idempotencia_bot`) aplicados contra `boliklor_ot`, sin código todavía que la use.
3. [PENDIENTE] Los 3 endpoints GET (`/productos`, `/stock/{empresa}`, `/movimientos`) — decisión ya tomada: `/stock/{empresa}` debe devolver `stock_ledger` + `stock_legacy` + el modo vigente, no un solo número, mientras la base siga en `MODO_TRANSICION`.
4. [PENDIENTE] `POST /recepciones` con idempotencia (usa la tabla de la tarea 2) — decisión ya tomada: una sola API key para todo el bot, `actor_referencia` viene del campo `solicitado_por` del payload.
5. [PENDIENTE] Tests de los 4 endpoints (auth rechazada, idempotencia, recepción real end-to-end).
