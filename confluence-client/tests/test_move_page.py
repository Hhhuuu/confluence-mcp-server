"""Тесты перемещения страницы."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

import httpx

from confluence_client.client import ConfluenceClient


class RecordingConfluenceClient(ConfluenceClient):
    """Клиент без сети, запоминающий REST-запрос."""

    def __init__(self) -> None:
        self._api_prefix = "/wiki"
        self._config = SimpleNamespace(deployment="cloud")
        self.recorded_request: tuple[str, str] | None = None

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        self.recorded_request = (method, path)
        return httpx.Response(
            200,
            content=json.dumps({"pageId": "123"}).encode(),
            request=httpx.Request(method, f"https://example.test{path}"),
        )


class MovePageTests(unittest.TestCase):
    def test_moves_page_after_target(self) -> None:
        client = RecordingConfluenceClient()

        result = client.move_page("123", "456", "after")

        self.assertEqual(result.page_id, "123")
        self.assertEqual(
            client.recorded_request,
            ("PUT", "/wiki/rest/api/content/123/move/after/456"),
        )

    def test_rejects_page_as_its_own_target(self) -> None:
        client = RecordingConfluenceClient()

        with self.assertRaisesRegex(ValueError, "должны отличаться"):
            client.move_page("123", "123", "before")

    def test_rejects_unknown_position(self) -> None:
        client = RecordingConfluenceClient()

        with self.assertRaisesRegex(ValueError, "before, after, append"):
            client.move_page("123", "456", "last")  # type: ignore[arg-type]


class RecordingServerClient(ConfluenceClient):
    def __init__(self) -> None:
        self._api_prefix = ""
        self._config = SimpleNamespace(deployment="server")
        self.requests: list[tuple[str, str, dict]] = []

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        self.requests.append((method, path, kwargs))
        return httpx.Response(
            200,
            content=b"moved",
            headers={"success": "true"},
            request=httpx.Request(method, f"https://example.test{path}"),
        )


class MovePageServerTests(unittest.TestCase):
    def test_moves_page_after_target_with_move_page_action(self) -> None:
        client = RecordingServerClient()

        result = client.move_page("123", "456", "after")

        self.assertEqual(result.page_id, "123")
        method, path, kwargs = client.requests[0]
        self.assertEqual((method, path), ("GET", "/pages/movepage.action"))
        self.assertEqual(
            kwargs["params"],
            {
                "pageId": "123",
                "point": "below",
                "targetId": "456",
            },
        )

    def test_appends_page_as_last_child(self) -> None:
        client = RecordingServerClient()

        client.move_page("123", "456", "append")

        params = client.requests[0][2]["params"]
        self.assertEqual(params["point"], "append")


if __name__ == "__main__":
    unittest.main()
