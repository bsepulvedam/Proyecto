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

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.empresa import Empresa
from app.models.idempotencia_bot import ClaveIdempotenciaBot
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.schemas.bot_inventario import OrigenMovimientoBot, RecepcionBotCreate
from app.schemas.movimiento_inventario import LineaRecepcionCreate, RecepcionCreate
from app.services.inventario_catalogo_service import listar_productos
from app.services.inventario_movimiento_service import InventoryMovementError, create_receipt, list_movements
from app.services.inventory_stock_service import inventory_stock_rows

router = APIRouter(prefix="/api/bot/inventario", tags=["bot-inventario"])
IDEMPOTENCY_HEADER = "Idempotency-Key"
_MAX_IDEMPOTENCY_KEY_LENGTH = 200


def _resolve_empresa(db: Session, empresa_codigo: str) -> Empresa:
    empresa = db.scalar(select(Empresa).where(Empresa.codigo == empresa_codigo.strip().upper()))
    if empresa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada.")
    return empresa


def _product_dict(product: Producto) -> dict:
    return {
        "producto_id": product.id,
        "sku": product.sku,
        "nombre": product.nombre,
        "empresa_codigo": product.empresa.codigo,
        "unidad_stock": product.unidad_stock.codigo,
        "permite_decimales": product.unidad_stock.permite_decimales,
        "factor_conversion": str(product.factor_conversion),
        "unidad_contenido": product.unidad_contenido.codigo if product.unidad_contenido else None,
        "unidad_costo": product.unidad_costo.codigo if product.unidad_costo else None,
        "stock_minimo": str(product.stock_minimo),
        "activo": product.activo,
    }


def _movement_dict(movement: MovimientoInventario) -> dict:
    return {
        "movimiento_id": movement.id,
        "numero_documento": movement.numero_documento,
        "tipo": movement.tipo,
        "empresa_codigo": movement.empresa.codigo,
        "fecha": movement.fecha.isoformat(),
        "guia_despacho": movement.guia_despacho,
        "referencia": movement.referencia,
        "observaciones": movement.observaciones,
        "origen": movement.origen,
        "actor_referencia": movement.actor_referencia,
        "valor_total": str(movement.valor_total),
        "lineas": [
            {
                "sku": linea.producto.sku,
                "cantidad_presentaciones": str(linea.cantidad_presentaciones),
                "unidad_presentacion": linea.unidad_presentacion_snapshot,
                "costo_unitario": str(linea.costo_unitario) if linea.costo_unitario is not None else None,
                "valor_total": str(linea.valor_total) if linea.valor_total is not None else None,
            }
            for linea in movement.detalles
        ],
    }


@router.get("/productos")
def bot_list_products(
    q: str = Query("", max_length=100),
    empresa: str = Query("", max_length=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    products = listar_productos(db)
    company = empresa.strip().upper()
    if company:
        products = [product for product in products if product.empresa.codigo == company]
    term = q.strip().casefold()
    if term:
        products = [
            product for product in products
            if term in product.sku.casefold() or term in product.nombre.casefold()
        ]
    return [_product_dict(product) for product in products]


@router.get("/stock/{empresa_codigo}")
def bot_stock(empresa_codigo: str, db: Session = Depends(get_db)) -> dict:
    empresa = _resolve_empresa(db, empresa_codigo)
    mode, rows = inventory_stock_rows(db)
    company_rows = [row for row in rows if row.product.empresa_id == empresa.id]
    return {
        "empresa_codigo": empresa.codigo,
        "modo": mode,
        "productos": [
            {
                "sku": row.product.sku,
                "nombre": row.product.nombre,
                "ledger_stock": str(row.movement_stock),
                "legacy_stock": str(row.legacy_stock) if row.legacy_stock is not None else None,
                "stock_mostrado": str(row.displayed_stock),
            }
            for row in company_rows
        ],
    }


@router.get("/movimientos")
def bot_list_movements(
    empresa: str = Query("", max_length=50),
    tipo: str = Query("", max_length=30),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    q: str = Query("", max_length=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    empresa_id = _resolve_empresa(db, empresa).id if empresa.strip() else None
    movements = list_movements(db, empresa_id, tipo, fecha_desde, fecha_hasta, q)
    return [_movement_dict(movement) for movement in movements]


def _resolve_empresa_for_receipt(db: Session, empresa_codigo: str) -> Empresa:
    """Variante de ``_resolve_empresa`` para el POST: 422 (error de negocio de
    ``create_receipt``), no 404 -- el bot ya validó el código contra un GET
    previo; si llega aquí inválido es un dato de la recepción, no una ruta
    inexistente."""
    empresa = db.scalar(select(Empresa).where(Empresa.codigo == empresa_codigo.strip().upper()))
    if empresa is None:
        raise InventoryMovementError(f"Empresa '{empresa_codigo}' no encontrada.")
    return empresa


def _resolve_producto_ids(db: Session, skus: set[str]) -> dict[str, int]:
    productos = db.scalars(select(Producto).where(Producto.sku.in_(skus))).all()
    resolved = {producto.sku: producto.id for producto in productos}
    missing = skus - resolved.keys()
    if missing:
        raise InventoryMovementError(f"SKU no encontrado: {', '.join(sorted(missing))}.")
    return resolved


def _receipt_response(movement: MovimientoInventario, creado: bool) -> dict:
    return {
        "movimiento_id": movement.id,
        "numero_documento": movement.numero_documento,
        "valor_total": str(movement.valor_total),
        "creado": creado,
    }


@router.post("/recepciones", status_code=status.HTTP_201_CREATED)
def bot_create_receipt(
    payload: RecepcionBotCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    db: Session = Depends(get_db),
) -> dict:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Header Idempotency-Key es obligatorio.")
    idempotency_key = idempotency_key.strip()
    if len(idempotency_key) > _MAX_IDEMPOTENCY_KEY_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key excede el largo máximo (200).")

    existing = db.scalar(select(ClaveIdempotenciaBot).where(ClaveIdempotenciaBot.clave == idempotency_key))
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _receipt_response(existing.movimiento, creado=False)

    try:
        empresa = _resolve_empresa_for_receipt(db, payload.empresa_codigo)
        producto_ids = _resolve_producto_ids(db, {linea.sku for linea in payload.lineas})
        data = RecepcionCreate(
            empresa_id=empresa.id, fecha=payload.fecha,
            guia_despacho=payload.guia_despacho, referencia=payload.referencia,
            observaciones=payload.observaciones,
            lineas=[
                LineaRecepcionCreate(
                    producto_id=producto_ids[linea.sku],
                    cantidad_presentaciones=linea.cantidad_presentaciones,
                    costo_unitario=linea.costo_unitario,
                    observacion_linea=linea.observacion_linea,
                )
                for linea in payload.lineas
            ],
        )
        movement = create_receipt(
            db, data,
            origen_bot=OrigenMovimientoBot(origen="BOT_TELEGRAM", actor_referencia=payload.solicitado_por),
        )
    except InventoryMovementError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    try:
        db.add(ClaveIdempotenciaBot(clave=idempotency_key, movimiento_id=movement.id))
        db.commit()
    except IntegrityError:
        # Reintento concurrente de N8N: otra request ya registró esta misma
        # clave entre nuestro SELECT y este INSERT. El movimiento ya se creó
        # (commit de create_receipt ya ocurrió) -- no se puede deshacer, así
        # que se devuelve como si fuera el hit de idempotencia normal, no
        # como error, para no dejar un movimiento huérfano sin registrar.
        # DEUDA_TECNICA: el movimiento recién creado queda huérfano (sin
        # clave apuntándolo) en vez de descartarse -- aceptado para Fase 1.
        db.rollback()
        existing = db.scalar(select(ClaveIdempotenciaBot).where(ClaveIdempotenciaBot.clave == idempotency_key))
        response.status_code = status.HTTP_200_OK
        return _receipt_response(existing.movimiento, creado=False)

    return _receipt_response(movement, creado=True)
