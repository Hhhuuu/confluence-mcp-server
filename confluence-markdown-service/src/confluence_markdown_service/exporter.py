"""Экспорт страниц Confluence в Markdown."""

from __future__ import annotations

from pathlib import Path

from confluence_client import ConfluenceClient

from .exceptions import MarkdownBridgeError
from .models import MarkdownExportResult
from .storage_normalizer import parse_storage_document
from .storage_renderer import StorageMarkdownRenderer


class ConfluenceMarkdownExporter:
    """
    Экспортёр страниц Confluence в Markdown.

    Экспорт ориентирован на текст и базовые markdown-конструкции.
    Confluence-макросы и сложные визуальные блоки в первой версии
    могут быть упрощены или пропущены с предупреждением.
    """

    def __init__(self, client: ConfluenceClient) -> None:
        """
        Создать экспортёр с указанным клиентом.

        Args:
            client: Клиент Confluence.
        """

        self._client = client

    def export_page_to_markdown(self, page_id: str) -> MarkdownExportResult:
        """
        Выгрузить страницу Confluence в Markdown.

        Args:
            page_id: Идентификатор страницы Confluence.

        Returns:
            Результат экспорта со сгенерированным Markdown и предупреждениями.

        Raises:
            MarkdownBridgeError: Если у страницы отсутствует `body.storage`.
        """

        page = self._client.find_page_by_id_with_storage(page_id)
        if not page.body or not page.body.storage:
            raise MarkdownBridgeError(
                f"У страницы {page_id} отсутствует body.storage, экспорт в Markdown невозможен."
            )

        root = parse_storage_document(page.body.storage.value)
        renderer = StorageMarkdownRenderer()
        markdown = renderer.render_document(root)

        return MarkdownExportResult(
            page_id=page.id,
            title=page.title,
            space_key=page.space.key if page.space else None,
            markdown=markdown,
            warnings=renderer.warnings,
        )


def export_page_to_markdown(client: ConfluenceClient, page_id: str) -> MarkdownExportResult:
    """
    Функциональный wrapper поверх `ConfluenceMarkdownExporter`.

    Args:
        client: Клиент Confluence.
        page_id: Идентификатор страницы.
    """

    return ConfluenceMarkdownExporter(client).export_page_to_markdown(page_id)


def export_page_to_markdown_file(
    client: ConfluenceClient,
    page_id: str,
    output_path: str | Path,
) -> MarkdownExportResult:
    """
    Выгрузить страницу Confluence в Markdown-файл на диске.
    """

    result = ConfluenceMarkdownExporter(client).export_page_to_markdown(page_id)
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.markdown, encoding="utf-8")
    result.output_path = str(path)
    return result
