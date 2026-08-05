"""Тесты ссылок внутри Markdown-кода."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from confluence_markdown_service import ConfluenceMarkdownImporter


class MarkdownFileCodeLinksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]

    def _preview(self, markdown_text: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.md"
            path.write_text(markdown_text, encoding="utf-8")
            return self.importer.preview_markdown_file_to_storage(path)

    def test_ignores_links_and_images_inside_fenced_code(self) -> None:
        result = self._preview(
            "```markdown\n[spec](./missing.pdf)\n![image](./missing.png)\n```\n"
        )

        self.assertEqual(result.warnings, [])
        self.assertIn("./missing.pdf", result.storage)
        self.assertIn("./missing.png", result.storage)

    def test_ignores_links_inside_inline_code(self) -> None:
        result = self._preview("Example: `[spec](./missing.pdf)`\n")

        self.assertEqual(result.warnings, [])
        self.assertIn("./missing.pdf", result.storage)

    def test_ignores_links_inside_indented_code(self) -> None:
        result = self._preview("    [spec](./missing.pdf)\n")

        self.assertEqual(result.warnings, [])
        self.assertIn("./missing.pdf", result.storage)


if __name__ == "__main__":
    unittest.main()
