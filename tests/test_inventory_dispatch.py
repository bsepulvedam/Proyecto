import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.empresa import Empresa
from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.bot_inventario import OrigenMovimientoBot
from app.schemas.movimiento_inventario import DespachoCreate, LineaDespachoCreate, LineaRecepcionCreate, RecepcionCreate
from app.services.inventario_movimiento_service import (
    InventoryMovementError, calculate_stock_from_movements, create_dispatch, create_receipt,
)


class InventoryDispatchTests(unittest.TestCase):
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

    def receive(self, product, quantity, cost=Decimal("100")):
        create_receipt(self.db, RecepcionCreate(
            empresa_id=product.empresa_id, fecha=date(2026, 8, 27),
            lineas=[LineaRecepcionCreate(producto_id=product.id, cantidad_presentaciones=quantity, costo_unitario=cost)],
        ))

    def dispatch(self, lines, empresa_id=None):
        return create_dispatch(self.db, DespachoCreate(
            empresa_id=empresa_id or self.bol_id, fecha=date(2026, 8, 28), lineas=lines,
        ))

    def line(self, product, quantity):
        return LineaDespachoCreate(producto_id=product.id, cantidad_presentaciones=quantity)

    def test_dispatch_reduces_stock_and_gets_sequential_document_number(self):
        self.receive(self.bol1, 10)
        movement = self.dispatch([self.line(self.bol1, 4)])
        self.assertEqual(movement.tipo, "DESPACHO")
        self.assertEqual(movement.numero_documento, "MOV-000002")
        stock = calculate_stock_from_movements(self.db)
        self.assertEqual(stock[(self.bol_id, self.bol1.id)], Decimal("6.000"))

    def test_dispatch_leaving_negative_stock_is_rejected_and_rolled_back(self):
        self.receive(self.bol1, 5)
        with self.assertRaisesRegex(InventoryMovementError, "no tiene stock suficiente"):
            self.dispatch([self.line(self.bol1, 6)])
        stock = calculate_stock_from_movements(self.db)
        self.assertEqual(stock[(self.bol_id, self.bol1.id)], Decimal("5.000"))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.tipo == "DESPACHO")), 0)

    def test_dispatch_without_any_receipt_is_rejected(self):
        with self.assertRaises(InventoryMovementError):
            self.dispatch([self.line(self.bol1, 1)])

    def test_dispatch_partial_line_failure_rolls_back_whole_movement(self):
        self.receive(self.bol1, 10)
        self.receive(self.bol8, 5)
        with self.assertRaises(InventoryMovementError):
            self.dispatch([self.line(self.bol1, 2), self.line(self.bol8, 999)])
        stock = calculate_stock_from_movements(self.db)
        self.assertEqual(stock[(self.bol_id, self.bol1.id)], Decimal("10.000"))
        self.assertEqual(stock[(self.bol_id, self.bol8.id)], Decimal("5.000"))

    def test_dispatch_cross_company_product_is_rejected(self):
        self.receive(self.alm1, 10)
        with self.assertRaises(InventoryMovementError):
            self.dispatch([self.line(self.alm1, 1)], empresa_id=self.bol_id)

    def test_dispatch_decimal_quantity_rejected_when_unit_forbids_it(self):
        self.receive(self.bol8, 100)
        with self.assertRaises(InventoryMovementError):
            self.dispatch([self.line(self.bol8, Decimal("2.5"))])

    def test_dispatch_empty_cart_is_rejected(self):
        data = DespachoCreate.model_construct(empresa_id=self.bol_id, fecha=date.today(), lineas=[])
        with self.assertRaises(InventoryMovementError):
            create_dispatch(self.db, data)

    def test_dispatch_without_origen_bot_defaults_to_erp_web(self):
        self.receive(self.bol1, 10)
        movement = self.dispatch([self.line(self.bol1, 1)])
        self.assertEqual(movement.origen, "ERP_WEB")
        self.assertIsNone(movement.actor_referencia)

    def test_dispatch_accepts_bot_origin_and_actor(self):
        self.receive(self.bol1, 10)
        origen_bot = OrigenMovimientoBot(origen="BOT_TELEGRAM", actor_referencia="Juan Pérez (Telegram id 5839201)")
        movement = create_dispatch(self.db, DespachoCreate(
            empresa_id=self.bol_id, fecha=date(2026, 8, 28), lineas=[self.line(self.bol1, 1)],
        ), origen_bot)
        self.assertEqual(movement.origen, "BOT_TELEGRAM")
        self.assertEqual(movement.actor_referencia, "Juan Pérez (Telegram id 5839201)")

    def test_dispatch_carries_guide_and_delivery_fields(self):
        self.receive(self.bol1, 10)
        movement = create_dispatch(self.db, DespachoCreate(
            empresa_id=self.bol_id, fecha=date(2026, 8, 28), guia_despacho="GD-0001",
            entregado_a="Juan Pérez", comuna="Providencia", lineas=[self.line(self.bol1, 1)],
        ))
        self.assertEqual(movement.guia_despacho, "GD-0001")
        self.assertEqual(movement.entregado_a, "Juan Pérez")
        self.assertEqual(movement.comuna, "Providencia")


if __name__ == "__main__": unittest.main()
