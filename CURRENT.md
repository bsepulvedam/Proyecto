# Estado actual y continuidad de Boliklor

Fuente compacta de continuidad. Ante diferencias prevalecen código ejecutable, configuración efectiva, migraciones y tests. Estados usados: `[IMPLEMENTADO]`, `[CONFIRMADO]`, `[PARCIAL]`, `[PREVISTO]`, `[PENDIENTE]` y `[DEUDA_TECNICA]`.

## 1. Estado Git verificado

- [CONFIRMADO 2026-09-07] Rama `main`; `HEAD` real `e4251dc0f7a1085f4f24d64e92dfc6771755df3a` (`e4251dc`, `Actualizar cierre de Asistencia 4B-3`, 2026-09-03T17:14:54-04:00).
- [CONFIRMADO 2026-09-07] Referencia local `origin/main`: `e4251dc0f7a1085f4f24d64e92dfc6771755df3a`; divergencia `HEAD...origin/main`: 0 izquierda / 0 derecha. No se ejecutó `fetch`, por lo que esto no confirma el estado remoto más reciente.
- [CONFIRMADO ANTES DE ESTE HANDOFF] `git status`: árbol limpio; `git diff` y `git diff --stat`: vacíos.
- [CONFIRMADO DESPUÉS DE ESTE HANDOFF] La única modificación esperada es `CURRENT.md`. No se ejecutaron `git add`, commit, push, rebase, reset ni deploy.

## 2. Base efectiva y Alembic

- [CONFIRMADO READ ONLY 2026-09-07] Configuración efectiva de `.env`: PostgreSQL, base `boliklor_ot`, usuario `postgres`, servidor PostgreSQL 18.6 x86_64 Windows. No se expuso la URL ni credenciales.
- [CONFIRMADO READ ONLY 2026-09-07] `alembic current`: `20260902_09 (head)`; `alembic heads`: `20260902_09 (head)`.
- [CONFIRMADO READ ONLY 2026-09-07] Inventario real: 2 empresas (`ALM`, `BOLIKLOR`), 7 unidades, 150 productos, 1 movimiento con 1 detalle; tipo existente `RECEPCION`. No existe `AJUSTE_INICIAL`, por lo que el sistema sigue en `MODO_TRANSICION`.
- [CONFIRMADO] No se ejecutaron migraciones ni se modificó `boliklor_ot` o `boliklor_ot_test` durante este handoff.

## 3. Fases cerradas: Asistencia

Asistencia 4B-3 está cerrada y no es la fase activa. Sus pendientes pasan a backlog.

- [IMPLEMENTADO Y CERRADO 4B-3A, `aea9c32`] Motor común de dominio para actividad, sesiones incompletas, situación horaria, jornadas pagables, doble turno, tarifa efectiva versionada y total provisional; calendario personal reutiliza la proyección.
- [IMPLEMENTADO, MIGRADO Y CERRADO 4B-3B, `aea9c32`] SALIDA administrativa transaccional/auditable, decisiones finales de incidencias y tarifas globales/individuales append-only. Migración `20260902_09` aplicada realmente a `boliklor_ot`.
- [IMPLEMENTADO Y CERRADO 4B-3C, `72534f5`] Supervisión ADMIN/JEFATURA bajo `/asistencia/supervision`, búsqueda, período, paginación, resumen, calendario/detalle individual y acciones auditadas, con CSRF/RBAC y sin exponer coordenadas exactas.
- [IMPLEMENTADO Y CERRADO 4B-3D, `ef468ec`] Administración de tarifas solo ADMIN y XLSX conjunto/individual para ADMIN/JEFATURA, con paridad de proyección, neutralización de fórmulas y omisión de GPS.
- [CONFIRMADO CIERRE, `e4251dc`] Gate real posterior: backup/restore previamente ensayado, base en `20260902_09`, `alembic check` sin drift, smoke de lectura y 44/44 pruebas focalizadas. Históricamente también quedaron verdes la suite completa aislada 209/209, la regresión de Asistencia 116/116 y las pruebas PostgreSQL de locks/concurrencia 3/3.
- [BACKLOG ASISTENCIA] Política legal de retención/acceso GPS, fuente de planificación/horario esperado, offline/fraude, alertas, revisión completa de justificaciones, horas/días extra y remuneración definitiva. No reabrir sin decisión expresa.

## 4. Fase activa

**INVENTARIO MVP** es la continuidad activa. Este handoff no autoriza implementación. El primer gate es revisar dos inputs reales: el XLSX actualizado de Inventario y ejemplos reales de Guía de Despacho.

Arquitectura vigente relevante: aplicación FastAPI única, UI operativa Jinja2/static, rutas delgadas deseables, servicios para casos de uso, SQLAlchemy/PostgreSQL, Alembic lineal y autorización backend. Inventario es dueño conceptual de empresa operativa, unidades, productos, movimientos y stock; Identidad aporta el actor futuro de auditoría. Órdenes de trabajo es heredado y no debe ampliarse aquí.

## 5. Inventario existente y brechas

### Implementado

- [IMPLEMENTADO] `Empresa`: catálogo multiempresa con código/nombre únicos, estado activo y relaciones a productos/movimientos; seeds actuales `ALM` y `BOLIKLOR`, sin modelar un universo cerrado a esas dos empresas.
- [IMPLEMENTADO] `UnidadMedida`: código único, nombre, decimales permitidos y estado activo; siete unidades seed.
- [IMPLEMENTADO] `Producto`: empresa, SKU global único, nombre/descripción, unidades de stock/contenido/costo, factor de conversión positivo, stock mínimo no negativo, tipo/familia y estado. Alta manual e importación/corrección de catálogo desde XLSX legacy.
- [IMPLEMENTADO] `MovimientoInventario` y `DetalleMovimientoInventario`: cabecera por empresa/fecha/número, referencia/guía/destino/comuna/observaciones; líneas con cantidad positiva y snapshots de unidades/factor/costos. Tipos permitidos por DB: `RECEPCION`, `DESPACHO`, `DEVOLUCION`, `AJUSTE_INICIAL`, `AJUSTE_POSITIVO`, `AJUSTE_NEGATIVO`.
- [IMPLEMENTADO] Ledger técnico: el saldo se deriva sumando tipos positivos y restando tipos negativos; no existe una columna de saldo mutable como verdad paralela.
- [IMPLEMENTADO] Recepción: formulario/carrito, validación de empresa/producto/unidades/decimales, snapshots de costo, número secuencial y commit/rollback atómico.
- [IMPLEMENTADO] Historial y detalle de movimientos; filtros combinables por empresa, tipo, fechas, documento/referencia/guía/SKU.
- [IMPLEMENTADO] Stock por empresa para BOLIKLOR y ALM, filtros por búsqueda/familia/estado/reposición/rango, inicialización de solo lectura y costo agregado. Dashboard muestra métricas de stock y últimos movimientos.
- [IMPLEMENTADO] Acceso global actual `INVENTARIO_ACCESS`; por la matriz vigente ADMIN tiene acceso y JEFATURA/TRABAJADOR no lo reciben. La seguridad depende de autorización backend, no del menú.

### Parcial o transitorio

- [PARCIAL] Fuente de stock: si existe algún `AJUSTE_INICIAL`, todo el sistema cambia a `MODO_OPERATIVO`; mientras no exista, el stock mostrado se lee del XLSX legacy y el ledger se mantiene separado. La base real sigue en transición.
- [PARCIAL] Costos: recepción calcula costo por presentación y valor de línea. La consulta actual obtiene un promedio de entradas positivas y valoriza stock positivo; no implementa todavía el costo promedio ponderado móvil por secuencia ni fija el costo histórico de cada despacho.
- [PARCIAL] Inmutabilidad: no hay rutas actuales de edición/eliminación de movimientos, pero tampoco existe todavía el flujo integral de confirmación/corrección compensatoria ni auditoría de actor que materialice la regla aprobada.
- [PARCIAL] Referencia de guía: existe `guia_despacho` como texto genérico, pero el contrato oficial SII aún no está definido con ejemplos reales.

### Previsto por estructura, pero no implementado operacionalmente

- [PREVISTO] La DB admite despacho, devolución y ajustes positivos/negativos, y el cálculo técnico conoce sus signos.
- [PENDIENTE] No existen creación/confirmación operacional de despachos, devoluciones o ajustes; control transaccional/concurrente de stock negativo; bodegas; relación devolución-despacho; motivos estructurados; actor/auditoría; permisos granulares; exportaciones de Inventario; “Detalles y trabajos”; PDF; ni contrato documental completo de Guía de Despacho.
- [PENDIENTE] No existen lotes, vencimientos, FIFO o FEFO; su ausencia es ahora una exclusión aprobada del MVP, no una decisión abierta inmediata.

## 6. Decisiones funcionales aprobadas para continuidad

1. [CONFIRMADO] **Fuente de verdad:** PostgreSQL + ledger será la única fuente operacional final. Excel queda para cutover controlado, conciliación, exportación, análisis e interoperabilidad. El archivo ya revisado puede estar desactualizado; revisar el XLSX actualizado antes de cutover. No ejecutar cutover todavía.
2. [CONFIRMADO] **Bodegas:** arquitectura `EMPRESA → BODEGA → STOCK/PRODUCTOS`; una o pocas bodegas iniciales por empresa, extensible a empresas futuras. ALM y BOLIKLOR no agotan el modelo.
3. [CONFIRMADO] **Stock negativo prohibido:** ningún despacho o ajuste negativo confirmado puede dejar saldo menor que cero; confirmación atómica y segura ante concurrencia.
4. [CONFIRMADO] **Movimientos confirmados inmutables:** no editar ni eliminar; corregir con movimientos compensatorios auditables.
5. [CONFIRMADO] **Despachos y Guía SII:** Boliklor no reemplaza el folio oficial; debe persistir referencia estructurada. Una futura carga PDF/imagen puede extraer y prellenar, siempre con revisión humana; no incluir OCR/extracción en la primera subfase ni confirmar automáticamente.
6. [CONFIRMADO] **Ajustes:** `AJUSTE_POSITIVO` y `AJUSTE_NEGATIVO` con motivo estructurado, actor, timestamp, comentario/referencia y trazabilidad; permiso previsto `INVENTARIO_AJUSTAR`.
7. [CONFIRMADO] **Devoluciones:** movimiento propio, auditable y relacionable con el despacho original; debe permitir `DESPACHADO - DEVUELTO = SALIDA/CONSUMO NETO`.
8. [CONFIRMADO] **Costos:** costo promedio ponderado móvil. Cada despacho conserva el costo histórico aplicado al confirmarse; movimientos históricos no se recalculan con costos nuevos.
9. [CONFIRMADO] **Exclusión de lotes:** no implementar lotes, vencimientos, FIFO ni FEFO en el Inventario MVP actual.
10. [CONFIRMADO] **Roles/permisos:** no crear rol `BODEGA`. Mantener ADMIN/JEFATURA/TRABAJADOR y evolucionar a `INVENTARIO_VER`, `INVENTARIO_EXPORTAR`, `INVENTARIO_RECIBIR`, `INVENTARIO_DESPACHAR`, `INVENTARIO_AJUSTAR`, `INVENTARIO_VER_COSTOS`, `INVENTARIO_AUDITAR`. No asumir que JEFATURA posee todos.
11. [CONFIRMADO] **Detalles y trabajos:** consulta express multi-producto con búsqueda/filtros/selección temporal, stock vigente, quitar/limpiar y exportar. Nunca reserva, despacha, persiste listas, crea movimientos ni cambia stock/costos/ajustes.
12. [CONFIRMADO] **Exportaciones:** prever XLSX/PDF para inventario completo/filtrado, recepciones, despachos, devoluciones, ajustes, movimientos, historial de producto y Detalles y trabajos. Reutilizar la misma consulta/proyección del portal; no duplicar reglas de negocio en Excel.
13. [CONFIRMADO] **Preparación BI:** persistir datos estructurados para futura analítica de stock, valorización, flujos, consumo neto, producto/empresa/bodega, costos, ajustes, actor, destinos, documentos y relación futura con OT. Power BI, data warehouse, ETL, cubos y API analítica quedan fuera del MVP.

## 7. Exclusiones y prohibiciones actuales

- No implementar todavía Inventario MVP-A, Bodega, permisos, despachos, devoluciones, ajustes, Detalles y trabajos, exportaciones ni OCR.
- No crear ni ejecutar migraciones; no importar/cortar Excel; no modificar stock, movimientos, configuración ni datos reales.
- No modificar `boliklor_ot` ni `boliklor_ot_test` sin un gate y autorización explícitos.
- No extender Órdenes de trabajo, desplegar, hacer `git add`, commit o push como parte de este handoff.

## 8. Próximos inputs necesarios

1. [PENDIENTE] **XLSX ORIGINAL actualizado** del responsable de Inventario. Analizar hojas, columnas, fórmulas, productos, empresas, stock, movimientos, recepciones, despachos, devoluciones, costos, reglas implícitas y diferencias con PostgreSQL. El usuario no necesita convertirlo a Markdown. Después documentar `docs/product/inventory/legacy-inventory-source.md`: estructura, reglas, mapeo Excel → PostgreSQL, datos migrables/no migrables, inconsistencias, conciliación y cutover.
2. [PENDIENTE] **Ejemplos reales de Guía de Despacho** (imágenes/PDF/documentos) para cerrar campos, referencias y contrato estructurado del despacho.

## 9. Riesgos y documentación obsoleta

- [RIESGO ALTO] El stock operativo visible depende hoy de un Excel legacy potencialmente desactualizado; el único movimiento real es una recepción y no debe confundirse con el saldo total.
- [RIESGO ALTO] El cálculo de costo actual no satisface aún el promedio ponderado móvil ni costo histórico de salida.
- [RIESGO ALTO] Despachos/ajustes negativos aún no tienen confirmación concurrente ni prohibición operacional de saldo negativo.
- [RIESGO MEDIO] No hay bodega ni actor/auditoría en el ledger actual; el modelo debe evolucionar mediante una nueva migración futura, nunca editando historial.
- [RIESGO MEDIO] `INVENTARIO_ACCESS` es demasiado amplio para la matriz granular aprobada; recepción y otras mutaciones de Inventario deberán revisar CSRF además de RBAC.
- [DEUDA_TECNICA DOCUMENTAL] `README.md` y partes de `docs/product/attendance/`, `docs/architecture/database.md`, `docs/architecture/system-overview.md` todavía presentan elementos cerrados de 4B-3 como futuros/en árbol y una cantidad anterior de revisiones/tablas. `docs/decisions/ADR-005-inventory-stock-ledger.md` y `docs/product/inventory/open-questions.md` dejan costo, stock negativo y lotes como abiertos; las decisiones de este handoff los reemplazan para la continuidad. No se editaron esos archivos para mantener este cierre limitado a `CURRENT.md`; deben alinearse antes o junto al diseño aprobado de MVP-A.

## 10. Próximo paso exacto y gate previo a implementación

**PRIMERA TAREA EN LA NUEVA VENTANA:** no generar código ni Prompt Maestro MVP-A. Recibir y revisar primero (A) el XLSX actualizado de Inventario y (B) ejemplos reales de Guía de Despacho.

Después, y todavía sin implementar: (1) documentar la fuente legacy; (2) definir el mapeo Excel → PostgreSQL y conciliación/cutover; (3) cerrar el contrato estructurado de despacho; (4) comprobar si la evidencia obliga a cambiar alguna decisión; (5) alinear documentación/ADR; y solo entonces preparar el Prompt Maestro INVENTARIO MVP-A para aprobación humana.

El gate de implementación exige decisiones y contratos documentados, diseño de Bodega y migración nueva, estrategia segura para datos existentes/cutover/rollback, transacciones concurrentes que impidan stock negativo, inmutabilidad/compensación, costo promedio móvil, auditoría/CSRF/RBAC granular y plan de pruebas aisladas. Ninguna migración ni escritura sobre base real queda autorizada por este documento.
