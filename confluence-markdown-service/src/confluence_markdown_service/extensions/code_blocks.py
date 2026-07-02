"""Расширение для code macro с заголовком."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ..storage_normalizer import attr_value, element_text_content, local_name
from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_LANGUAGE_RE = re.compile(r"(?:^|\\s)language-([A-Za-z0-9_+-]+)(?:\\s|$)")


class CodeBlocksExtension(ConfluenceMarkdownExtension):
    """Поддержка fenced code block с title=\"...\" для Confluence code macro."""

    name = "code_blocks"
    description = (
        "Поддержка fenced code block с параметрами языка и title, "
        "которые преобразуются в Confluence code macro."
    )

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) != "pre":  # noqa: SLF001
            return MarkdownImportTransformResult()

        code = self._find_code_child(element)
        if code is None:
            return MarkdownImportTransformResult()

        language = self._extract_language(code)
        title = attr_value(code, "title") or code.attrib.get("title") or ""
        body = element_text_content(code)

        if not language and not title:
            return MarkdownImportTransformResult()

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "code"

        if language:
            self._append_parameter(macro, "language", language)
        if title:
            self._append_parameter(macro, "title", title)

        body_element = ET.SubElement(macro, f"{{{_AC_URI}}}plain-text-body")
        body_element.text = body
        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name != "code":
            return MarkdownRenderResult()

        language = renderer._macro_parameter(element, "language").strip()  # noqa: SLF001
        title = renderer._macro_parameter(element, "title").strip()  # noqa: SLF001
        body = renderer._macro_plain_text_body(element)  # noqa: SLF001

        language_block = language
        if title:
            language_block = f'{language_block} {{title="{title}"}}'.strip()

        markdown = renderer._fenced_code_block(body, language_block)  # noqa: SLF001
        return MarkdownRenderResult(handled=True, markdown=markdown)

    @staticmethod
    def _find_code_child(pre: ET.Element) -> ET.Element | None:
        for child in list(pre):
            if local_name(child.tag) == "code":
                return child
        return None

    @staticmethod
    def _extract_language(code: ET.Element) -> str:
        css_class = attr_value(code, "class") or code.attrib.get("class") or ""
        match = _LANGUAGE_RE.search(css_class)
        return match.group(1) if match else ""

    @staticmethod
    def _append_parameter(macro: ET.Element, name: str, value: str) -> None:
        param = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
        param.attrib[f"{{{_AC_URI}}}name"] = name
        param.text = value
