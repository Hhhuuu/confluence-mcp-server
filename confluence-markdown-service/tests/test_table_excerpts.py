"""Tests for Stiltsoft Table Excerpt Markdown extension."""

from __future__ import annotations

import unittest

from confluence_markdown_service import (
    ConfluenceMarkdownImporter,
    TableExcerptsExtension,
)
from confluence_markdown_service.storage_normalizer import parse_storage_document
from confluence_markdown_service.storage_renderer import StorageMarkdownRenderer


SOURCE_MARKDOWN = """<table-excerpt name="project-status">

| Project | Owner | Status |
| --- | --- | --- |
| Alpha | Ivan | Active |

</table-excerpt>
"""

INCLUDE_MARKDOWN = """<table-excerpt-include
  name="project-status"
  source-type="page"
  page="DOC:Projects"
  show-source="true"
  report="true"
  transpose="auto"
  param-v="2"
/>
"""


class TableExcerptImportTests(unittest.TestCase):
    def test_source_table_becomes_rich_text_macro(self) -> None:
        importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]

        result = importer.preview_markdown_to_storage(SOURCE_MARKDOWN)

        self.assertIn('ac:name="table-excerpt"', result.storage)
        self.assertIn('ac:name="name">project-status</ac:parameter>', result.storage)
        self.assertIn("<ac:rich-text-body><table>", result.storage)
        self.assertIn("<th>Project</th>", result.storage)
        self.assertEqual(result.warnings, [])

    def test_include_maps_friendly_attributes_to_server_parameters(self) -> None:
        importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]

        result = importer.preview_markdown_to_storage(INCLUDE_MARKDOWN)

        self.assertIn('ac:name="table-excerpt-include"', result.storage)
        self.assertIn('ac:name="type">page</ac:parameter>', result.storage)
        self.assertIn('ac:name="copytable">true</ac:parameter>', result.storage)
        self.assertIn('ac:name="merge-tables">true</ac:parameter>', result.storage)
        self.assertIn('ac:name="transpose">auto</ac:parameter>', result.storage)
        self.assertIn('ac:name="v">2</ac:parameter>', result.storage)
        self.assertIn('ri:content-title="DOC:Projects"', result.storage)

    def test_extension_can_be_disabled(self) -> None:
        extension = TableExcerptsExtension(enabled=False)

        self.assertEqual(extension.preprocess_markdown(SOURCE_MARKDOWN), SOURCE_MARKDOWN)

    def test_tags_inside_fenced_code_are_not_converted(self) -> None:
        importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]
        markdown = """~~~md
<table-excerpt-include name="demo" source="current" />
~~~
"""

        result = importer.preview_markdown_to_storage(markdown)

        self.assertNotIn('ac:name="table-excerpt-include"', result.storage)
        self.assertIn("table-excerpt-include", result.storage)


class TableExcerptExportTests(unittest.TestCase):
    def test_exports_source_macro_as_editable_markdown(self) -> None:
        storage = (
            '<ac:structured-macro ac:name="table-excerpt" ac:schema-version="1">'
            '<ac:parameter ac:name="name">project-status</ac:parameter>'
            "<ac:rich-text-body>"
            "<table><tbody><tr><th>Project</th><th>Status</th></tr>"
            "<tr><td>Alpha</td><td>Active</td></tr></tbody></table>"
            "</ac:rich-text-body>"
            "</ac:structured-macro>"
        )

        markdown = self._render(storage)

        self.assertIn('<table-excerpt name="project-status">', markdown)
        self.assertIn("| Project | Status |", markdown)
        self.assertIn("| Alpha | Active |", markdown)
        self.assertIn("</table-excerpt>", markdown)

    def test_include_round_trip_preserves_known_and_unknown_parameters(self) -> None:
        storage = (
            '<ac:structured-macro ac:name="table-excerpt-include" ac:schema-version="1">'
            '<ac:parameter ac:name="name">project-status</ac:parameter>'
            '<ac:parameter ac:name="copytable">true</ac:parameter>'
            '<ac:parameter ac:name="merge-tables">true</ac:parameter>'
            '<ac:parameter ac:name="v">2</ac:parameter>'
            '<ac:parameter ac:name="page"><ac:link>'
            '<ri:page ri:content-title="DOC:Projects"/>'
            "</ac:link></ac:parameter>"
            '<ac:parameter ac:name="custom-xml"><ac:link>'
            '<ri:page ri:content-title="DOC:Archive"/>'
            "</ac:link></ac:parameter>"
            "</ac:structured-macro>"
        )

        markdown = self._render(storage)

        self.assertIn('name="project-status"', markdown)
        self.assertIn('show-source="true"', markdown)
        self.assertIn('report="true"', markdown)
        self.assertIn('page="DOC:Projects"', markdown)
        self.assertIn('param-v="2"', markdown)
        self.assertIn("xml-param-custom-xml=", markdown)

        importer = ConfluenceMarkdownImporter(None)  # type: ignore[arg-type]
        imported = importer.preview_markdown_to_storage(markdown).storage
        self.assertIn('ac:name="custom-xml"', imported)
        self.assertIn('ri:content-title="DOC:Archive"', imported)
        self.assertIn('ac:name="merge-tables">true</ac:parameter>', imported)

    @staticmethod
    def _render(storage: str) -> str:
        renderer = StorageMarkdownRenderer()
        return renderer.render_document(parse_storage_document(storage))


if __name__ == "__main__":
    unittest.main()
