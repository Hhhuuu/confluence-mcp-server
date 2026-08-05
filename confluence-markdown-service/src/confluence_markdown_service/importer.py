"""Импорт Markdown в Confluence storage format и публикация страниц."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Sequence
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

import markdown as markdown_lib
from confluence_client import ConfluenceClient

from .extensions import ConfluenceMarkdownExtension, build_markdown_extension_registry
from .exceptions import MarkdownBridgeError
from .models import (
    MarkdownAttachmentResult,
    MarkdownPreviewResult,
    MarkdownPublishResult,
)

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"
_MARKDOWN_IMAGE_PATTERN = re.compile(r"(!\[[^\]]*]\()([^)]+)(\))")
_MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)(\[[^\]]*]\()([^)]+)(\))")
_HTML_IMAGE_SRC_PATTERN = re.compile(
    r'(?P<prefix><img\b[^>]*?\bsrc=")(?P<target>[^"]+)(?P<suffix>"[^>]*?/?>)',
    re.IGNORECASE,
)
_MARKDOWN_LIST_ITEM_PATTERN = re.compile(
    r"^(?P<indent> {0,3})(?:[-+*]|\d+[.)])\s+\S"
)
_ALLOWED_HTML_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "code": {"class", "title"},
    "pre": {"data-code-title", "data-code-language"},
    "blockquote": {"data-admonition"},
    "time": {"datetime", "datatime"},
    "status": {"color", "colour", "subtle"},
    "table": set(),
    "thead": set(),
    "tbody": set(),
    "tfoot": set(),
    "tr": set(),
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "caption": set(),
}


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

    def __init__(
        self,
        client: ConfluenceClient,
        *,
        enabled_extensions: Sequence[str] | None = None,
        extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
        builtin_extension_options: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._client = client
        self._root: ET.Element | None = None
        self._registry = build_markdown_extension_registry(
            enabled_extensions=enabled_extensions,
            extra_extensions=extra_extensions,
            builtin_extension_options=builtin_extension_options,
        )
        self.warnings: list[str] = []

    def preview_markdown_to_storage(self, markdown_text: str) -> MarkdownPreviewResult:
        """
        Преобразовать Markdown в Confluence storage format без записи в Confluence.

        Args:
            markdown_text: Исходный Markdown.

        Returns:
            Содержимое storage format и предупреждения.
        """

        self.warnings = []
        prepared_markdown = self._registry.preprocess_markdown(markdown_text)
        html = self._render_markdown_to_xhtml(prepared_markdown)
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
                self._normalize_list_boundaries(markdown_text),
                extensions=["extra", "fenced_code", "tables", "sane_lists"],
                output_format="xhtml",
            )
        except Exception as exc:
            raise MarkdownBridgeError(
                f"Не удалось преобразовать Markdown в XHTML: {exc}"
            ) from exc

    @staticmethod
    def _normalize_list_boundaries(markdown_text: str) -> str:
        """Отделить начало списка от предыдущего абзаца.

        Python Markdown требует пустую строку перед списком, хотя
        распространённый Markdown часто пишут без неё.
        """

        lines = markdown_text.splitlines(keepends=True)
        normalized: list[str] = []
        in_fence = False
        previous_was_list_item = False

        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence

            is_list_item = not in_fence and bool(
                _MARKDOWN_LIST_ITEM_PATTERN.match(line.rstrip("\r\n"))
            )
            previous_is_blank = not normalized or not normalized[-1].strip()
            if is_list_item and not previous_is_blank and not previous_was_list_item:
                newline = "\r\n" if line.endswith("\r\n") else "\n"
                normalized.append(newline)

            normalized.append(line)
            previous_was_list_item = is_list_item

        return "".join(normalized)

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

        def register_local_target(raw_target: str) -> tuple[str, str] | None:
            local_target = self._extract_markdown_target(raw_target)
            if not local_target or self._is_remote_or_confluence_target(local_target):
                return None

            resolved_path = self._resolve_local_path(source_dir, local_target)
            attachment_name = resolved_path.name
            existing_source = filename_to_source.get(attachment_name)
            if existing_source and existing_source != resolved_path:
                raise MarkdownBridgeError(
                    "В одном markdown-файле найдены разные локальные файлы с одинаковым именем "
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
                "Локальный файл "
                f"{resolved_path} будет загружен во вложения страницы как {attachment_name}."
            )
            quoted_name = quote(attachment_name)
            return attachment_name, f"attachment:{quoted_name}"

        def replace_image(match: re.Match[str]) -> str:
            registered = register_local_target(match.group(2).strip())
            if registered is None:
                return match.group(0)
            _, attachment_target = registered
            return f"{match.group(1)}{attachment_target}{match.group(3)}"

        def replace_link(match: re.Match[str]) -> str:
            registered = register_local_target(match.group(2).strip())
            if registered is None:
                return match.group(0)
            _, attachment_target = registered
            return f"{match.group(1)}{attachment_target}{match.group(3)}"

        def replace_html_image(match: re.Match[str]) -> str:
            registered = register_local_target(match.group("target").strip())
            if registered is None:
                return match.group(0)
            _, attachment_target = registered
            return f'{match.group("prefix")}{attachment_target}{match.group("suffix")}'

        prepared = _MARKDOWN_IMAGE_PATTERN.sub(replace_image, markdown_text)
        prepared = _MARKDOWN_LINK_PATTERN.sub(replace_link, prepared)
        prepared = _HTML_IMAGE_SRC_PATTERN.sub(replace_html_image, prepared)
        unique_attachments = list(self._deduplicate_attachments(attachments))
        return prepared, unique_attachments, warnings

    @staticmethod
    def _extract_markdown_target(raw_target: str) -> str:
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
    def _resolve_local_path(source_dir: Path, target: str) -> Path:
        candidate = Path(unquote(target)).expanduser()
        if not candidate.is_absolute():
            candidate = source_dir / candidate
        candidate = candidate.resolve()

        if not candidate.exists():
            raise MarkdownBridgeError(
                f"Не найден локальный файл из markdown: {candidate}"
            )
        if not candidate.is_file():
            raise MarkdownBridgeError(
                f"Путь локального файла не является файлом: {candidate}"
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
        self._transform_tree(root)
        storage = self._serialize_inner_xml(root)
        return storage, list(self.warnings)

    def _transform_tree(self, element: ET.Element) -> None:
        for child in list(element):
            self._transform_tree(child)

        for extension in self._registry.extensions:
            result = extension.transform_import_element(self, element)
            if not result.handled:
                continue
            if result.replacement is not None:
                self._replace_element_in_parent(element, result.replacement)
            return

        name = self._local_name(element.tag)

        if name == "img":
            image = self._convert_img_to_confluence_image(element)
            if image is not None:
                self._replace_element_in_parent(element, image)
                return

        if name == "a":
            link = self._convert_anchor_to_confluence_link(element)
            if link is not None:
                self._replace_element_in_parent(element, link)
                return

        if name == "input":
            replacement = self._convert_input_element(element)
            if replacement is not None:
                self._replace_element_in_parent(element, replacement)
                return

        if name == "details":
            replacement = self._convert_details_element(element)
            if replacement is not None:
                self._replace_element_in_parent(element, replacement)
                return

        if name == "summary":
            replacement = self._convert_summary_element(element)
            if replacement is not None:
                self._replace_element_in_parent(element, replacement)
                return

        self._sanitize_html_element_attributes(element)

    def _convert_img_to_confluence_image(
        self,
        element: ET.Element,
    ) -> ET.Element | None:
        src = element.attrib.get("src", "").strip()
        if not src:
            self._warn("Markdown-изображение без src было пропущено.")
            return None

        image = ET.Element(f"{{{_AC_URI}}}image")
        alt = element.attrib.get("alt", "").strip()
        if alt:
            image.attrib[f"{{{_AC_URI}}}alt"] = alt
        width = (element.attrib.get("width") or "").strip()
        height = (element.attrib.get("height") or "").strip()
        if width:
            image.attrib[f"{{{_AC_URI}}}width"] = width
        if height:
            image.attrib[f"{{{_AC_URI}}}height"] = height

        if src.startswith("attachment:"):
            attachment = ET.SubElement(image, f"{{{_RI_URI}}}attachment")
            attachment.attrib[f"{{{_RI_URI}}}filename"] = src.removeprefix("attachment:")
            return image

        resource = ET.SubElement(image, f"{{{_RI_URI}}}url")
        resource.attrib[f"{{{_RI_URI}}}value"] = src
        return image

    def _convert_anchor_to_confluence_link(
        self,
        element: ET.Element,
    ) -> ET.Element | None:
        href = element.attrib.get("href", "").strip()
        if not href.startswith("attachment:"):
            return None

        filename = unquote(href.removeprefix("attachment:"))
        if not filename:
            self._warn("Markdown-ссылка на вложение без имени файла была пропущена.")
            return None

        link = ET.Element(f"{{{_AC_URI}}}link")
        attachment = ET.SubElement(link, f"{{{_RI_URI}}}attachment")
        attachment.attrib[f"{{{_RI_URI}}}filename"] = filename

        link_text = self._collapse_text(element).strip()
        if link_text and link_text != href:
            body = ET.SubElement(link, f"{{{_AC_URI}}}plain-text-link-body")
            body.text = link_text

        return link

    def _convert_input_element(self, element: ET.Element) -> ET.Element | None:
        input_type = (element.attrib.get("type") or "").strip().lower()
        if input_type != "checkbox":
            return None

        checked = (element.attrib.get("checked") or "").strip().lower()
        marker = "[x]" if checked in {"checked", "true", "1", "yes", "on"} else "[ ]"

        span = ET.Element("span")
        span.text = marker
        return span

    def _convert_details_element(self, element: ET.Element) -> ET.Element | None:
        container = ET.Element("div")
        has_content = False

        for child in list(element):
            element.remove(child)
            container.append(child)
            has_content = True

        details_text = (element.text or "").strip()
        if details_text:
            paragraph = ET.Element("p")
            paragraph.text = details_text
            container.insert(0, paragraph)
            has_content = True

        return container if has_content else None

    def _convert_summary_element(self, element: ET.Element) -> ET.Element | None:
        text = self._collapse_text(element).strip()
        if not text:
            return None

        paragraph = ET.Element("p")
        strong = ET.SubElement(paragraph, "strong")
        strong.text = text
        return paragraph

    def _sanitize_html_element_attributes(self, element: ET.Element) -> None:
        if self._namespace_uri(element.tag):
            return

        allowed = _ALLOWED_HTML_ATTRIBUTES.get(self._local_name(element.tag), set())
        if not element.attrib:
            return

        original_keys = list(element.attrib.keys())
        for key in original_keys:
            if key not in allowed:
                element.attrib.pop(key, None)

        if original_keys and set(original_keys) != set(element.attrib):
            self._warn(
                f"У HTML-элемента <{self._local_name(element.tag)}> были удалены неподдерживаемые "
                "атрибуты перед публикацией в Confluence."
            )

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
        xml = "".join(
            ET.tostring(child, encoding="unicode", method="xml") for child in list(root)
        )
        return self._postprocess_storage_xml(xml)

    @staticmethod
    def _postprocess_storage_xml(xml: str) -> str:
        def replace_plain_text_body(match: re.Match[str]) -> str:
            body = match.group("body")
            unescaped = (
                body.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
            )
            return f'<ac:plain-text-body><![CDATA[{unescaped}]]></ac:plain-text-body>'

        return re.sub(
            r"<ac:plain-text-body>(?P<body>.*?)</ac:plain-text-body>",
            replace_plain_text_body,
            xml,
            flags=re.DOTALL,
        )

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

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

    @staticmethod
    def _namespace_uri(tag: str) -> str:
        if tag.startswith("{") and "}" in tag:
            return tag[1:].split("}", 1)[0]
        return ""


def preview_markdown_to_storage(
    client: ConfluenceClient,
    markdown_text: str,
    *,
    enabled_extensions: Sequence[str] | None = None,
    extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
    builtin_extension_options: dict[str, dict[str, Any]] | None = None,
) -> MarkdownPreviewResult:
    """
    Функциональный wrapper для preview markdown -> storage.
    """

    return ConfluenceMarkdownImporter(
        client,
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
        builtin_extension_options=builtin_extension_options,
    ).preview_markdown_to_storage(markdown_text)
