"""Тесты Mermaid Diagrams for Confluence (Server/DC)."""

from __future__ import annotations

from pathlib import Path
import unittest

from confluence_client import AttachmentSummary, PageData, PageSummary
from confluence_client.models import SpaceRef, VersionInfo
from confluence_markdown_service import (
    ConfluenceMarkdownExporter,
    ConfluenceMarkdownImporter,
)


MERMAID_MARKDOWN = """```mermaid
flowchart LR
    A --> B
```
"""


class FakeMermaidClient:
    def __init__(self) -> None:
        self.updated_storage = ""
        self.uploaded_content = ""
        self.uploaded_content_type = ""

    def create_child_page(self, **kwargs) -> PageData:
        self.updated_storage = kwargs["content"]
        return PageData(title=kwargs["title"], page_id="100", page_url="https://example/100")

    def find_page_by_id_with_storage(self, page_id: str) -> PageSummary:
        return PageSummary(
            id=page_id,
            title="Page",
            type="page",
            version=VersionInfo(number=4),
            space=SpaceRef(key="DOC"),
        )

    def find_attachment_by_filename(self, page_id: str, filename: str):
        return AttachmentSummary(
            id="att-1",
            title=filename,
            version=VersionInfo(number=2),
        )

    def update_page(self, **kwargs) -> PageData:
        self.updated_storage = kwargs["content"]
        return PageData(title=kwargs["title"], page_id=kwargs["page_id"], page_url="https://example/100")

    def upsert_attachment(
        self,
        page_id: str,
        file_path: Path,
        comment: str,
        content_type: str | None = None,
    ):
        self.uploaded_content = Path(file_path).read_text(encoding="utf-8")
        self.uploaded_content_type = content_type or ""
        return "updated", AttachmentSummary(id="att-1", title=Path(file_path).name)


class MermaidImportTests(unittest.TestCase):
    def test_server_extension_creates_attachment_macro(self) -> None:
        importer = ConfluenceMarkdownImporter(
            None,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.preview_markdown_to_storage(MERMAID_MARKDOWN)

        self.assertIn('ac:name="mermaid-cloud"', result.storage)
        self.assertIn('ac:name="filename">mermaid-diagram-1.mmd', result.storage)
        self.assertIn('ac:name="revision">1', result.storage)

    def test_cloud_does_not_create_mermaid_cloud_macro(self) -> None:
        importer = ConfluenceMarkdownImporter(
            None,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": False}},
        )

        result = importer.preview_markdown_to_storage(MERMAID_MARKDOWN)

        self.assertNotIn("mermaid-cloud", result.storage)

    def test_update_uses_next_attachment_revision_and_uploads_source(self) -> None:
        client = FakeMermaidClient()
        importer = ConfluenceMarkdownImporter(
            client,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.update_page_from_markdown("100", MERMAID_MARKDOWN)

        self.assertIn('ac:name="revision">3', client.updated_storage)
        self.assertEqual(client.uploaded_content, "flowchart LR\n    A --> B\n")
        self.assertEqual(client.uploaded_content_type, "text/plain")
        self.assertEqual(result.attachments[0].filename, "mermaid-diagram-1.mmd")


class FakeMermaidExportClient:
    def find_page_by_id_with_storage(self, page_id: str) -> PageSummary:
        storage = (
            '<ac:structured-macro ac:name="mermaid-cloud">'
            '<ac:parameter ac:name="filename">diagram.mmd</ac:parameter>'
            '<ac:parameter ac:name="revision">2</ac:parameter>'
            '</ac:structured-macro>'
        )
        from confluence_client.models import BodyValue, StorageValue

        return PageSummary(
            id=page_id,
            title="Diagram",
            body=BodyValue(storage=StorageValue(value=storage)),
        )

    def find_attachment_by_filename(self, page_id: str, filename: str):
        return AttachmentSummary(id="att-1", title=filename)

    def download_attachment(self, attachment, output_path):
        Path(output_path).write_text("sequenceDiagram\nA->>B: Hi\n", encoding="utf-8")
        return Path(output_path)


class MermaidExportTests(unittest.TestCase):
    def test_exports_attachment_source_as_mermaid_fence(self) -> None:
        exporter = ConfluenceMarkdownExporter(
            FakeMermaidExportClient(),  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = exporter.export_page_to_markdown("100")

        self.assertIn("```mermaid", result.markdown)
        self.assertIn("A->>B: Hi", result.markdown)


if __name__ == "__main__":
    unittest.main()
