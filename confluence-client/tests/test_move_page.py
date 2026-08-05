"""Тесты перемещения страницы."""

from __future__ import annotations

import json
import unittest

import httpx

from confluence_client.client import ConfluenceClient


class RecordingConfluenceClient(ConfluenceClient):
    """Клиент без сети, запоминающий REST-запрос."""

    def __init__(self) -> None:
        self._api_prefix = "/wiki"
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


if __name__ == "__main__":
    unittest.main()
