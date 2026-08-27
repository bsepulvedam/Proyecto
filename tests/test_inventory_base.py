import asyncio
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from app.main import app
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.inventario import ProductoCreate
from app.services.product_import_service import ProductImportReport


async def asgi_get(path: str) -> tuple[int, bytes]:
    messages: list[dict] = []
    request_sent = False

    async def receive() -> dict:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    route_path, _, query_string = path.partition("?")
    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": route_path,
            "raw_path": route_path.encode("ascii"),
            "query_string": query_string.encode("utf-8"),
            "root_path": "",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], body


class InventoryBaseTests(unittest.TestCase):
    def test_inventory_tables_and_constraints_are_declared(self) -> None:
        self.assertEqual(Empresa.__tablename__, "empresas")
        self.assertEqual(UnidadMedida.__tablename__, "unidades_medida")
        self.assertEqual(Producto.__tablename__, "productos")

        product_constraints = {constraint.name for constraint in Producto.__table__.constraints}
        self.assertIn("uq_productos_sku", product_constraints)
        self.assertIn("ck_productos_factor_conversion_positivo", product_constraints)
        self.assertIn("ck_productos_stock_minimo_no_negativo", product_constraints)

        foreign_keys = {
            foreign_key.target_fullname for foreign_key in Producto.__table__.foreign_keys
        }
        self.assertEqual(
            foreign_keys,
            {
                "empresas.id",
                "unidades_medida.id",
            },
        )
        self.assertTrue(Producto.__table__.c.unidad_contenido_id.nullable)
        self.assertFalse(Producto.__table__.c.empresa_id.nullable)

    def test_product_schema_rejects_invalid_numeric_values(self) -> None:
        common = {
            "empresa_id": 1,
            "sku": "BOL-TEST",
            "nombre": "Producto de prueba",
            "unidad_stock_id": 1,
            "unidad_costo_id": 1,
        }
        with self.assertRaises(ValidationError):
            ProductoCreate(**common, factor_conversion=0)
        with self.assertRaises(ValidationError):
            ProductoCreate(**common, stock_minimo=-1)

    def test_empty_products_page(self) -> None:
        with (
            patch("app.web.products.listar_productos", return_value=[]) as list_mock,
            patch(
                "app.services.orden_trabajo_service.numero_ot_sequence.next_value"
            ) as next_value_mock,
        ):
            status, body = asyncio.run(asgi_get("/productos"))
        self.assertEqual(status, 200)
        self.assertIn("Aún no hay productos".encode(), body)
        list_mock.assert_called_once()
        next_value_mock.assert_not_called()

    def test_products_page_lists_catalog_relations(self) -> None:
        unit_stock = SimpleNamespace(codigo="SACO")
        unit_content = SimpleNamespace(codigo="KG")
        product = SimpleNamespace(
            sku="BOL-8",
            empresa=SimpleNamespace(codigo="BOLIKLOR"),
            nombre="Pintura termoplástica",
            unidad_stock=unit_stock,
            unidad_contenido=unit_content,
            factor_conversion=Decimal("25.0000"),
            unidad_costo=unit_content,
            stock_minimo="10.000",
            tipo="Pintura",
            familia="Termoplástica",
            activo=True,
        )
        with patch("app.web.products.listar_productos", return_value=[product]):
            status, body = asyncio.run(asgi_get("/productos"))
        self.assertEqual(status, 200)
        self.assertIn(b"BOL-8", body)
        self.assertIn(b"BOLIKLOR", body)
        self.assertIn(b"25 KG / SACO", body)
        self.assertNotIn(b"25.0000", body)
        self.assertIn(b">10<", body)

    def test_products_use_natural_sku_order(self) -> None:
        company = SimpleNamespace(codigo="BOLIKLOR")
        stock_unit = SimpleNamespace(codigo="UN")
        products = [
            SimpleNamespace(id=index, sku=sku, empresa=company, nombre=sku,
                unidad_stock=stock_unit, unidad_contenido=None,
                factor_conversion=Decimal("1"), unidad_costo=stock_unit,
                stock_minimo=Decimal("1"), tipo="MATERIAL", familia="FAMILIA", activo=True)
            for index, sku in enumerate(("BOL-10", "BOL-2", "BOL-1"), start=1)
        ]
        with patch("app.web.products.listar_productos", return_value=products):
            status, body = asyncio.run(asgi_get("/productos"))
        self.assertEqual(status, 200)
        self.assertLess(body.index(b"BOL-1"), body.index(b"BOL-2"))
        self.assertLess(body.index(b"BOL-2"), body.index(b"BOL-10"))

    def test_family_and_company_filters_are_combined(self) -> None:
        unit_value = SimpleNamespace(codigo="UN")
        def item(sku, company, family):
            return SimpleNamespace(id=sku, sku=sku, empresa=SimpleNamespace(codigo=company),
                nombre=sku, unidad_stock=unit_value, unidad_contenido=None,
                factor_conversion=Decimal("1"), unidad_costo=unit_value,
                stock_minimo=Decimal("1"), tipo="MATERIAL", familia=family, activo=True)
        products = [
            item("BOL-1", "BOLIKLOR", "DEMARCACION"),
            item("BOL-2", "BOLIKLOR", "FERRETERIA"),
            item("ALM-1", "ALM", "DEMARCACION"),
        ]
        with patch("app.web.products.listar_productos", return_value=products):
            status, body = asyncio.run(asgi_get("/productos?familia=DEMARCACION&empresa=BOLIKLOR"))
        self.assertEqual(status, 200)
        self.assertIn(b"BOL-1", body)
        self.assertNotIn(b"BOL-2", body)
        self.assertNotIn(b"ALM-1", body)
        self.assertIn(b"?familia=DEMARCACION", body)

    def test_product_import_preview_route(self) -> None:
        report = ProductImportReport(
            source_file="maestro.xlsx",
            sheets_used=["Maestro de materiales", "Stock Boliklor", "Stock ALM"],
            rows=[],
            unidades_detectadas=[],
            unidades_no_registradas=[],
            duplicados=[],
            conflictos_maestro_stock=[],
            productos_stock_sin_maestro=[],
        )
        with (
            patch("app.web.products.listar_empresas", return_value=[]),
            patch("app.web.products.listar_unidades", return_value=[]),
            patch("app.web.products.listar_productos", return_value=[]),
            patch("app.web.products.analyze_product_workbook", return_value=report),
        ):
            status, body = asyncio.run(asgi_get("/productos/importar"))
        self.assertEqual(status, 200)
        self.assertIn("Vista previa de importación".encode(), body)
        self.assertIn("Importar productos".encode(), body)

    def test_migration_is_additive_and_does_not_reference_ot_objects(self) -> None:
        migration = Path(
            "alembic/versions/20260826_02_fase_4_inventario_base.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ordenes_trabajo", migration)
        self.assertNotIn("productos_ot", migration)
        self.assertNotIn("numero_ot_seq", migration)
        self.assertIn('down_revision: str | None = "20260826_01"', migration)

    def test_existing_api_routes_remain_registered(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/productos/importar"])
        self.assertIn("get", paths["/productos/corregir-importacion"])
        self.assertNotIn("post", paths["/productos/corregir-importacion"])
        self.assertIn("post", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo/{orden_id}"])


if __name__ == "__main__":
    unittest.main()
