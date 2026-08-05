"""Регрессионные тесты Markdown-списков."""

from __future__ import annotations

import unittest

from confluence_markdown_service import ConfluenceMarkdownImporter


class MarkdownListTests(unittest.TestCase):
    def setUp(self) -> None:
        self.importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]

    def test_star_list_without_blank_line(self) -> None:
        result = self.importer.preview_markdown_to_storage(
            "Текст какой-то:\n* один\n* два\n"
        )

        self.assertEqual(
            result.storage,
            "<p>Текст какой-то:</p>\n<ul>\n<li>один</li>\n<li>два</li>\n</ul>",
        )

    def test_dash_list_without_blank_line(self) -> None:
        result = self.importer.preview_markdown_to_storage(
            "Текст:\n- один\n- два\n"
        )

        self.assertIn("<ul>", result.storage)
        self.assertIn("<li>один</li>", result.storage)

    def test_list_marker_inside_fenced_code_is_unchanged(self) -> None:
        result = self.importer.preview_markdown_to_storage(
            "```text\nТекст:\n* не список\n```\n"
        )

        self.assertNotIn("<ul>", result.storage)


if __name__ == "__main__":
    unittest.main()
