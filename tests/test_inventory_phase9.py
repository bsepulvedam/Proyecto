import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database.base import Base
from app.main import app
from app.models.empresa import Empresa
from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.inventario import ProductoCreate
from app.services.inventario_catalogo_service import CatalogError, crear_producto
from app.services.inventario_movimiento_service import calculate_stock_from_movements, list_movements
from app.services.inventory_stock_service import MODE_OPERATIONAL, MODE_TRANSITION, inventory_mode, inventory_stock_rows
from app.web.inventory import _stock_page


class InventoryPhase9Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[
            Empresa.__table__, UnidadMedida.__table__, Producto.__table__,
            MovimientoInventario.__table__, DetalleMovimientoInventario.__table__,
        ])
        self.db = Session(self.engine)
        bol = Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")
        alm = Empresa(codigo="ALM", nombre="ALM")
        unit = UnidadMedida(codigo="UN", nombre="Unidad", permite_decimales=False)
        self.db.add_all([bol, alm, unit]); self.db.flush()
        self.bol, self.alm, self.unit = bol, alm, unit
        self.bol_product = self._product("BOL-1", bol, Decimal("10"))
        self.alm_product = self._product("ALM-1", alm, Decimal("2"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _product(self, sku, company, minimum):
        product = Producto(empresa_id=company.id, sku=sku, nombre=sku, unidad_stock_id=self.unit.id,
            unidad_costo_id=self.unit.id, factor_conversion=1, stock_minimo=minimum, familia="LIMPIEZA")
        self.db.add(product)
        return product

    def _movement(self, kind, company, product, quantity, number):
        movement = MovimientoInventario(tipo=kind, empresa_id=company.id, fecha=date(2026, 8, 28), numero_documento=number)
        movement.detalles.append(DetalleMovimientoInventario(
            producto_id=product.id, cantidad_presentaciones=quantity,
            unidad_presentacion_snapshot="UN", factor_conversion_snapshot=1,
            unidad_costo_snapshot="UN", costo_unitario=100, costo_presentacion=100,
            valor_total=Decimal(quantity) * 100,
        ))
        self.db.add(movement)
        self.db.commit()
        return movement

    def test_receipt_does_not_switch_transition_mode(self):
        self.assertEqual(inventory_mode(self.db), MODE_TRANSITION)
        self._movement("RECEPCION", self.bol, self.bol_product, 3, "MOV-000001")
        self.assertEqual(inventory_mode(self.db), MODE_TRANSITION)

    def test_initial_adjustment_switches_to_operational_stock(self):
        self._movement("AJUSTE_INICIAL", self.bol, self.bol_product, 4, "MOV-000001")
        self._movement("AJUSTE_INICIAL", self.alm, self.alm_product, 7, "MOV-000002")
        self.assertEqual(inventory_mode(self.db), MODE_OPERATIONAL)
        with patch("app.services.inventory_stock_service._legacy_values") as legacy_mock:
            mode, rows = inventory_stock_rows(self.db)
        values = {row.product.sku: row for row in rows}
        self.assertEqual(mode, MODE_OPERATIONAL)
        self.assertEqual(values["BOL-1"].displayed_stock, Decimal("4.000"))
        self.assertEqual(values["ALM-1"].displayed_stock, Decimal("7.000"))
        self.assertTrue(values["BOL-1"].requires_restock)
        self.assertFalse(values["ALM-1"].requires_restock)
        legacy_mock.assert_not_called()

    def test_transition_shows_legacy_and_keeps_test_movements_separate(self):
        self._movement("RECEPCION", self.bol, self.bol_product, 3, "MOV-000001")
        with patch("app.services.inventory_stock_service._legacy_values", return_value={"BOL-1": Decimal("47"), "ALM-1": Decimal("0")}):
            mode, rows = inventory_stock_rows(self.db)
        values = {row.product.sku: row for row in rows}
        self.assertEqual(mode, MODE_TRANSITION)
        self.assertEqual(values["BOL-1"].displayed_stock, Decimal("47"))
        self.assertEqual(values["BOL-1"].movement_stock, Decimal("3.000"))
        self.assertEqual(values["ALM-1"].stock_state, "SIN STOCK")

    def test_missing_legacy_value_is_not_silently_replaced_by_test_movement(self):
        self._movement("RECEPCION", self.bol, self.bol_product, 3, "MOV-000001")
        with patch("app.services.inventory_stock_service._legacy_values", return_value={}):
            _, rows = inventory_stock_rows(self.db)
        bol = next(row for row in rows if row.product.sku == "BOL-1")
        self.assertEqual(bol.displayed_stock, Decimal("0"))
        self.assertEqual(bol.movement_stock, Decimal("3.000"))

    def test_stock_pages_filter_each_company_and_combined_criteria(self):
        from app.services.inventory_stock_service import InventoryStockRow
        bol_row = InventoryStockRow(self.bol_product, Decimal("5"), Decimal("0"), Decimal("5"), MODE_TRANSITION)
        alm_row = InventoryStockRow(self.alm_product, Decimal("0"), Decimal("0"), Decimal("0"), MODE_TRANSITION)

        def context_for(company, query):
            request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": query.encode()})
            with (
                patch("app.web.inventory.inventory_stock_rows", return_value=(MODE_TRANSITION, [bol_row, alm_row])),
                patch("app.web.inventory.templates.TemplateResponse", side_effect=lambda **kwargs: SimpleNamespace(context=kwargs["context"])),
            ):
                return _stock_page(request, self.db, company).context

        bol = context_for("BOLIKLOR", "q=BOL&familia=LIMPIEZA&estado=EN%20STOCK&stock_desde=5&stock_hasta=5")
        alm = context_for("ALM", "familia=LIMPIEZA&estado=SIN%20STOCK&reposicion=1&stock_hasta=0")
        self.assertEqual([row.product.sku for row in bol["rows"]], ["BOL-1"])
        self.assertEqual([row.product.sku for row in alm["rows"]], ["ALM-1"])

    def test_product_creation_has_zero_transactional_stock_and_rejects_duplicate(self):
        data = ProductoCreate(empresa_id=self.bol.id, sku=" bol-20 ", nombre=" nuevo ",
            unidad_stock_id=self.unit.id, unidad_costo_id=self.unit.id, stock_minimo=5)
        product = crear_producto(self.db, data)
        self.assertEqual((product.sku, product.nombre), ("BOL-20", "NUEVO"))
        self.assertEqual(calculate_stock_from_movements(self.db).get((self.bol.id, product.id), Decimal("0")), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(MovimientoInventario)), 0)
        with self.assertRaises(CatalogError):
            crear_producto(self.db, data)

    def test_movement_filters_combine_company_type_date_and_sku(self):
        self._movement("RECEPCION", self.bol, self.bol_product, 2, "MOV-000001")
        self._movement("AJUSTE_INICIAL", self.alm, self.alm_product, 1, "MOV-000002")
        rows = list_movements(self.db, self.bol.id, "RECEPCION", date(2026, 8, 28), date(2026, 8, 28), "BOL-1")
        self.assertEqual([row.numero_documento for row in rows], ["MOV-000001"])

    def test_phase9_routes_and_non_operational_initialization(self):
        paths = app.openapi()["paths"]
        for path in ("/inventario/stock/boliklor", "/inventario/stock/alm", "/inventario/inicializacion", "/inventario/costos", "/productos/nuevo"):
            self.assertIn("get", paths[path])
        self.assertIn("post", paths["/productos/nuevo"])
        self.assertNotIn("post", paths["/inventario/inicializacion"])
        initialization = Path("app/templates/inventory/initialization.html").read_text(encoding="utf-8")
        product_form = Path("app/templates/products/new.html").read_text(encoding="utf-8")
        self.assertNotIn('method="post"', initialization.lower())
        self.assertNotIn('name="stock_actual"', product_form)


if __name__ == "__main__":
    unittest.main()
