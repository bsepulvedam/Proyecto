import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.empresa import Empresa
from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.movimiento_inventario import LineaRecepcionCreate, RecepcionCreate
from app.services.inventario_movimiento_service import (
    InventoryMovementError, calculate_receipt_cost, calculate_stock_from_movements,
    create_receipt, get_movement, list_movements,
)
from app.api.productos import search_products


class InventoryMovementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[
            Empresa.__table__, UnidadMedida.__table__, Producto.__table__,
            MovimientoInventario.__table__, DetalleMovimientoInventario.__table__,
        ])
        self.db = Session(self.engine)
        bol = Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")
        alm = Empresa(codigo="ALM", nombre="ALM")
        tineta = UnidadMedida(codigo="TINETA", nombre="Tineta", permite_decimales=False)
        sack = UnidadMedida(codigo="SACO", nombre="Saco", permite_decimales=False)
        kg = UnidadMedida(codigo="KG", nombre="Kilogramo", permite_decimales=True)
        self.db.add_all([bol, alm, tineta, sack, kg]); self.db.flush()
        self.bol_id, self.alm_id = bol.id, alm.id
        self.bol1 = Producto(empresa_id=bol.id, sku="BOL-1", nombre="PINTURA ACRILICA", unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=10)
        self.bol8 = Producto(empresa_id=bol.id, sku="BOL-8", nombre="PINTURA TERMOPLASTICA", unidad_stock_id=sack.id, unidad_contenido_id=kg.id, factor_conversion=25, unidad_costo_id=kg.id, stock_minimo=80)
        self.alm1 = Producto(empresa_id=alm.id, sku="ALM-1", nombre="PRODUCTO ALM", unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=1)
        self.db.add_all([self.bol1, self.bol8, self.alm1]); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def receipt(self, lines):
        return RecepcionCreate(empresa_id=self.bol_id, fecha=date(2026, 8, 27), lineas=lines)

    def line(self, product, quantity, cost):
        return LineaRecepcionCreate(producto_id=product.id, cantidad_presentaciones=quantity, costo_unitario=cost)

    def test_bol1_single_line_calculation_and_snapshots(self):
        movement = create_receipt(self.db, self.receipt([self.line(self.bol1, 47, 42300)]))
        line = movement.detalles[0]
        self.assertEqual(movement.numero_documento, "MOV-000001")
        self.assertEqual(line.costo_presentacion, Decimal("42300.0000"))
        self.assertEqual(line.valor_total, Decimal("1988100.00"))
        self.assertEqual(line.unidad_presentacion_snapshot, "TINETA")

    def test_bol8_and_multiple_lines_calculation(self):
        movement = create_receipt(self.db, self.receipt([
            self.line(self.bol1, 47, 42300), self.line(self.bol8, 80, 880),
        ]))
        bol8 = next(line for line in movement.detalles if line.producto_id == self.bol8.id)
        self.assertEqual(bol8.costo_presentacion, Decimal("22000.0000"))
        self.assertEqual(bol8.valor_total, Decimal("1760000.00"))
        self.assertEqual(movement.valor_total, Decimal("3748100.00"))

    def test_empty_cart_is_rejected(self):
        data = RecepcionCreate.model_construct(empresa_id=self.bol_id, fecha=date.today(), lineas=[])
        with self.assertRaises(InventoryMovementError): create_receipt(self.db, data)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MovimientoInventario)), 0)

    def test_wrong_company_and_cross_company_product_are_rejected(self):
        with self.assertRaises(InventoryMovementError):
            create_receipt(self.db, self.receipt([self.line(self.alm1, 1, 100)]))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MovimientoInventario)), 0)

    def test_decimal_sack_is_rejected_and_rolls_back_valid_line(self):
        with self.assertRaises(InventoryMovementError):
            create_receipt(self.db, self.receipt([self.line(self.bol1, 1, 100), self.line(self.bol8, Decimal("2.5"), 880)]))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MovimientoInventario)), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(DetalleMovimientoInventario)), 0)

    def test_product_without_cost_unit_is_rejected(self):
        product = SimpleNamespace(unidad_costo=None, unidad_contenido=None, factor_conversion=Decimal("1"))
        with self.assertRaisesRegex(InventoryMovementError, "requiere definir"):
            calculate_receipt_cost(product, Decimal("1"), Decimal("100"))

    def test_history_detail_and_technical_stock(self):
        first = create_receipt(self.db, self.receipt([self.line(self.bol1, 2, 100)]))
        second = create_receipt(self.db, self.receipt([self.line(self.bol8, 3, 10)]))
        history = list_movements(self.db)
        self.assertEqual([item.id for item in history], [second.id, first.id])
        self.assertEqual(get_movement(self.db, first.id).detalles[0].producto.sku, "BOL-1")
        stock = calculate_stock_from_movements(self.db)
        self.assertEqual(stock[(self.bol_id, self.bol1.id)], Decimal("2.000"))
        self.assertEqual(stock[(self.bol_id, self.bol8.id)], Decimal("3.000"))

    def test_product_search_is_limited_to_selected_company(self):
        bol_results = search_products(q="PINTURA", empresa_id=self.bol_id, db=self.db)
        alm_results = search_products(q="PRODUCTO", empresa_id=self.alm_id, db=self.db)
        self.assertEqual({item["sku"] for item in bol_results}, {"BOL-1", "BOL-8"})
        self.assertEqual({item["sku"] for item in alm_results}, {"ALM-1"})


if __name__ == "__main__": unittest.main()
