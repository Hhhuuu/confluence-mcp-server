"""Импорт Markdown в Confluence storage format и публикация страниц."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable
from xml.etree import ElementTree as ET

import markdown as markdown_lib
from confluence_client import ConfluenceClient

from .exceptions import MarkdownBridgeError
from .models import (
    MarkdownAttachmentResult,
    MarkdownPreviewResult,
    MarkdownPublishResult,
)

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"
_TOC_MARKERS = {"[TOC]", "[[TOC]]"}
_MARKDOWN_IMAGE_PATTERN = re.compile(r"(!\[[^\]]*]\()([^)]+)(\))")


@dataclass(frozen=True)
class LocalAttachmentCandidate:
    """Локальное изображение, найденное в markdown-файле."""

    source_path: Path
    attachment_name: str


class ConfluenceMarkdownImporter:
    """
    Импортер Markdown в Confluence.

    Первая версия ориентирована на текст и стандартные markdown-конструкции.
    Результат публикуется как `body.storage` через существующий `confluence-client`.
    """

    def __init__(self, client: ConfluenceClient) -> None:
        self._client = client
        self._root: ET.Element | None = None

    def preview_markdown_to_storage(self, markdown_text: str) -> MarkdownPreviewResult:
        """
        Преобразовать Markdown в Confluence storage format без записи в Confluence.

        Args:
            markdown_text: Исходный Markdown.

        Returns:
            Содержимое storage format и предупреждения.
        """

        html = self._render_markdown_to_xhtml(markdown_text)
        storage, warnings = self._xhtml_to_storage(html)
        return MarkdownPreviewResult(storage=storage, warnings=warnings)

    def preview_markdown_file_to_storage(self, file_path: str | Path) -> MarkdownPreviewResult:
        """
        Преобразовать Markdown-файл в Confluence storage format без публикации.
        """

        path = Path(file_path).expanduser()
        markdown_text = self._read_markdown_file(path)
        prepared_markdown, _, local_warnings = self._prepare_markdown_file(markdown_text, path)
        result = self.preview_markdown_to_storage(prepared_markdown)
        result.source_path = str(path)
        result.warnings = [*local_warnings, *result.warnings]
        return result

    def create_page_from_markdown(
        self,
        title: str,
        markdown_text: str,
        parent_id: str,
        space_key: str,
    ) -> MarkdownPublishResult:
        """
        Создать страницу Confluence из Markdown.
        """

        preview = self.preview_markdown_to_storage(markdown_text)
        page = self._client.create_child_page(
            title=title,
            space_key=space_key,
            parent_id=parent_id,
            content=preview.storage,
        )
        return MarkdownPublishResult(
            title=page.title,
            page_id=page.page_id,
            page_url=page.page_url,
            attachments=[],
            warnings=preview.warnings,
        )

    def create_page_from_markdown_file(
        self,
        title: str,
        file_path: str | Path,
        parent_id: str,
        space_key: str,
    ) -> MarkdownPublishResult:
        """
        Создать страницу Confluence из Markdown-файла.
        """

        path = Path(file_path).expanduser()
        markdown_text = self._read_markdown_file(path)
        prepared_markdown, attachments, local_warnings = self._prepare_markdown_file(
            markdown_text,
            path,
        )
        result = self.create_page_from_markdown(
            title=title,
            markdown_text=prepared_markdown,
            parent_id=parent_id,
            space_key=space_key,
        )
        result.source_path = str(path)
        result.attachments = self._upload_local_attachments(result.page_id, attachments)
        result.warnings = [*local_warnings, *result.warnings]
        return result

    def update_page_from_markdown(
        self,
        page_id: str,
        markdown_text: str,
        title: str | None = None,
    ) -> MarkdownPublishResult:
        """
        Обновить существующую страницу Confluence содержимым из Markdown.
        """

        page = self._client.find_page_by_id_with_storage(page_id)
        if not page.version or not page.space:
            raise MarkdownBridgeError(
                f"Для страницы {page_id} не удалось определить version или space."
            )

        preview = self.preview_markdown_to_storage(markdown_text)
        next_version = page.version.number + 1
        page_data = self._client.update_page(
            title=title or page.title,
            space_key=page.space.key,
            page_id=page.id,
            version_number=next_version,
            content=preview.storage,
        )
        return MarkdownPublishResult(
            title=page_data.title,
            page_id=page_data.page_id,
            page_url=page_data.page_url,
            attachments=[],
            warnings=preview.warnings,
        )

    def update_page_from_markdown_file(
        self,
        page_id: str,
        file_path: str | Path,
        title: str | None = None,
    ) -> MarkdownPublishResult:
        """
        Обновить страницу Confluence содержимым из Markdown-файла.
        """

        path = Path(file_path).expanduser()
        markdown_text = self._read_markdown_file(path)
        prepared_markdown, attachments, local_warnings = self._prepare_markdown_file(
            markdown_text,
            path,
        )
        result = self.update_page_from_markdown(
            page_id=page_id,
            markdown_text=prepared_markdown,
            title=title,
        )
        result.source_path = str(path)
        result.attachments = self._upload_local_attachments(result.page_id, attachments)
        result.warnings = [*local_warnings, *result.warnings]
        return result

    def _render_markdown_to_xhtml(self, markdown_text: str) -> str:
        try:
            return markdown_lib.markdown(
                markdown_text,
                extensions=["extra", "fenced_code", "tables", "sane_lists"],
                output_format="xhtml",
            )
        except Exception as exc:
            raise MarkdownBridgeError(
                f"Не удалось преобразовать Markdown в XHTML: {exc}"
            ) from exc

    @staticmethod
    def _read_markdown_file(path: Path) -> str:
        if not path.exists():
            raise MarkdownBridgeError(f"Не найден Markdown-файл: {path}")
        if not path.is_file():
            raise MarkdownBridgeError(f"Путь Markdown-источника не является файлом: {path}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise MarkdownBridgeError(f"Не удалось прочитать Markdown-файл {path}: {exc}") from exc

    def _prepare_markdown_file(
        self,
        markdown_text: str,
        source_path: Path,
    ) -> tuple[str, list[LocalAttachmentCandidate], list[str]]:
        source_dir = source_path.parent
        attachments: list[LocalAttachmentCandidate] = []
        warnings: list[str] = []
        filename_to_source: dict[str, Path] = {}

        def replace_image(match: re.Match[str]) -> str:
            raw_target = match.group(2).strip()
            image_target = self._extract_image_target(raw_target)
            if not image_target or self._is_remote_or_confluence_target(image_target):
                return match.group(0)

            resolved_path = self._resolve_local_image_path(source_dir, image_target)
            attachment_name = resolved_path.name
            existing_source = filename_to_source.get(attachment_name)
            if existing_source and existing_source != resolved_path:
                raise MarkdownBridgeError(
                    "В одном markdown-файле найдены разные локальные изображения с одинаковым именем "
                    f"вложения '{attachment_name}': {existing_source} и {resolved_path}. "
                    "Переименуйте один из файлов, чтобы избежать конфликта."
                )

            filename_to_source[attachment_name] = resolved_path
            attachments.append(
                LocalAttachmentCandidate(
                    source_path=resolved_path,
                    attachment_name=attachment_name,
                )
            )
            warnings.append(
                "Локальное изображение "
                f"{resolved_path} будет загружено во вложения страницы как {attachment_name}."
            )
            return f"{match.group(1)}attachment:{attachment_name}{match.group(3)}"

        prepared = _MARKDOWN_IMAGE_PATTERN.sub(replace_image, markdown_text)
        unique_attachments = list(self._deduplicate_attachments(attachments))
        return prepared, unique_attachments, warnings

    @staticmethod
    def _extract_image_target(raw_target: str) -> str:
        if not raw_target:
            return ""

        target = raw_target.strip()
        if target.startswith("<") and ">" in target:
            return target[1 : target.index(">")].strip()
        if " " in target:
            return target.split(" ", 1)[0].strip()
        return target

    @staticmethod
    def _is_remote_or_confluence_target(target: str) -> bool:
        lowered = target.lower()
        return (
            lowered.startswith("http://")
            or lowered.startswith("https://")
            or lowered.startswith("attachment:")
            or lowered.startswith("data:")
            or lowered.startswith("file://")
        )

    @staticmethod
    def _resolve_local_image_path(source_dir: Path, target: str) -> Path:
        candidate = Path(target).expanduser()
        if not candidate.is_absolute():
            candidate = source_dir / candidate
        candidate = candidate.resolve()

        if not candidate.exists():
            raise MarkdownBridgeError(
                f"Не найден локальный файл изображения из markdown: {candidate}"
            )
        if not candidate.is_file():
            raise MarkdownBridgeError(
                f"Путь локального изображения не является файлом: {candidate}"
            )
        return candidate

    @staticmethod
    def _deduplicate_attachments(
        attachments: Iterable[LocalAttachmentCandidate],
    ) -> Iterable[LocalAttachmentCandidate]:
        seen: set[tuple[str, str]] = set()
        for attachment in attachments:
            key = (attachment.attachment_name, str(attachment.source_path))
            if key in seen:
                continue
            seen.add(key)
            yield attachment

    def _upload_local_attachments(
        self,
        page_id: str,
        attachments: Iterable[LocalAttachmentCandidate],
    ) -> list[MarkdownAttachmentResult]:
        uploaded: list[MarkdownAttachmentResult] = []
        for attachment in attachments:
            action, uploaded_attachment = self._client.upsert_attachment(
                page_id=page_id,
                file_path=attachment.source_path,
                comment="Загружено из markdown-файла",
            )
            uploaded.append(
                MarkdownAttachmentResult(
                    filename=attachment.attachment_name,
                    source_path=str(attachment.source_path),
                    attachment_id=uploaded_attachment.id,
                    action=action,
                )
            )
        return uploaded

    def _xhtml_to_storage(self, xhtml: str) -> tuple[str, list[str]]:
        wrapped = (
            "<root "
            'xmlns:ac="urn:ac"'
            ' xmlns:ri="urn:ri"'
            ">"
            f"{xhtml}"
            "</root>"
        )
        try:
            root = ET.fromstring(wrapped)
        except ET.ParseError as exc:
            raise MarkdownBridgeError(
                f"Не удалось распарсить XHTML после markdown-конвертации: {exc}"
            ) from exc

        self._root = root
        warnings: list[str] = []
        self._transform_tree(root, warnings)
        storage = self._serialize_inner_xml(root)
        return storage, warnings

    def _transform_tree(self, element: ET.Element, warnings: list[str]) -> None:
        for child in list(element):
            self._transform_tree(child, warnings)

        name = self._local_name(element.tag)

        if name == "p":
            text = self._collapse_text(element)
            if text.strip() in _TOC_MARKERS:
                macro = self._build_toc_macro()
                self._replace_element_in_parent(element, macro)
                return

        if name == "img":
            image = self._convert_img_to_confluence_image(element, warnings)
            if image is not None:
                self._replace_element_in_parent(element, image)
                return

    def _convert_img_to_confluence_image(
        self,
        element: ET.Element,
        warnings: list[str],
    ) -> ET.Element | None:
        src = element.attrib.get("src", "").strip()
        if not src:
            warnings.append("Markdown-изображение без src было пропущено.")
            return None

        image = ET.Element(f"{{{_AC_URI}}}image")
        alt = element.attrib.get("alt", "").strip()
        if alt:
            image.attrib[f"{{{_AC_URI}}}alt"] = alt

        if src.startswith("attachment:"):
            attachment = ET.SubElement(image, f"{{{_RI_URI}}}attachment")
            attachment.attrib[f"{{{_RI_URI}}}filename"] = src.removeprefix("attachment:")
            return image

        resource = ET.SubElement(image, f"{{{_RI_URI}}}url")
        resource.attrib[f"{{{_RI_URI}}}value"] = src
        return image

    @staticmethod
    def _build_toc_macro() -> ET.Element:
        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "toc"
        return macro

    def _replace_element_in_parent(self, old: ET.Element, new: ET.Element) -> None:
        parent = self._find_parent(old)
        if parent is None:
            return

        index = list(parent).index(old)
        new.tail = old.tail
        parent.remove(old)
        parent.insert(index, new)

    def _find_parent(self, target: ET.Element) -> ET.Element | None:
        if self._root is None:
            raise MarkdownBridgeError("Внутренняя ошибка: root дерева импорта не установлен.")

        for parent in self._iter_parents(self._root):
            for child in list(parent):
                if child is target:
                    return parent
        return None

    def _iter_parents(self, element: ET.Element):
        yield element
        for child in list(element):
            yield from self._iter_parents(child)

    def _serialize_inner_xml(self, root: ET.Element) -> str:
        ET.register_namespace("ac", _AC_URI)
        ET.register_namespace("ri", _RI_URI)
        return "".join(
            ET.tostring(child, encoding="unicode", method="xml") for child in list(root)
        )

    @staticmethod
    def _collapse_text(element: ET.Element) -> str:
        parts: list[str] = []
        if element.text:
            parts.append(element.text)
        for child in list(element):
            parts.append(ConfluenceMarkdownImporter._collapse_text(child))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)

    @staticmethod
    def _local_name(tag: str) -> str:
        if tag.startswith("{") and "}" in tag:
            return tag.split("}", 1)[1]
        return tag


def preview_markdown_to_storage(
    client: ConfluenceClient,
    markdown_text: str,
) -> MarkdownPreviewResult:
    """
    Функциональный wrapper для preview markdown -> storage.
    """

    return ConfluenceMarkdownImporter(client).preview_markdown_to_storage(markdown_text)
