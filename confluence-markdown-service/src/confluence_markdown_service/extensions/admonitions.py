"""Расширение для note / warning / tip / info / error блоков."""

from __future__ import annotations

import copy
import re
from xml.etree import ElementTree as ET

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_ADMONITION_PATTERN = re.compile(r"^\s*\[!([A-Z]+)\]\s*(.*)$")
_MARKER_TO_MACRO = {
    "NOTE": "note",
    "WARNING": "warning",
    "TIP": "tip",
    "INFO": "info",
}
_MACRO_TO_MARKER = {
    "note": "NOTE",
    "warning": "WARNING",
    "tip": "TIP",
    "info": "INFO",
}


class AdmonitionsExtension(ConfluenceMarkdownExtension):
    """
    Поддержка admonition-синтаксиса:

    > [!NOTE]
    > Текст
    """

    name = "admonitions"
    description = (
        "Поддержка markdown admonitions через blockquote синтаксис "
        "[!NOTE], [!WARNING], [!TIP], [!INFO], [!ERROR]."
    )

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) != "blockquote":  # noqa: SLF001
            return MarkdownImportTransformResult()

        first_paragraph = self._first_paragraph(element)
        if first_paragraph is None:
            return MarkdownImportTransformResult()

        first_text = importer._collapse_text(first_paragraph).strip()  # noqa: SLF001
        match = _ADMONITION_PATTERN.match(first_text)
        if not match:
            return MarkdownImportTransformResult()

        marker = match.group(1).upper()
        remainder = match.group(2).strip()

        macro = self._build_macro_for_marker(marker)
        if macro is None:
            return MarkdownImportTransformResult()

        rich_body = ET.SubElement(macro, f"{{{_AC_URI}}}rich-text-body")
        copied_children = [copy.deepcopy(child) for child in list(element)]

        if not copied_children:
            return MarkdownImportTransformResult()

        first_copied = copied_children[0]
        if importer._local_name(first_copied.tag) == "p":  # noqa: SLF001
            self._strip_marker_from_first_paragraph(first_copied, remainder)

        meaningful_children = []
        for child in copied_children:
            if importer._collapse_text(child).strip() or list(child):  # noqa: SLF001
                meaningful_children.append(child)

        for child in meaningful_children:
            rich_body.append(child)

        if marker == "ERROR":
            importer._warn("Admonition [!ERROR] был преобразован в panel macro Confluence.")  # noqa: SLF001

        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name in _MACRO_TO_MARKER:
            marker = _MACRO_TO_MARKER[macro_name]
            body = renderer._macro_rich_text_body(element).strip()  # noqa: SLF001
            markdown = self._format_admonition(marker, body)
            return MarkdownRenderResult(handled=True, markdown=markdown)

        if macro_name == "panel":
            title = renderer._macro_parameter(element, "title").strip().upper()  # noqa: SLF001
            if title == "ERROR":
                body = renderer._macro_rich_text_body(element).strip()  # noqa: SLF001
                markdown = self._format_admonition("ERROR", body)
                return MarkdownRenderResult(handled=True, markdown=markdown)

        return MarkdownRenderResult()

    @staticmethod
    def _first_paragraph(blockquote: ET.Element) -> ET.Element | None:
        for child in list(blockquote):
            if child.tag.endswith("p"):
                return child
        return None

    @staticmethod
    def _build_macro_for_marker(marker: str) -> ET.Element | None:
        if marker in _MARKER_TO_MACRO:
            macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
            macro.attrib[f"{{{_AC_URI}}}name"] = _MARKER_TO_MACRO[marker]
            return macro

        if marker == "ERROR":
            macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
            macro.attrib[f"{{{_AC_URI}}}name"] = "panel"
            params = {
                "title": "ERROR",
                "borderStyle": "solid",
                "borderColor": "#DC2626",
                "titleBGColor": "#FEE2E2",
                "titleColor": "#991B1B",
                "bgColor": "#FEF2F2",
            }
            for key, value in params.items():
                param = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
                param.attrib[f"{{{_AC_URI}}}name"] = key
                param.text = value
            return macro
        return None

    @staticmethod
    def _strip_marker_from_first_paragraph(paragraph: ET.Element, remainder: str) -> None:
        paragraph.text = remainder

    @staticmethod
    def _format_admonition(marker: str, body: str) -> str:
        body = body.strip()
        if not body:
            return f"> [!{marker}]"
        lines = [f"> [!{marker}]"]
        lines.extend(f"> {line}" if line.strip() else ">" for line in body.splitlines())
        return "\n".join(lines)
