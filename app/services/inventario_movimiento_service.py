import logging
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import Sequence, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.schemas.movimiento_inventario import RecepcionCreate

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


def create_receipt(db: Session, data: RecepcionCreate) -> MovimientoInventario:
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


def list_movements(db: Session) -> list[MovimientoInventario]:
    query = select(MovimientoInventario).options(
        joinedload(MovimientoInventario.empresa), selectinload(MovimientoInventario.detalles)
    ).order_by(MovimientoInventario.created_at.desc(), MovimientoInventario.id.desc())
    return list(db.scalars(query).all())


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
