"""Экспорт страниц Confluence в Markdown."""

from __future__ import annotations

from pathlib import Path
import re

from confluence_client import ConfluenceClient

from .exceptions import MarkdownBridgeError
from .models import (
    MarkdownExportResult,
    MarkdownTreeExportItem,
    MarkdownTreeExportResult,
)
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

    def export_page_tree_to_markdown_files(
        self,
        root_page_id: str,
        output_dir: str | Path,
    ) -> MarkdownTreeExportResult:
        """
        Выгрузить страницу и все её дочерние страницы в набор Markdown-файлов.

        Структура создаётся как дерево директорий:
        - корневая страница -> `<output_dir>/README.md`
        - дочерняя страница -> `<parent_dir>/<slug>--<page_id>/README.md`
        """

        root_page = self._client.find_page_by_id_with_storage(root_page_id)
        if not root_page.body or not root_page.body.storage:
            raise MarkdownBridgeError(
                f"У страницы {root_page_id} отсутствует body.storage, экспорт дерева невозможен."
            )

        base_dir = Path(output_dir).expanduser()
        base_dir.mkdir(parents=True, exist_ok=True)

        result = MarkdownTreeExportResult(
            root_page_id=root_page.id,
            root_title=root_page.title,
            output_dir=str(base_dir),
        )

        self._export_page_tree_node(
            page_id=root_page.id,
            title=root_page.title,
            target_dir=base_dir,
            depth=0,
            result=result,
        )
        return result

    def _export_page_tree_node(
        self,
        page_id: str,
        title: str,
        target_dir: Path,
        depth: int,
        result: MarkdownTreeExportResult,
    ) -> None:
        export_result = self.export_page_to_markdown(page_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / "README.md"
        output_path.write_text(export_result.markdown, encoding="utf-8")

        result.items.append(
            MarkdownTreeExportItem(
                page_id=export_result.page_id,
                title=export_result.title,
                depth=depth,
                output_path=str(output_path),
                warnings=export_result.warnings,
            )
        )
        result.warnings.extend(export_result.warnings)

        for child in self._iter_child_pages(page_id):
            child_dir = target_dir / self._directory_name_for_page(child.title, child.id)
            self._export_page_tree_node(
                page_id=child.id,
                title=child.title,
                target_dir=child_dir,
                depth=depth + 1,
                result=result,
            )

    def _iter_child_pages(self, page_id: str):
        start = 0
        limit = 100
        while True:
            response = self._client.list_child_pages(
                page_id=page_id,
                include_storage=False,
                start=start,
                limit=limit,
            )
            for page in response.results:
                yield page

            batch_size = len(response.results)
            if batch_size == 0:
                return

            next_link = response.links.next if response.links else None
            if next_link:
                start += batch_size
                continue

            if response.limit and batch_size >= response.limit:
                start += batch_size
                continue
            return

    @staticmethod
    def _directory_name_for_page(title: str, page_id: str) -> str:
        slug = re.sub(r"[^0-9A-Za-zА-Яа-я._-]+", "-", title.strip()).strip("-").lower()
        if not slug:
            slug = "page"
        return f"{slug}--{page_id}"


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


def export_page_tree_to_markdown_files(
    client: ConfluenceClient,
    root_page_id: str,
    output_dir: str | Path,
) -> MarkdownTreeExportResult:
    """
    Функциональный wrapper для выгрузки дерева страниц в Markdown-файлы.
    """

    return ConfluenceMarkdownExporter(client).export_page_tree_to_markdown_files(
        root_page_id=root_page_id,
        output_dir=output_dir,
    )
