"""Экспорт страниц Confluence в Markdown."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence
from urllib.parse import quote

from confluence_client import ConfluenceClient

from .extensions import ConfluenceMarkdownExtension
from .exceptions import MarkdownBridgeError
from .models import (
    MarkdownExportResult,
    MarkdownExportedAttachmentResult,
    MarkdownTreeExportItem,
    MarkdownTreeExportResult,
)
from .storage_normalizer import parse_storage_document
from .storage_renderer import StorageMarkdownRenderer

_MARKDOWN_TARGET_PATTERN = re.compile(r"(?P<prefix>!?\[[^\]]*]\()(?P<target>[^)]+)(?P<suffix>\))")


@dataclass(frozen=True)
class AttachmentReference:
    filename: str
    is_image: bool


class ConfluenceMarkdownExporter:
    """
    Экспортёр страниц Confluence в Markdown.

    Экспорт ориентирован на текст и базовые markdown-конструкции.
    Confluence-макросы и сложные визуальные блоки в первой версии
    могут быть упрощены или пропущены с предупреждением.
    """

    def __init__(
        self,
        client: ConfluenceClient,
        *,
        enabled_extensions: Sequence[str] | None = None,
        extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
    ) -> None:
        """
        Создать экспортёр с указанным клиентом.

        Args:
            client: Клиент Confluence.
        """

        self._client = client
        self._enabled_extensions = (
            list(enabled_extensions) if enabled_extensions is not None else None
        )
        self._extra_extensions = list(extra_extensions or [])

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
        renderer = StorageMarkdownRenderer(
            enabled_extensions=self._enabled_extensions,
            extra_extensions=self._extra_extensions,
        )
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
        export_result = self._materialize_markdown_bundle(
            page_id=page_id,
            export_result=export_result,
            output_path=output_path,
        )

        result.items.append(
            MarkdownTreeExportItem(
                page_id=export_result.page_id,
                title=export_result.title,
                depth=depth,
                output_path=str(output_path),
                attachments=export_result.attachments,
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

    def _materialize_markdown_bundle(
        self,
        *,
        page_id: str,
        export_result: MarkdownExportResult,
        output_path: Path,
    ) -> MarkdownExportResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        references = self._collect_attachment_references(export_result.markdown)
        attachments_dir = output_path.parent / "attachments"
        attachments, attachment_warnings = self._download_referenced_attachments(
            page_id,
            references,
            attachments_dir,
        )
        rewritten_markdown = self._rewrite_attachment_targets(
            export_result.markdown,
            attachments_dir_name=attachments_dir.name,
            available_filenames={attachment.filename for attachment in attachments},
        )

        output_path.write_text(rewritten_markdown, encoding="utf-8")
        export_result.markdown = rewritten_markdown
        export_result.output_path = str(output_path)
        if attachments:
            export_result.attachments_dir = str(attachments_dir)
        export_result.attachments = attachments
        export_result.warnings.extend(attachment_warnings)
        return export_result

    def _collect_attachment_references(self, markdown_text: str) -> list[AttachmentReference]:
        references: list[AttachmentReference] = []
        seen: set[tuple[str, bool]] = set()
        for match in _MARKDOWN_TARGET_PATTERN.finditer(markdown_text):
            target = match.group("target").strip()
            if not target.startswith("attachment:"):
                continue
            filename = target.removeprefix("attachment:")
            if not filename:
                continue
            reference = AttachmentReference(
                filename=filename,
                is_image=match.group("prefix").startswith("!["),
            )
            key = (reference.filename, reference.is_image)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
        return references

    def _download_referenced_attachments(
        self,
        page_id: str,
        references: list[AttachmentReference],
        attachments_dir: Path,
    ) -> tuple[list[MarkdownExportedAttachmentResult], list[str]]:
        if not references:
            return [], []

        attachment_map = self._list_attachments_by_filename(page_id)
        exported: list[MarkdownExportedAttachmentResult] = []
        warnings: list[str] = []

        for reference in references:
            attachment = attachment_map.get(reference.filename)
            if attachment is None:
                warnings.append(
                    f"Во вложениях страницы не найден файл {reference.filename}, "
                    "поэтому ссылка в markdown оставлена в формате attachment:..."
                )
                continue

            attachments_dir.mkdir(parents=True, exist_ok=True)
            output_path = attachments_dir / reference.filename
            saved_path = self._client.download_attachment(attachment, output_path)
            exported.append(
                MarkdownExportedAttachmentResult(
                    filename=reference.filename,
                    output_path=str(saved_path),
                    attachment_id=attachment.id,
                    action="downloaded",
                )
            )

        return exported, warnings

    def _list_attachments_by_filename(self, page_id: str) -> dict[str, object]:
        attachment_map: dict[str, object] = {}
        start = 0
        limit = 100
        while True:
            response = self._client.list_attachments(page_id=page_id, start=start, limit=limit)
            for attachment in response.results:
                attachment_map[attachment.title] = attachment

            batch_size = len(response.results)
            if batch_size == 0:
                return attachment_map

            next_link = response.links.next if response.links else None
            if next_link:
                start += batch_size
                continue

            if response.limit and batch_size >= response.limit:
                start += batch_size
                continue
            return attachment_map

    @staticmethod
    def _rewrite_attachment_targets(
        markdown_text: str,
        *,
        attachments_dir_name: str,
        available_filenames: set[str],
    ) -> str:
        def replace(match: re.Match[str]) -> str:
            target = match.group("target").strip()
            if not target.startswith("attachment:"):
                return match.group(0)
            filename = target.removeprefix("attachment:")
            if filename not in available_filenames:
                return match.group(0)
            relative_target = f"./{attachments_dir_name}/{quote(filename)}"
            return f"{match.group('prefix')}{relative_target}{match.group('suffix')}"

        return _MARKDOWN_TARGET_PATTERN.sub(replace, markdown_text)


def export_page_to_markdown(
    client: ConfluenceClient,
    page_id: str,
    *,
    enabled_extensions: Sequence[str] | None = None,
    extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
) -> MarkdownExportResult:
    """
    Функциональный wrapper поверх `ConfluenceMarkdownExporter`.

    Args:
        client: Клиент Confluence.
        page_id: Идентификатор страницы.
    """

    return ConfluenceMarkdownExporter(
        client,
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
    ).export_page_to_markdown(page_id)


def export_page_to_markdown_file(
    client: ConfluenceClient,
    page_id: str,
    output_path: str | Path,
    *,
    enabled_extensions: Sequence[str] | None = None,
    extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
) -> MarkdownExportResult:
    """
    Выгрузить страницу Confluence в Markdown-файл на диске.
    """

    result = ConfluenceMarkdownExporter(
        client,
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
    ).export_page_to_markdown(page_id)
    path = Path(output_path).expanduser()
    return ConfluenceMarkdownExporter(
        client,
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
    )._materialize_markdown_bundle(
        page_id=page_id,
        export_result=result,
        output_path=path,
    )


def export_page_tree_to_markdown_files(
    client: ConfluenceClient,
    root_page_id: str,
    output_dir: str | Path,
    *,
    enabled_extensions: Sequence[str] | None = None,
    extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
) -> MarkdownTreeExportResult:
    """
    Функциональный wrapper для выгрузки дерева страниц в Markdown-файлы.
    """

    return ConfluenceMarkdownExporter(
        client,
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
    ).export_page_tree_to_markdown_files(
        root_page_id=root_page_id,
        output_dir=output_dir,
    )
