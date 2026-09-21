# BOLIKLOR — Diseño de integración Bot de Telegram ↔ API del ERP (Inventario)

**Fecha:** 21 de septiembre de 2026
**Estado:** PROPUESTA — pendiente de aprobación antes de implementar. Nada de esto está construido todavía.
**Decisión base ya confirmada:** el bot llama directo a una API del ERP; Google Sheets deja de ser el registro final de inventario (ver `BOLIKLOR_TECHNICAL_AUDIT.md`, Addendum 2).
**Relación con el otro chat:** este documento define el **contrato** (qué expone el ERP). Cómo N8N consume ese contrato — nodos, prompts de Gemini, flujo de conversación en Telegram — se diseña en el otro chat. Aquí sólo construimos el lado del ERP.

---

## 1. Objetivo

Que el bot pueda, para el personal autorizado: consultar stock, consultar catálogo, registrar movimientos de inventario y consultar historial/devoluciones — sin pasar por Google Sheets, sin duplicar la lógica de negocio que el ERP ya tiene, y con trazabilidad de quién (o qué sistema) originó cada cambio.

## 2. Principio de diseño: cero lógica de negocio nueva

Cada endpoint que se exponga al bot debe llamar **exactamente** a los mismos servicios que ya usa la interfaz web (`inventario_movimiento_service.create_receipt`, `inventory_stock_service.inventory_stock_rows`, etc.). El bot no debe tener su propia copia de las reglas de cálculo de costo, stock o secuencias. Esto es lo que evita que ERP y bot "vean cosas distintas".

## 3. Gap crítico a resolver primero: el ledger no tiene "actor"

Verifiqué el modelo (`app/models/movimiento_inventario.py`): `MovimientoInventario` tiene `created_at`, pero **ningún campo de quién lo creó** — ni usuario, ni sistema de origen. Esto ya estaba señalado como pendiente en la auditoría (INV-004, "actor del ledger"), pero ahora se vuelve un requisito duro: sin esto, un movimiento creado por el bot es indistinguible de uno creado por Sofía desde el ERP.

**Recomendación:** antes de exponer cualquier endpoint al bot, agregar una migración pequeña y no destructiva:
```text
ALTER TABLE movimientos_inventario ADD COLUMN origen VARCHAR(30) NOT NULL DEFAULT 'ERP_WEB';
ALTER TABLE movimientos_inventario ADD COLUMN actor_referencia VARCHAR(200) NULL;
```
- `origen`: `'ERP_WEB'` | `'BOT_TELEGRAM'` — de dónde vino el movimiento.
- `actor_referencia`: texto libre con quién lo pidió (p. ej. `"Telegram: Juan Pérez (id 5839201)"`), hasta que exista un modelo formal de "usuarios de servicio" si algún día hace falta.

Es una migración de bajo riesgo (columna nueva con default, no toca datos existentes) y resuelve de paso parte de INV-004 que de todas formas estaba pendiente.

## 4. Autenticación: API key de servicio, no sesión de cookie

Confirmado en código: hoy sólo existe autenticación por sesión de cookie + CSRF (pensada para navegador). Se necesita un mecanismo aparte para el bot:

- Header `X-Service-Key: <token largo, generado una vez, guardado como variable de entorno en N8N>`.
- El token se valida contra un hash guardado en configuración del servidor (mismo patrón que ya usa Argon2/HMAC para sesiones — no reinventar el mecanismo de hashing).
- Alcance limitado: ese token **sólo** abre los endpoints de `/api/bot/inventario/*`, nada de administración, usuarios ni asistencia.
- No reemplaza RBAC humano — es un "rol de servicio" nuevo, separado de ADMIN/JEFATURA/TRABAJADOR.
- Sin esto, no se expone nada al bot. Es P0 antes de cualquier endpoint nuevo.

## 5. Superficie de API propuesta — por fases (respetando lo que hoy SÍ existe operacionalmente)

La auditoría ya dejó claro que Despacho/Devolución/Ajuste existen como **tipos** en el ledger pero sin flujo operacional de confirmación (INV-005) — no hay control de stock negativo ni de concurrencia todavía. Exponer esas acciones al bot antes de que el ERP mismo las tenga resueltas sería construir sobre una base a medio terminar. Por eso la superficie se divide en dos fases.

### Fase 1 — Implementable ahora (todo lo que el ERP ya sabe hacer)

| Método | Ruta propuesta | Reutiliza | Propósito |
| --- | --- | --- | --- |
| GET | `/api/bot/inventario/productos` | `inventario_catalogo_service.listar_productos` | Buscar producto por SKU/nombre/empresa (catálogo) |
| GET | `/api/bot/inventario/stock/{empresa_codigo}` | `inventory_stock_service.inventory_stock_rows` | Consultar stock actual por empresa (respeta el modo legacy/ledger vigente — importante: una vez resuelto INV-001, será una sola fuente consistente) |
| GET | `/api/bot/inventario/movimientos` | `inventario_movimiento_service` (listado/filtros) | Consultar historial de movimientos, incluyendo Devoluciones ya registradas |
| POST | `/api/bot/inventario/recepciones` | `inventario_movimiento_service.create_receipt` | Registrar una recepción — la única operación de **escritura** que el ERP ya soporta de punta a punta hoy |

### Fase 2 — Bloqueada hasta que el ERP tenga el flujo operacional (Fase 2 del Remediation Roadmap, INV-004/INV-005)

| Método | Ruta propuesta | Bloqueador |
| --- | --- | --- |
| POST | `/api/bot/inventario/despachos` | Requiere control concurrente de stock negativo, aún no diseñado |
| POST | `/api/bot/inventario/devoluciones` | Requiere flujo de confirmación operacional, aún no implementado |
| POST | `/api/bot/inventario/ajustes` | Requiere actor+motivo obligatorio y permisos granulares (INV-004) |

**No se recomienda saltarse esta secuencia.** Si negocio necesita despachos/devoluciones vía bot con urgencia, la respuesta correcta es adelantar la Fase 2 de Inventario en el ERP (ya priorizada P0 en el roadmap de la auditoría), no construir esa lógica sólo del lado del bot.

## 6. Idempotencia (evitar duplicados por reintentos de N8N)

N8N puede reintentar una llamada si hay timeout, aunque el ERP ya la haya procesado. Cada `POST` debe aceptar un header `Idempotency-Key` (puede ser el `message_id` de Telegram). El servicio guarda ese key junto al movimiento creado (puede vivir en `actor_referencia` o en una tabla pequeña de claves-ya-usadas) y, si llega dos veces la misma key, devuelve el movimiento ya creado en vez de duplicarlo.

## 7. Ejemplo de contrato — `POST /api/bot/inventario/recepciones`

**Request:**
```json
{
  "empresa_codigo": "BOLIKLOR",
  "fecha": "2026-09-21",
  "referencia": "Guía 4821",
  "lineas": [
    {"sku": "BOL-00123", "cantidad_presentaciones": 10, "costo_unitario": 3500}
  ],
  "solicitado_por": "Juan Pérez (Telegram id 5839201)"
}
```
Headers: `X-Service-Key: ***`, `Idempotency-Key: telegram-msg-88213`

**Response 201:**
```json
{
  "movimiento_id": 341,
  "numero_documento": "REC-000341",
  "estado": "confirmado",
  "valor_total": 35000
}
```
**Response 422:** mismos errores de validación que ya usa `create_receipt` (producto inexistente, empresa distinta, cantidad no permitida) — el bot recibe el mismo mensaje que hoy vería un usuario del ERP, sin traducción intermedia.

*(`sku` en vez de `producto_id` en el request: el bot conoce productos por SKU, no por ID interno — el endpoint resuelve el SKU a `producto_id` antes de llamar a `create_receipt`, sin cambiar el servicio interno.)*

## 8. Qué se hace en cada chat

**Aquí (ERP):** migración del campo `origen`/`actor_referencia`, mecanismo de API key, los 4 endpoints de Fase 1, tests de esos endpoints (incluyendo idempotencia y rechazo sin key válida).

**En el otro chat (N8N/bot):** reemplazar los nodos que hoy escriben en Google Sheets por llamadas HTTP a estos endpoints; decidir qué hace Gemini con las respuestas (formato de mensaje en Telegram); manejo de errores 422 hacia el usuario de Telegram.

## 9. Transición de Google Sheets — sin corte abrupto

No hace falta apagar Sheets de un día para otro:
1. Se construyen los endpoints de Fase 1 aquí, en paralelo a que N8N siga funcionando como hoy.
2. En el otro chat, se migran primero las **consultas** (leer stock/catálogo) de Sheets a la API — es el cambio de menor riesgo.
3. Luego se migra la **escritura** de recepciones.
4. Sheets puede seguir existiendo como bitácora de respaldo/lectura humana mientras se gana confianza en la API — pero deja de ser la fuente que el bot escribe primero.
5. Cuando el ERP tenga Fase 2 de Inventario (despacho/devolución/ajuste operacional), se repite el mismo patrón para esas acciones.

## 10. Preguntas abiertas para antes de implementar

1. ¿El "personal autorizado" que usará el bot para registrar recepciones son las mismas pocas personas que hoy tienen `INVENTARIO_ACCESS` en el ERP, o un grupo distinto que habría que dar de alta?
2. ¿El token de servicio (API key) es uno solo para todo el bot, o prefieres uno por persona autorizada (para que `actor_referencia` sea más preciso sin depender de que Gemini reporte bien el nombre)?
3. ¿Confirmas que las consultas de stock/catálogo (Fase 1, sólo lectura) pueden implementarse ya, en paralelo a que decidamos el detalle de recepciones?

---

## 11. Actualización tras revisar el Excel real (21-09-2026)

Confirmaciones que simplifican este diseño:
- **`actor_referencia` ya tiene fuente de datos clara:** la columna `Usuario / Origen` del Excel del bot mapea 1:1. No hay que inventar nada nuevo del lado del bot, sólo escribir ese valor en el campo nuevo de PostgreSQL.
- **`Idempotency-Key` ya existe conceptualmente:** el `ID Transacción` (`TX-0001`...) del bot puede usarse tal cual como esa clave.
- **Prerrequisito nuevo, antes de cualquier endpoint:** dar de alta la empresa `Mas Vial` (código sugerido `MASV`, igual que el prefijo de SKU real `MASV-*`) en el modelo `Empresa` de PostgreSQL — hoy sólo existen `BOLIKLOR`/`ALM`. Sin esto, cualquier movimiento de Mas Vial fallará al resolver `empresa_id`.
- **Costo fijo = 1 en ALM/Mas Vial:** confirmado en datos reales (100% de esos productos). Antes de sincronizar catálogo/costos, decidir si el ERP debe respetar ese mismo criterio (bodegas sin valorización real) o si se espera costeo real a futuro para esas dos empresas también.

**Sobre el stock negativo — no bloquea la Fase 1:** una recepción nunca puede dejar el stock en negativo (sólo suma), así que la Fase 1 de este diseño (consultas + recepciones) puede avanzar sin esperar la decisión de política de stock negativo. Esa decisión sí es bloqueante para la Fase 2 (despacho/devolución/ajuste), porque es exactamente ahí donde el ERP tendría que decidir si permite o rechaza un movimiento que deja el stock bajo cero. Ver `BOLIKLOR_TECHNICAL_AUDIT.md`, Addendum 3, pregunta de negocio #21.
