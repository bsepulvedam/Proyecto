"""API de Inventario para el bot de Telegram (N8N/Gemini).

Contrato completo en ``docs/architecture/BOLIKLOR_BOT_API_DESIGN.md``.

Principio rector (§2 de ese documento): **cero lógica de negocio nueva**. Cada
endpoint de este módulo se limita a traducir el vocabulario del bot (SKU,
código de empresa) al vocabulario interno del ERP (ids) y delegar en los mismos
servicios que ya usa la interfaz web. Ninguna regla de stock, costo o
numeración se reimplementa aquí — es lo que evita que el ERP y el bot "vean
cosas distintas".

La autenticación se monta en ``app/main.py`` como dependencia del router
completo (``require_service_key``), no endpoint por endpoint, para que ninguna
ruta futura de este módulo pueda quedar expuesta por olvido.

Fase 1 (este trabajo): 3 consultas + recepciones. Los endpoints de
despacho/devolución/ajuste son Fase 4 del roadmap y están bloqueados hasta que
el ERP tenga esos flujos operacionales (§5 del diseño).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/bot/inventario", tags=["bot-inventario"])
