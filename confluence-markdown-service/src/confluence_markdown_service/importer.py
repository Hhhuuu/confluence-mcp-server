"""Импорт Markdown в Confluence storage format и публикация страниц."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import markdown as markdown_lib
from confluence_client import ConfluenceClient

from .exceptions import MarkdownBridgeError
from .models import MarkdownPreviewResult, MarkdownPublishResult

_AC_URI = "urn:ac"
_TOC_MARKERS = {"[TOC]", "[[TOC]]"}


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
            warnings=preview.warnings,
        )

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
            warnings=preview.warnings,
        )

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

    def _xhtml_to_storage(self, xhtml: str) -> tuple[str, list[str]]:
        wrapped = (
            "<root "
            'xmlns:ac="urn:ac"'
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

        if name == "pre":
            code = self._convert_pre_to_code_macro(element)
            if code is not None:
                self._replace_element_in_parent(element, code)
                return

        if name == "img":
            warnings.append(
                "Markdown-изображения публикуются как обычные HTML img-теги. "
                "Для attachments может понадобиться отдельная загрузка файлов."
            )

    def _convert_pre_to_code_macro(self, element: ET.Element) -> ET.Element | None:
        code_child = None
        for child in list(element):
            if self._local_name(child.tag) == "code":
                code_child = child
                break

        code_text = self._collapse_text(code_child or element).strip("\n")
        if not code_text:
            return None

        language = ""
        if code_child is not None:
            class_name = code_child.attrib.get("class", "")
            match = re.search(r"language-([A-Za-z0-9_+-]+)", class_name)
            if match:
                language = match.group(1)

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "code"

        if language:
            parameter = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
            parameter.attrib[f"{{{_AC_URI}}}name"] = "language"
            parameter.text = language

        body = ET.SubElement(macro, f"{{{_AC_URI}}}plain-text-body")
        body.text = code_text
        return macro

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
