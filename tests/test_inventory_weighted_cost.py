import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.empresa import Empresa
from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.movimiento_inventario import (
    AjusteCreate, DespachoCreate, DevolucionCreate, LineaAjusteCreate, LineaDespachoCreate,
    LineaDevolucionCreate, LineaRecepcionCreate, RecepcionCreate,
)
from app.services.inventario_movimiento_service import (
    calculate_weighted_average_cost, create_adjustment, create_dispatch, create_receipt, create_return,
)


class InventoryWeightedCostTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[
            Empresa.__table__, UnidadMedida.__table__, Producto.__table__,
            MovimientoInventario.__table__, DetalleMovimientoInventario.__table__,
        ])
        self.db = Session(self.engine)
        bol = Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")
        alm = Empresa(codigo="ALM", nombre="ALM")
        masv = Empresa(codigo="MASV", nombre="Mas Vial")
        tineta = UnidadMedida(codigo="TINETA", nombre="Tineta", permite_decimales=False)
        self.db.add_all([bol, alm, masv, tineta]); self.db.flush()
        self.bol_id, self.alm_id, self.masv_id = bol.id, alm.id, masv.id
        self.bol1 = Producto(empresa_id=bol.id, sku="BOL-1", nombre="PINTURA ACRILICA", unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=10)
        self.alm1 = Producto(empresa_id=alm.id, sku="ALM-1", nombre="PRODUCTO ALM", unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=1)
        self.masv1 = Producto(empresa_id=masv.id, sku="MASV-1", nombre="PRODUCTO MASV", unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=1)
        self.db.add_all([self.bol1, self.alm1, self.masv1]); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def receive(self, product, quantity, cost, fecha=date(2026, 9, 1)):
        create_receipt(self.db, RecepcionCreate(
            empresa_id=product.empresa_id, fecha=fecha,
            lineas=[LineaRecepcionCreate(producto_id=product.id, cantidad_presentaciones=quantity, costo_unitario=cost)],
        ))

    def dispatch(self, product, quantity, fecha=date(2026, 9, 2)):
        create_dispatch(self.db, DespachoCreate(
            empresa_id=product.empresa_id, fecha=fecha,
            lineas=[LineaDespachoCreate(producto_id=product.id, cantidad_presentaciones=quantity)],
        ))

    def do_return(self, product, quantity, fecha=date(2026, 9, 2)):
        create_return(self.db, DevolucionCreate(
            empresa_id=product.empresa_id, fecha=fecha,
            lineas=[LineaDevolucionCreate(producto_id=product.id, cantidad_presentaciones=quantity)],
        ))

    def adjust(self, product, tipo_ajuste, quantity, fecha=date(2026, 9, 2), motivo="Corrección de conteo físico"):
        create_adjustment(self.db, AjusteCreate(
            empresa_id=product.empresa_id, fecha=fecha, tipo_ajuste=tipo_ajuste, motivo=motivo,
            lineas=[LineaAjusteCreate(producto_id=product.id, cantidad_presentaciones=quantity)],
        ))

    def test_single_receipt_average_equals_its_cost(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("100"))

    def test_two_receipts_at_different_costs_produce_weighted_average(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 1))
        self.receive(self.bol1, Decimal("10"), Decimal("200"), fecha=date(2026, 9, 2))
        averages = calculate_weighted_average_cost(self.db)
        # (10*100 + 10*200) / 20 = 150
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("150"))

    def test_dispatch_consumes_at_current_average_without_changing_it(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 1))
        self.dispatch(self.bol1, Decimal("4"), fecha=date(2026, 9, 2))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("100"))

    def test_return_without_known_cost_does_not_dilute_average(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 1))
        self.do_return(self.bol1, Decimal("5"), fecha=date(2026, 9, 2))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("100"))

    def test_negative_adjustment_consumes_at_current_average_without_changing_it(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 1))
        self.adjust(self.bol1, "AJUSTE_NEGATIVO", Decimal("3"), fecha=date(2026, 9, 2))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("100"))

    def test_positive_adjustment_without_known_cost_does_not_dilute_average(self):
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 1))
        self.adjust(self.bol1, "AJUSTE_POSITIVO", Decimal("5"), fecha=date(2026, 9, 2))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("100"))

    def test_alm_and_masv_always_return_fixed_cost_of_one(self):
        # costo_unitario=5 a propósito: la función debe forzar 1 igual,
        # sin depender de que el dato de entrada respete ADR-012.
        self.receive(self.alm1, Decimal("10"), Decimal("5"), fecha=date(2026, 9, 1))
        self.dispatch(self.alm1, Decimal("2"), fecha=date(2026, 9, 2))
        self.receive(self.masv1, Decimal("7"), Decimal("5"), fecha=date(2026, 9, 1))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.alm_id, self.alm1.id)], Decimal("1"))
        self.assertEqual(averages[(self.masv_id, self.masv1.id)], Decimal("1"))

    def test_average_respects_chronological_order_not_insertion_order(self):
        # Orden de inserción: recepción (9/10) -> despacho (9/12) -> recepción (9/11).
        # Orden cronológico real: 9/10 -> 9/11 -> 9/12. Si el cálculo usara
        # el orden de inserción en vez de `fecha`, el resultado sería 166.67
        # en vez de 150 -- este test distingue ambos casos.
        self.receive(self.bol1, Decimal("10"), Decimal("100"), fecha=date(2026, 9, 10))
        self.dispatch(self.bol1, Decimal("5"), fecha=date(2026, 9, 12))
        self.receive(self.bol1, Decimal("10"), Decimal("200"), fecha=date(2026, 9, 11))
        averages = calculate_weighted_average_cost(self.db)
        self.assertEqual(averages[(self.bol_id, self.bol1.id)], Decimal("150"))


if __name__ == "__main__": unittest.main()
