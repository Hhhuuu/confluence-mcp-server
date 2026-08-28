"""Регрессионные тесты экспорта небезопасного HTML."""

from __future__ import annotations

import unittest

from confluence_markdown_service.storage_normalizer import parse_storage_document
from confluence_markdown_service.storage_renderer import StorageMarkdownRenderer


class UnsafeHtmlExportTests(unittest.TestCase):
    def _render(self, storage: str) -> tuple[str, StorageMarkdownRenderer]:
        renderer = StorageMarkdownRenderer()
        markdown = renderer.render_document(parse_storage_document(storage))
        return markdown, renderer

    def test_skips_html_macro_body(self) -> None:
        markdown, renderer = self._render(
            '<ac:structured-macro ac:name="html">'
            "<ac:plain-text-body><![CDATA["
            '<div id="widget">visible</div><script>alert(1)</script>'
            "]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )

        self.assertEqual(markdown, "")
        self.assertNotIn("<div", markdown)
        self.assertNotIn("<script", markdown)
        self.assertIn("Макрос html был пропущен", renderer.warnings[0])

    def test_skips_script_but_keeps_safe_div_text(self) -> None:
        markdown, renderer = self._render(
            '<div>Полезный текст<script>window.secret = true</script></div>'
        )

        self.assertEqual(markdown, "Полезный текст")
        self.assertIn("HTML-тег script был пропущен", renderer.warnings[0])


if __name__ == "__main__":
    unittest.main()
