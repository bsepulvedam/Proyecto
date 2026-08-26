import asyncio
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from app.main import app
from app.web.work_orders import work_order_dates


async def asgi_request(
    method: str, path: str, fields: list[tuple[str, str]] | None = None
) -> tuple[int, dict[str, str], bytes]:
    body = urlencode(fields or []).encode("utf-8")
    messages: list[dict] = []
    request_sent = False

    async def receive() -> dict:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    headers = [(b"host", b"testserver")]
    if body:
        headers.extend(
            [
                (b"content-type", b"application/x-www-form-urlencoded"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start["headers"]
    }
    return start["status"], response_headers, response_body


VALID_FORM = [
    ("comuna", "Mostazal"),
    ("descripcion", "Señalética preventiva"),
    ("unidad", "UND"),
    ("cantidad", "2.500"),
    ("medida_especifica", "60 x 80 cm"),
    ("observaciones", "Instalar en acceso principal"),
]


def persisted_order(order_id: int = 20, numero_ot: int = 20) -> SimpleNamespace:
    product = SimpleNamespace(
        id=1,
        descripcion="Señalética vial",
        unidad="UND",
        cantidad="3.000",
        medida_especifica="60 x 80 cm",
    )
    return SimpleNamespace(
        id=order_id,
        numero_ot=numero_ot,
        comuna="Mostazal",
        empresa_origen=None,
        recibe=None,
        fecha_pedido=date(2026, 8, 26),
        fecha_entrega=date(2026, 8, 28),
        fecha_finalizacion=None,
        estado=None,
        cliente="Cliente de prueba",
        telefono=None,
        correo="cliente@example.com",
        recibido_por=None,
        lugar_trabajo="Acceso principal",
        estado_cliente=None,
        referencia_pedido="PED-100",
        responsable_boliklor=None,
        observaciones="Instalación prioritaria",
        productos=[product],
    )


class WorkOrderWebTests(unittest.TestCase):
    def test_new_work_order_form(self) -> None:
        status, headers, body = asyncio.run(
            asgi_request("GET", "/ordenes-trabajo/nueva")
        )
        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertEqual(body.count(b'class="product-row"'), 6)
        self.assertIn("Se asignará al confirmar".encode(), body)

    def test_delivery_date_is_two_calendar_days_after_request(self) -> None:
        request_date, delivery_date = work_order_dates(date(2026, 8, 30))
        self.assertEqual(request_date, date(2026, 8, 30))
        self.assertEqual(delivery_date, date(2026, 9, 1))

    def test_valid_review_does_not_create_order(self) -> None:
        with patch("app.web.work_orders.crear_orden") as create_mock:
            status, _, body = asyncio.run(
                asgi_request("POST", "/ordenes-trabajo/revisar", VALID_FORM)
            )
        self.assertEqual(status, 200)
        self.assertIn("Revisa la orden de trabajo".encode(), body)
        self.assertIn("Señalética preventiva".encode(), body)
        create_mock.assert_not_called()

    def test_review_without_products_is_rejected(self) -> None:
        status, _, body = asyncio.run(
            asgi_request(
                "POST", "/ordenes-trabajo/revisar", [("comuna", "Colina")]
            )
        )
        self.assertEqual(status, 422)
        self.assertIn("al menos un producto".encode(), body)

    def test_partial_row_is_rejected(self) -> None:
        status, _, body = asyncio.run(
            asgi_request(
                "POST",
                "/ordenes-trabajo/revisar",
                [("comuna", "Colina"), ("descripcion", "Trabajo incompleto")],
            )
        )
        self.assertEqual(status, 422)
        self.assertIn("está incompleta".encode(), body)

    def test_invalid_quantity_is_rejected(self) -> None:
        fields = [
            ("comuna", "Colina"),
            ("descripcion", "Trabajo"),
            ("unidad", "UND"),
            ("cantidad", "0"),
        ]
        status, _, body = asyncio.run(
            asgi_request("POST", "/ordenes-trabajo/revisar", fields)
        )
        self.assertEqual(status, 422)
        self.assertIn("mayor que 0".encode(), body)

    def test_edit_preserves_reviewed_information(self) -> None:
        status, _, body = asyncio.run(
            asgi_request("POST", "/ordenes-trabajo/nueva", VALID_FORM)
        )
        self.assertEqual(status, 200)
        self.assertIn(b'value="Mostazal" selected', body)
        self.assertIn("Señalética preventiva".encode(), body)
        self.assertIn("Instalar en acceso principal".encode(), body)

    def test_confirm_reuses_service_without_real_database_write(self) -> None:
        created = SimpleNamespace(id=321, numero_ot=77)
        with patch("app.web.work_orders.crear_orden", return_value=created) as create_mock:
            status, _, body = asyncio.run(
                asgi_request("POST", "/ordenes-trabajo/confirmar", VALID_FORM)
            )
        self.assertEqual(status, 201)
        self.assertIn("OT N°77".encode(), body)
        create_mock.assert_called_once()
        submitted_order = create_mock.call_args.args[1]
        self.assertEqual(submitted_order.comuna, "Mostazal")
        self.assertIsNone(submitted_order.empresa_origen)
        self.assertIsNone(submitted_order.cliente)
        self.assertEqual(len(submitted_order.productos), 1)

    def test_existing_api_routes_remain_registered(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo/{orden_id}"])

    def test_history_uses_listing_service_and_renders_orders(self) -> None:
        order = persisted_order()
        with (
            patch("app.web.work_orders.listar_ordenes", return_value=[order]) as list_mock,
            patch(
                "app.services.orden_trabajo_service.numero_ot_sequence.next_value"
            ) as next_value_mock,
        ):
            status, _, body = asyncio.run(
                asgi_request("GET", "/ordenes-trabajo")
            )
        self.assertEqual(status, 200)
        self.assertIn("Historial OT".encode(), body)
        self.assertIn("OT N°20".encode(), body)
        self.assertIn("Por definir".encode(), body)
        self.assertIn(b"26/08/2026", body)
        list_mock.assert_called_once()
        next_value_mock.assert_not_called()

    def test_existing_work_order_detail_uses_service(self) -> None:
        order = persisted_order()
        with (
            patch("app.web.work_orders.obtener_orden", return_value=order) as get_mock,
            patch(
                "app.services.orden_trabajo_service.numero_ot_sequence.next_value"
            ) as next_value_mock,
        ):
            status, _, body = asyncio.run(
                asgi_request("GET", "/ordenes-trabajo/20")
            )
        self.assertEqual(status, 200)
        self.assertIn("OT N°20".encode(), body)
        self.assertIn("Cliente de prueba".encode(), body)
        self.assertIn("Señalética vial".encode(), body)
        self.assertIn("Instalación prioritaria".encode(), body)
        self.assertIn("—".encode(), body)
        get_mock.assert_called_once_with(unittest.mock.ANY, 20)
        next_value_mock.assert_not_called()

    def test_missing_work_order_returns_404(self) -> None:
        with patch("app.web.work_orders.obtener_orden", return_value=None) as get_mock:
            status, _, body = asyncio.run(
                asgi_request("GET", "/ordenes-trabajo/999999")
            )
        self.assertEqual(status, 404)
        self.assertIn("Orden de trabajo no encontrada".encode(), body)
        get_mock.assert_called_once_with(unittest.mock.ANY, 999999)


if __name__ == "__main__":
    unittest.main()
