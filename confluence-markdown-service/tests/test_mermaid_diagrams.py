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

MERMAID_ER_DIAGRAM = """```mermaid {title="database-schema"}
erDiagram
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER {
        int id PK
        string name
    }
    ORDER {
        int id PK
        int customer_id FK
    }
```
"""


class FakeMermaidClient:
    def __init__(self, existing_attachments: set[str] | None = None) -> None:
        self.updated_storage = ""
        self.existing_attachments = set(existing_attachments or ())
        self.uploaded_content: dict[str, bytes] = {}
        self.uploaded_content_types: dict[str, str] = {}
        self.events: list[str] = []

    def create_child_page(self, **kwargs) -> PageData:
        self.events.append("create_page")
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
        if filename not in self.existing_attachments:
            return None
        return AttachmentSummary(
            id="att-1",
            title=filename,
            version=VersionInfo(number=2),
        )

    def update_page(self, **kwargs) -> PageData:
        self.events.append("update_page")
        self.updated_storage = kwargs["content"]
        return PageData(title=kwargs["title"], page_id=kwargs["page_id"], page_url="https://example/100")

    def upsert_attachment(
        self,
        page_id: str,
        file_path: Path,
        comment: str,
        content_type: str | None = None,
    ):
        self.events.append("upload_attachment")
        path = Path(file_path)
        action = "updated" if path.name in self.existing_attachments else "created"
        self.existing_attachments.add(path.name)
        self.uploaded_content[path.name] = path.read_bytes()
        self.uploaded_content_types[path.name] = content_type or ""
        return action, AttachmentSummary(id="att-1", title=path.name)


class MermaidImportTests(unittest.TestCase):
    def test_server_extension_creates_attachment_macro(self) -> None:
        importer = ConfluenceMarkdownImporter(
            None,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.preview_markdown_to_storage(MERMAID_MARKDOWN)

        self.assertIn('ac:name="mermaid-cloud"', result.storage)
        self.assertIn('ac:name="filename">mermaid-diagram-1', result.storage)
        self.assertIn('ac:name="format">svg', result.storage)
        self.assertIn('ac:name="revision">1', result.storage)

    def test_title_uses_plugin_compatible_attachment_basename(self) -> None:
        importer = ConfluenceMarkdownImporter(
            None,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.preview_markdown_to_storage(
            MERMAID_ER_DIAGRAM.replace('title="database-schema"', 'title="database.schema.mmd"')
        )

        self.assertIn('ac:name="filename">database', result.storage)
        self.assertNotIn("database.schema.mmd", result.storage)

    def test_cloud_does_not_create_mermaid_cloud_macro(self) -> None:
        importer = ConfluenceMarkdownImporter(
            None,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": False}},
        )

        result = importer.preview_markdown_to_storage(MERMAID_MARKDOWN)

        self.assertNotIn("mermaid-cloud", result.storage)

    def test_update_uses_next_attachment_revision_and_uploads_source(self) -> None:
        client = FakeMermaidClient({"mermaid-diagram-1"})
        importer = ConfluenceMarkdownImporter(
            client,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.update_page_from_markdown("100", MERMAID_MARKDOWN)

        self.assertIn('ac:name="revision">3', client.updated_storage)
        self.assertEqual(
            client.uploaded_content["mermaid-diagram-1"],
            b"flowchart LR\n    A --> B\n",
        )
        self.assertEqual(
            client.uploaded_content_types["mermaid-diagram-1"],
            "text/plain",
        )
        self.assertEqual(
            client.uploaded_content_types["mermaid-diagram-1.svg"],
            "image/svg+xml",
        )
        self.assertEqual(
            client.uploaded_content_types["mermaid-diagram-1.png"],
            "image/png",
        )
        self.assertTrue(client.uploaded_content["mermaid-diagram-1.svg"].startswith(b"<svg"))
        self.assertTrue(client.uploaded_content["mermaid-diagram-1.png"].startswith(b"\x89PNG"))
        self.assertEqual(result.attachments[0].filename, "mermaid-diagram-1")
        self.assertEqual(
            client.events,
            [
                "upload_attachment",
                "upload_attachment",
                "upload_attachment",
                "update_page",
            ],
        )

    def test_update_preserves_existing_plugin_preview_assets(self) -> None:
        client = FakeMermaidClient(
            {"mermaid-diagram-1", "mermaid-diagram-1.svg", "mermaid-diagram-1.png"}
        )
        importer = ConfluenceMarkdownImporter(
            client,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.update_page_from_markdown("100", MERMAID_MARKDOWN)

        self.assertEqual(set(client.uploaded_content), {"mermaid-diagram-1"})
        self.assertEqual(
            [item.filename for item in result.attachments],
            ["mermaid-diagram-1"],
        )
        self.assertEqual(client.events, ["upload_attachment", "update_page"])

    def test_create_refreshes_er_diagram_after_attachment_upload(self) -> None:
        client = FakeMermaidClient()
        importer = ConfluenceMarkdownImporter(
            client,  # type: ignore[arg-type]
            builtin_extension_options={"mermaid_diagrams": {"enabled": True}},
        )

        result = importer.create_page_from_markdown(
            title="Database schema",
            markdown_text=MERMAID_ER_DIAGRAM,
            parent_id="10",
            space_key="DOC",
        )

        self.assertEqual(
            client.events,
            [
                "create_page",
                "upload_attachment",
                "upload_attachment",
                "upload_attachment",
                "update_page",
            ],
        )
        self.assertIn('ac:name="mermaid-cloud"', client.updated_storage)
        self.assertIn('ac:name="filename">database-schema', client.updated_storage)
        self.assertIn(b"erDiagram", client.uploaded_content["database-schema"])
        self.assertEqual(
            [item.filename for item in result.attachments],
            ["database-schema", "database-schema.svg", "database-schema.png"],
        )


class FakeMermaidExportClient:
    def find_page_by_id_with_storage(self, page_id: str) -> PageSummary:
        storage = (
            '<ac:structured-macro ac:name="mermaid-cloud">'
            '<ac:parameter ac:name="filename">diagram</ac:parameter>'
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
