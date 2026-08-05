"""Тесты Markdown-содержимого create_pages."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from confluence_mcp.mcp_server import create_pages


class FakeClient:
    def close(self) -> None:
        pass


class FakeResult:
    def model_dump(self, *, mode: str) -> dict:
        return {"mode": mode}


class RecordingService:
    def __init__(self) -> None:
        self.content = ""

    def create_pages(self, request, *, default_space_key=None):
        self.content = request.content
        return FakeResult()


class CreatePagesMarkdownTests(unittest.TestCase):
    def test_converts_markdown_content_to_storage(self) -> None:
        service = RecordingService()
        with (
            patch(
                "confluence_mcp.mcp_server.load_runtime_client",
                return_value=(FakeClient(), None),
            ),
            patch(
                "confluence_mcp.mcp_server.load_runtime_service",
                return_value=(service, "DOC"),
            ),
            patch("confluence_mcp.mcp_server._builtin_extension_options", return_value={}),
        ):
            create_pages(
                paths=["Root/Page"],
                content="Текст:\n* один\n* два",
            )

        self.assertIn("<ul>", service.content)
        self.assertIn("<li>один</li>", service.content)

    def test_keeps_explicit_storage_content(self) -> None:
        service = RecordingService()
        storage = "<ul><li>один</li></ul>"
        with patch(
            "confluence_mcp.mcp_server.load_runtime_service",
            return_value=(service, "DOC"),
        ):
            create_pages(
                paths=["Root/Page"],
                content=storage,
                content_format="storage",
            )

        self.assertEqual(service.content, storage)


if __name__ == "__main__":
    unittest.main()
