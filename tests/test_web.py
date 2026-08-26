import asyncio
import unittest

from app.main import app


async def asgi_get(path: str) -> tuple[int, dict[str, str], bytes]:
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

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)

    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start["headers"]
    }
    return start["status"], headers, body


class WebIntegrationTests(unittest.TestCase):
    def test_root(self) -> None:
        status, _, body = asyncio.run(asgi_get("/"))
        self.assertEqual(status, 200)
        self.assertIn(b'"ok":true', body)

    def test_health(self) -> None:
        status, _, body = asyncio.run(asgi_get("/health"))
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok"}')

    def test_dashboard(self) -> None:
        status, headers, body = asyncio.run(asgi_get("/dashboard"))
        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertIn("Dashboard | BOLIKLOR".encode(), body)

    def test_stylesheet(self) -> None:
        status, headers, body = asyncio.run(asgi_get("/static/css/styles.css"))
        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/css"))
        self.assertIn(b"--color-yellow: #f4c400", body)

    def test_work_order_routes_remain_registered(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo"])
        self.assertIn("get", paths["/api/ordenes-trabajo/{orden_id}"])


if __name__ == "__main__":
    unittest.main()
