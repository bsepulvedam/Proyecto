import asyncio
import json
import os
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.service_auth import SERVICE_KEY_HEADER, service_key_digest
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.empresa import Empresa
from app.models.idempotencia_bot import ClaveIdempotenciaBot
from app.models.movimiento_inventario import DetalleMovimientoInventario, MovimientoInventario
from app.models.producto import Producto
from app.models.unidad_medida import UnidadMedida
from app.schemas.movimiento_inventario import LineaRecepcionCreate, RecepcionCreate
from app.services.inventario_movimiento_service import create_receipt


class ASGIResponse:
    def __init__(self, status_code: int, headers: dict[str, str], body: bytes):
        self.status_code = status_code
        self.headers = headers
        self.body = body

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class JsonASGIClient:
    """Cliente ASGI mínimo para JSON + headers arbitrarios.

    Variante reducida del ``ASGIClient`` de ``test_identity_auth.py``: ese
    sólo manda ``application/x-www-form-urlencoded`` (formularios web); la
    API del bot recibe JSON y necesita headers de servicio (``X-Service-Key``,
    ``Idempotency-Key``) que ese cliente no soporta. Vive sólo en este
    archivo de test -- no se toca el cliente original ni código de producción.
    """

    async def _request(self, method, path, json_body=None, headers=None) -> ASGIResponse:
        messages, sent = [], False
        body = json.dumps(json_body).encode() if json_body is not None else b""
        route, _, query = path.partition("?")

        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        request_headers = [(b"host", b"testserver")]
        if json_body is not None:
            request_headers.append((b"content-type", b"application/json"))
        for key, value in (headers or {}).items():
            # ASGI exige nombres de header en bytes minúsculas; al invocar
            # ``app(...)`` directo (sin servidor ASGI real de por medio) nadie
            # los normaliza, y Starlette compara sin hacer lower() del lado
            # almacenado -- un header con mayúsculas nunca haría match.
            request_headers.append((key.encode().lower(), value.encode()))

        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
            "scheme": "http", "path": route, "raw_path": route.encode(), "query_string": query.encode(),
            "root_path": "", "headers": request_headers, "client": ("127.0.0.1", 50000), "server": ("testserver", 80),
        }, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        response_headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in start["headers"]}
        response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return ASGIResponse(start["status"], response_headers, response_body)

    def get(self, path, headers=None):
        return asyncio.run(self._request("GET", path, headers=headers))

    def post(self, path, json_body=None, headers=None):
        return asyncio.run(self._request("POST", path, json_body=json_body, headers=headers))


class BotInventarioApiTests(unittest.TestCase):
    SERVICE_TOKEN = "test-bot-service-token-not-a-real-secret"

    def setUp(self):
        self.previous_env = {"BOT_SERVICE_KEY_HASH": os.environ.get("BOT_SERVICE_KEY_HASH")}
        os.environ["BOT_SERVICE_KEY_HASH"] = service_key_digest(self.SERVICE_TOKEN)

        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=[
            Empresa.__table__, UnidadMedida.__table__, Producto.__table__,
            MovimientoInventario.__table__, DetalleMovimientoInventario.__table__,
            ClaveIdempotenciaBot.__table__,
        ])
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            bol = Empresa(codigo="BOLIKLOR", nombre="BOLIKLOR")
            tineta = UnidadMedida(codigo="TINETA", nombre="Tineta", permite_decimales=False)
            db.add_all([bol, tineta]); db.flush()
            self.bol_id = bol.id
            product = Producto(
                empresa_id=bol.id, sku="BOL-1", nombre="PINTURA ACRILICA",
                unidad_stock_id=tineta.id, factor_conversion=1, unidad_costo_id=tineta.id, stock_minimo=10,
            )
            db.add(product); db.commit()
            self.product_id = product.id

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = JsonASGIClient()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        for name, value in self.previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def auth_headers(self, extra=None):
        headers = {SERVICE_KEY_HEADER: self.SERVICE_TOKEN}
        headers.update(extra or {})
        return headers

    def _receive_via_service(self, quantity="5"):
        with self.Session() as db:
            return create_receipt(db, RecepcionCreate(
                empresa_id=self.bol_id, fecha=date(2026, 9, 1),
                lineas=[LineaRecepcionCreate(producto_id=self.product_id, cantidad_presentaciones=quantity, costo_unitario=100)],
            ))

    def _receipt_payload(self, **overrides):
        payload = {
            "empresa_codigo": "BOLIKLOR",
            "fecha": "2026-09-01",
            "lineas": [{"sku": "BOL-1", "cantidad_presentaciones": "5", "costo_unitario": "100"}],
            "solicitado_por": "Juan Pérez (Telegram id 5839201)",
        }
        payload.update(overrides)
        return payload

    # --- GET /productos ---

    def test_productos_sin_api_key_devuelve_401(self):
        response = self.client.get("/api/bot/inventario/productos")
        self.assertEqual(response.status_code, 401)

    def test_productos_con_api_key_valida_filtra_por_empresa_y_q(self):
        response = self.client.get(
            "/api/bot/inventario/productos?q=pintura&empresa=BOLIKLOR", headers=self.auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([item["sku"] for item in data], ["BOL-1"])
        self.assertEqual(data[0]["empresa_codigo"], "BOLIKLOR")

    # --- GET /stock/{empresa_codigo} ---

    def test_stock_sin_api_key_devuelve_401(self):
        response = self.client.get("/api/bot/inventario/stock/BOLIKLOR")
        self.assertEqual(response.status_code, 401)

    def test_stock_con_api_key_valida_devuelve_modo_y_ledger(self):
        self._receive_via_service()
        with patch("app.services.inventory_stock_service._legacy_values", return_value={}):
            response = self.client.get("/api/bot/inventario/stock/BOLIKLOR", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["modo"], "MODO_TRANSICION")
        row = next(item for item in data["productos"] if item["sku"] == "BOL-1")
        self.assertEqual(row["ledger_stock"], "5.000")
        self.assertIsNone(row["legacy_stock"])

    def test_stock_empresa_inexistente_devuelve_404(self):
        response = self.client.get("/api/bot/inventario/stock/NOEXISTE", headers=self.auth_headers())
        self.assertEqual(response.status_code, 404)

    # --- GET /movimientos ---

    def test_movimientos_sin_api_key_devuelve_401(self):
        response = self.client.get("/api/bot/inventario/movimientos")
        self.assertEqual(response.status_code, 401)

    def test_movimientos_con_api_key_valida_filtra_por_empresa(self):
        self._receive_via_service()
        response = self.client.get(
            "/api/bot/inventario/movimientos?empresa=BOLIKLOR&tipo=RECEPCION", headers=self.auth_headers(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["tipo"], "RECEPCION")
        self.assertEqual(data[0]["lineas"][0]["sku"], "BOL-1")

    # --- POST /recepciones ---

    def test_recepciones_sin_api_key_devuelve_401(self):
        response = self.client.post("/api/bot/inventario/recepciones", json_body=self._receipt_payload())
        self.assertEqual(response.status_code, 401)

    def test_recepciones_sin_idempotency_key_devuelve_400(self):
        response = self.client.post(
            "/api/bot/inventario/recepciones", json_body=self._receipt_payload(), headers=self.auth_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_recepciones_crea_movimiento_y_es_idempotente(self):
        headers = self.auth_headers({"Idempotency-Key": "telegram-msg-88213"})
        first = self.client.post("/api/bot/inventario/recepciones", json_body=self._receipt_payload(), headers=headers)
        self.assertEqual(first.status_code, 201)
        first_data = first.json()
        self.assertTrue(first_data["creado"])

        second = self.client.post("/api/bot/inventario/recepciones", json_body=self._receipt_payload(), headers=headers)
        self.assertEqual(second.status_code, 200)
        second_data = second.json()
        self.assertFalse(second_data["creado"])
        self.assertEqual(second_data["movimiento_id"], first_data["movimiento_id"])

        with self.Session() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(MovimientoInventario)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(ClaveIdempotenciaBot)), 1)

    def test_recepciones_empresa_inexistente_devuelve_422(self):
        headers = self.auth_headers({"Idempotency-Key": "telegram-msg-1"})
        response = self.client.post(
            "/api/bot/inventario/recepciones", json_body=self._receipt_payload(empresa_codigo="NOEXISTE"), headers=headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_recepciones_sku_inexistente_devuelve_422(self):
        headers = self.auth_headers({"Idempotency-Key": "telegram-msg-2"})
        payload = self._receipt_payload(lineas=[{"sku": "NOEXISTE", "cantidad_presentaciones": "1", "costo_unitario": "10"}])
        response = self.client.post("/api/bot/inventario/recepciones", json_body=payload, headers=headers)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
