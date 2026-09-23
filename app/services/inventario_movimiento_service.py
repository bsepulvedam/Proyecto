import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import Sequence, case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.schemas.bot_inventario import OrigenMovimientoBot
from app.schemas.movimiento_inventario import DespachoCreate, DevolucionCreate, RecepcionCreate

logger = logging.getLogger(__name__)
movimiento_sequence = Sequence("movimiento_inventario_seq")
POSITIVE_TYPES = {"RECEPCION", "DEVOLUCION", "AJUSTE_INICIAL", "AJUSTE_POSITIVO"}
NEGATIVE_TYPES = {"DESPACHO", "AJUSTE_NEGATIVO"}


class InventoryMovementError(ValueError):
    pass


def _next_movement_number(db: Session) -> str:
    if db.get_bind().dialect.name == "postgresql":
        number = db.execute(select(movimiento_sequence.next_value())).scalar_one()
    else:
        number = (db.scalar(select(func.max(MovimientoInventario.id))) or 0) + 1
    return f"MOV-{number:06d}"


def _load_products(db: Session, ids: set[int]) -> dict[int, Producto]:
    query = select(Producto).options(
        joinedload(Producto.empresa), joinedload(Producto.unidad_stock),
        joinedload(Producto.unidad_contenido), joinedload(Producto.unidad_costo),
    ).where(Producto.id.in_(ids))
    return {product.id: product for product in db.scalars(query).all()}


def calculate_receipt_cost(product: Producto, quantity: Decimal, unit_cost: Decimal) -> tuple[Decimal, Decimal]:
    if product.unidad_costo is None:
        raise InventoryMovementError("Este producto requiere definir su unidad de costo antes de recibirlo.")
    factor = product.factor_conversion
    cost_uses_content = (
        product.unidad_contenido is not None
        and product.unidad_costo.codigo == product.unidad_contenido.codigo
    )
    presentation_cost = unit_cost * factor if cost_uses_content else unit_cost
    return presentation_cost, (quantity * presentation_cost).quantize(Decimal("0.01"))


def create_receipt(
    db: Session, data: RecepcionCreate, origen_bot: OrigenMovimientoBot | None = None
) -> MovimientoInventario:
    """Crea una recepción. ``origen_bot`` es exclusivo de la API del bot.

    La web sigue llamando ``create_receipt(db, data)`` sin este tercer
    argumento -- por defecto equivale a ``OrigenMovimientoBot()``, es decir
    ``origen="ERP_WEB"`` y ``actor_referencia=None``, el mismo comportamiento
    que ya tenía este servicio antes de la Fase 1 de la API del bot.
    """
    origen_bot = origen_bot or OrigenMovimientoBot()
    try:
        if not data.lineas:
            raise InventoryMovementError("La recepción debe incluir al menos un producto.")
        ids = {line.producto_id for line in data.lineas}
        products = _load_products(db, ids)
        if len(products) != len(ids):
            raise InventoryMovementError("Uno o más productos ya no existen.")
        movement = MovimientoInventario(
            tipo="RECEPCION", empresa_id=data.empresa_id, fecha=data.fecha,
            numero_documento=_next_movement_number(db),
            guia_despacho=data.guia_despacho or None,
            referencia=data.referencia or None, observaciones=data.observaciones or None,
            origen=origen_bot.origen, actor_referencia=origen_bot.actor_referencia,
        )
        for index, line in enumerate(data.lineas, start=1):
            product = products[line.producto_id]
            if product.empresa_id != data.empresa_id:
                raise InventoryMovementError(f"La línea {index} pertenece a otra empresa.")
            quantity = line.cantidad_presentaciones
            if not product.unidad_stock.permite_decimales and quantity != quantity.to_integral_value():
                raise InventoryMovementError(f"{product.sku} no permite cantidades decimales en {product.unidad_stock.codigo}.")
            presentation_cost, total = calculate_receipt_cost(product, quantity, line.costo_unitario)
            movement.detalles.append(DetalleMovimientoInventario(
                producto_id=product.id, cantidad_presentaciones=quantity,
                unidad_presentacion_snapshot=product.unidad_stock.codigo,
                factor_conversion_snapshot=product.factor_conversion,
                unidad_contenido_snapshot=product.unidad_contenido.codigo if product.unidad_contenido else None,
                unidad_costo_snapshot=product.unidad_costo.codigo if product.unidad_costo else None,
                costo_unitario=line.costo_unitario, costo_presentacion=presentation_cost,
                valor_total=total, observacion_linea=line.observacion_linea or None,
            ))
        db.add(movement)
        db.commit()
        return get_movement(db, movement.id) or movement
    except InventoryMovementError as exc:
        db.rollback()
        logger.warning("Recepción rechazada: %s", exc)
        raise
    except Exception:
        db.rollback()
        logger.exception("No fue posible crear la recepción")
        raise


def _stock_disponible(db: Session, empresa_id: int, producto_ids: set[int]) -> dict[int, Decimal]:
    """Stock actual por producto, acotado a ``producto_ids`` (agregación SQL).

    A diferencia de ``calculate_stock_from_movements`` (que recorre todo el
    ledger para construir el stock de todas las empresas/productos), esta
    consulta solo agrega lo necesario para validar un despacho puntual.
    """
    if not producto_ids:
        return {}
    sign = case(
        (MovimientoInventario.tipo.in_(POSITIVE_TYPES), 1),
        (MovimientoInventario.tipo.in_(NEGATIVE_TYPES), -1),
        else_=0,
    )
    query = (
        select(DetalleMovimientoInventario.producto_id, func.sum(sign * DetalleMovimientoInventario.cantidad_presentaciones))
        .join(MovimientoInventario, MovimientoInventario.id == DetalleMovimientoInventario.movimiento_id)
        .where(MovimientoInventario.empresa_id == empresa_id, DetalleMovimientoInventario.producto_id.in_(producto_ids))
        .group_by(DetalleMovimientoInventario.producto_id)
    )
    return {producto_id: total or Decimal("0") for producto_id, total in db.execute(query).all()}


def _lock_products_for_dispatch(db: Session, empresa_id: int, producto_ids: set[int]) -> None:
    """Serializa despachos concurrentes sobre el mismo (empresa, producto).

    No hay tabla de saldo mutable que bloquear con ``SELECT ... FOR UPDATE``
    (ADR-005: el ledger de movimientos es la fuente de verdad, un saldo
    mutable único fue rechazado explícitamente como alternativa). En su
    lugar se usa un advisory lock de Postgres por producto, liberado
    automáticamente al terminar la transacción (commit o rollback). En
    SQLite (tests) no hay lock real -- tampoco hay concurrencia real ahí.
    """
    if db.get_bind().dialect.name != "postgresql":
        return
    for producto_id in sorted(producto_ids):
        db.execute(select(func.pg_advisory_xact_lock(empresa_id, producto_id)))


def create_dispatch(
    db: Session, data: DespachoCreate, origen_bot: OrigenMovimientoBot | None = None
) -> MovimientoInventario:
    """Crea un despacho. Rechaza cualquier línea que deje saldo negativo.

    ``origen_bot`` sigue el mismo contrato que ``create_receipt``: por
    defecto ``OrigenMovimientoBot()`` (``origen="ERP_WEB"``), pensado para
    que la futura API del bot (Fase 4 del roadmap) reutilice este mismo
    servicio sin duplicar lógica de negocio.
    """
    origen_bot = origen_bot or OrigenMovimientoBot()
    try:
        if not data.lineas:
            raise InventoryMovementError("El despacho debe incluir al menos un producto.")
        ids = {line.producto_id for line in data.lineas}
        products = _load_products(db, ids)
        if len(products) != len(ids):
            raise InventoryMovementError("Uno o más productos ya no existen.")
        for index, line in enumerate(data.lineas, start=1):
            if products[line.producto_id].empresa_id != data.empresa_id:
                raise InventoryMovementError(f"La línea {index} pertenece a otra empresa.")

        _lock_products_for_dispatch(db, data.empresa_id, ids)
        available = _stock_disponible(db, data.empresa_id, ids)
        for index, line in enumerate(data.lineas, start=1):
            product = products[line.producto_id]
            quantity = line.cantidad_presentaciones
            if not product.unidad_stock.permite_decimales and quantity != quantity.to_integral_value():
                raise InventoryMovementError(f"{product.sku} no permite cantidades decimales en {product.unidad_stock.codigo}.")
            remaining = available.get(product.id, Decimal("0")) - quantity
            if remaining < 0:
                raise InventoryMovementError(f"{product.sku} no tiene stock suficiente para despachar {quantity}.")
            available[product.id] = remaining

        movement = MovimientoInventario(
            tipo="DESPACHO", empresa_id=data.empresa_id, fecha=data.fecha,
            numero_documento=_next_movement_number(db),
            guia_despacho=data.guia_despacho or None,
            entregado_a=data.entregado_a or None, comuna=data.comuna or None,
            referencia=data.referencia or None, observaciones=data.observaciones or None,
            origen=origen_bot.origen, actor_referencia=origen_bot.actor_referencia,
        )
        for line in data.lineas:
            product = products[line.producto_id]
            movement.detalles.append(DetalleMovimientoInventario(
                producto_id=product.id, cantidad_presentaciones=line.cantidad_presentaciones,
                unidad_presentacion_snapshot=product.unidad_stock.codigo,
                factor_conversion_snapshot=product.factor_conversion,
                unidad_contenido_snapshot=product.unidad_contenido.codigo if product.unidad_contenido else None,
                unidad_costo_snapshot=product.unidad_costo.codigo if product.unidad_costo else None,
                observacion_linea=line.observacion_linea or None,
            ))
        db.add(movement)
        db.commit()
        return get_movement(db, movement.id) or movement
    except InventoryMovementError as exc:
        db.rollback()
        logger.warning("Despacho rechazado: %s", exc)
        raise
    except Exception:
        db.rollback()
        logger.exception("No fue posible crear el despacho")
        raise


def create_return(
    db: Session, data: DevolucionCreate, origen_bot: OrigenMovimientoBot | None = None
) -> MovimientoInventario:
    """Crea una devolución. Suma stock -- no valida stock disponible.

    Simétrico a ``create_dispatch`` pero sin ``_lock_products_for_dispatch``
    ni ``_stock_disponible``: una devolución no puede dejar saldo negativo,
    así que no hay nada que bloquear ni validar antes de escribir. El
    contrato de ``origen_bot`` es el mismo que en recepción/despacho.
    """
    origen_bot = origen_bot or OrigenMovimientoBot()
    try:
        if not data.lineas:
            raise InventoryMovementError("La devolución debe incluir al menos un producto.")
        ids = {line.producto_id for line in data.lineas}
        products = _load_products(db, ids)
        if len(products) != len(ids):
            raise InventoryMovementError("Uno o más productos ya no existen.")
        movement = MovimientoInventario(
            tipo="DEVOLUCION", empresa_id=data.empresa_id, fecha=data.fecha,
            numero_documento=_next_movement_number(db),
            guia_despacho=data.guia_despacho or None,
            referencia=data.referencia or None, observaciones=data.observaciones or None,
            origen=origen_bot.origen, actor_referencia=origen_bot.actor_referencia,
        )
        for index, line in enumerate(data.lineas, start=1):
            product = products[line.producto_id]
            if product.empresa_id != data.empresa_id:
                raise InventoryMovementError(f"La línea {index} pertenece a otra empresa.")
            quantity = line.cantidad_presentaciones
            if not product.unidad_stock.permite_decimales and quantity != quantity.to_integral_value():
                raise InventoryMovementError(f"{product.sku} no permite cantidades decimales en {product.unidad_stock.codigo}.")
            movement.detalles.append(DetalleMovimientoInventario(
                producto_id=product.id, cantidad_presentaciones=quantity,
                unidad_presentacion_snapshot=product.unidad_stock.codigo,
                factor_conversion_snapshot=product.factor_conversion,
                unidad_contenido_snapshot=product.unidad_contenido.codigo if product.unidad_contenido else None,
                unidad_costo_snapshot=product.unidad_costo.codigo if product.unidad_costo else None,
                observacion_linea=line.observacion_linea or None,
            ))
        db.add(movement)
        db.commit()
        return get_movement(db, movement.id) or movement
    except InventoryMovementError as exc:
        db.rollback()
        logger.warning("Devolución rechazada: %s", exc)
        raise
    except Exception:
        db.rollback()
        logger.exception("No fue posible crear la devolución")
        raise


def list_movements(db: Session, empresa_id: int | None = None, tipo: str = "", fecha_desde: date | None = None, fecha_hasta: date | None = None, search: str = "") -> list[MovimientoInventario]:
    query = select(MovimientoInventario).options(
        joinedload(MovimientoInventario.empresa),
        selectinload(MovimientoInventario.detalles).joinedload(DetalleMovimientoInventario.producto),
    )
    if empresa_id is not None:
        query = query.where(MovimientoInventario.empresa_id == empresa_id)
    if tipo:
        query = query.where(MovimientoInventario.tipo == tipo.upper())
    if fecha_desde is not None:
        query = query.where(MovimientoInventario.fecha >= fecha_desde)
    if fecha_hasta is not None:
        query = query.where(MovimientoInventario.fecha <= fecha_hasta)
    movements = list(db.scalars(query.order_by(MovimientoInventario.created_at.desc(), MovimientoInventario.id.desc())).all())
    term = search.strip().casefold()
    if not term:
        return movements
    return [movement for movement in movements if term in movement.numero_documento.casefold()
        or term in (movement.guia_despacho or "").casefold()
        or term in (movement.referencia or "").casefold()
        or any(term in line.producto.sku.casefold() for line in movement.detalles)]


def get_movement(db: Session, movement_id: int) -> MovimientoInventario | None:
    query = select(MovimientoInventario).options(
        joinedload(MovimientoInventario.empresa),
        selectinload(MovimientoInventario.detalles).joinedload(DetalleMovimientoInventario.producto),
    ).where(MovimientoInventario.id == movement_id)
    return db.scalar(query)


def calculate_stock_from_movements(db: Session) -> dict[tuple[int, int], Decimal]:
    stock = defaultdict(lambda: Decimal("0"))
    query = select(MovimientoInventario).options(selectinload(MovimientoInventario.detalles))
    for movement in db.scalars(query).all():
        sign = Decimal("1") if movement.tipo in POSITIVE_TYPES else Decimal("-1") if movement.tipo in NEGATIVE_TYPES else Decimal("0")
        for line in movement.detalles:
            stock[(movement.empresa_id, line.producto_id)] += sign * line.cantidad_presentaciones
    return dict(stock)


def calculate_weighted_average_cost(db: Session) -> dict[tuple[int, int], Decimal]:
    quantities, values = defaultdict(lambda: Decimal("0")), defaultdict(lambda: Decimal("0"))
    query = select(MovimientoInventario).options(selectinload(MovimientoInventario.detalles))
    for movement in db.scalars(query).all():
        if movement.tipo not in POSITIVE_TYPES:
            continue
        for line in movement.detalles:
            key = (movement.empresa_id, line.producto_id)
            quantities[key] += line.cantidad_presentaciones
            values[key] += line.valor_total or Decimal("0")
    return {key: values[key] / quantity for key, quantity in quantities.items() if quantity > 0}
