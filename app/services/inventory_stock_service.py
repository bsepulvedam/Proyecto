import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.services.inventario_catalogo_service import listar_productos, listar_unidades
from app.services.inventario_movimiento_service import calculate_stock_from_movements, calculate_weighted_average_cost
from app.services.product_import_correction_service import analyze_product_corrections
from app.services.product_import_service import ProductImportError, default_source_path


MODE_TRANSITION = "MODO_TRANSICION"
MODE_OPERATIONAL = "MODO_OPERATIVO"


@dataclass(frozen=True)
class InventoryStockRow:
    product: Producto
    legacy_stock: Decimal | None
    movement_stock: Decimal
    displayed_stock: Decimal
    mode: str

    @property
    def stock_state(self) -> str:
        return "EN STOCK" if self.displayed_stock > 0 else "SIN STOCK"

    @property
    def requires_restock(self) -> bool:
        return self.product.stock_minimo is not None and self.displayed_stock <= self.product.stock_minimo


def inventory_mode(db: Session) -> str:
    opened = db.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.tipo == "AJUSTE_INICIAL"))
    return MODE_OPERATIONAL if opened else MODE_TRANSITION


def _legacy_values(db: Session, products: list[Producto]) -> dict[str, Decimal]:
    configured = os.getenv("PRODUCT_IMPORT_FILE")
    source = Path(configured) if configured else default_source_path()
    try:
        report = analyze_product_corrections(source, products, listar_unidades(db))
    except (ProductImportError, OSError):
        return {}
    return {row.sku: row.stock_actual for row in report.rows}


def inventory_stock_rows(db: Session) -> tuple[str, list[InventoryStockRow]]:
    products = listar_productos(db)
    mode = inventory_mode(db)
    movement_values = calculate_stock_from_movements(db)
    legacy_values = _legacy_values(db, products) if mode == MODE_TRANSITION else {}
    rows = []
    for product in products:
        movement_stock = movement_values.get((product.empresa_id, product.id), Decimal("0"))
        legacy_stock = legacy_values.get(product.sku)
        displayed = (legacy_stock if legacy_stock is not None else Decimal("0")) if mode == MODE_TRANSITION else movement_stock
        rows.append(InventoryStockRow(product, legacy_stock, movement_stock, displayed, mode))
    return mode, rows


def transactional_inventory_values(db: Session) -> dict[str, Decimal]:
    stocks = calculate_stock_from_movements(db)
    averages = calculate_weighted_average_cost(db)
    products = {product.id: product for product in listar_productos(db)}
    totals = {"BOLIKLOR": Decimal("0"), "ALM": Decimal("0")}
    for key, stock in stocks.items():
        company_id, product_id = key
        product = products.get(product_id)
        if product and stock > 0:
            totals[product.empresa.codigo] = totals.get(product.empresa.codigo, Decimal("0")) + stock * averages.get((company_id, product_id), Decimal("0"))
    totals["TOTAL"] = sum(totals.values(), Decimal("0"))
    return totals
