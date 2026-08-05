"""Тесты перемещения страницы."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

import httpx

from confluence_client.client import ConfluenceClient
from confluence_client.exceptions import ConfluenceRequestError


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
        if method == "GET" and path.endswith("/123"):
            payload = {
                "id": "123",
                "type": "page",
                "title": "Source",
                "version": {"number": 4},
            }
        else:
            payload = {"id": "123", "title": "Source"}
        return httpx.Response(
            200,
            content=json.dumps(payload).encode(),
            request=httpx.Request(method, f"https://example.test{path}"),
        )


class MovePageServerTests(unittest.TestCase):
    def test_rejects_after_not_supported_by_85_rest_api(self) -> None:
        client = RecordingServerClient()

        with self.assertRaisesRegex(ConfluenceRequestError, "8.5 REST API"):
            client.move_page("123", "456", "after")

        self.assertEqual(client.requests, [])

    def test_appends_page_under_target_with_content_rest_api(self) -> None:
        client = RecordingServerClient()

        result = client.move_page("123", "456", "append")

        self.assertEqual(result.page_id, "123")
        method, path, kwargs = client.requests[-1]
        self.assertEqual((method, path), ("PUT", "/rest/api/content/123"))
        self.assertEqual(
            kwargs["json"],
            {
                "id": "123",
                "type": "page",
                "title": "Source",
                "version": {"number": 5},
                "ancestors": [{"id": "456"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
