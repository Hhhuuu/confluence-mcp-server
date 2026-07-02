"""Расширение для note / warning / tip / info / error блоков."""

from __future__ import annotations

import copy
import html
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

    def preprocess_markdown(self, markdown_text: str) -> str:
        lines = markdown_text.splitlines()
        output: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            marker_match = re.match(r"^\s*>\s*\[!([A-Z]+)\]\s*(.*)$", line)
            if not marker_match:
                output.append(line)
                index += 1
                continue

            marker = marker_match.group(1).upper()
            first_remainder = marker_match.group(2).strip()
            body_lines: list[str] = []
            if first_remainder:
                body_lines.append(first_remainder)

            index += 1
            while index < len(lines):
                next_line = lines[index]
                if re.match(r"^\s*>\s*\[![A-Z]+\]\s*(.*)$", next_line):
                    break
                if not next_line.strip():
                    body_lines.append("")
                    index += 1
                    continue
                continuation_match = re.match(r"^\s*>\s?(.*)$", next_line)
                if not continuation_match:
                    break
                body_lines.append(continuation_match.group(1))
                index += 1

            html_block = self._build_placeholder_block(marker, body_lines)
            output.append(html_block)

        return "\n".join(output)

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        placeholder_marker = (element.attrib.get("data-admonition") or "").strip().upper()
        if placeholder_marker:
            macro = self._build_macro_for_marker(placeholder_marker)
            if macro is None:
                return MarkdownImportTransformResult()

            rich_body = ET.SubElement(macro, f"{{{_AC_URI}}}rich-text-body")
            copied_children = [copy.deepcopy(child) for child in list(element)]
            for child in copied_children:
                rich_body.append(child)

            if placeholder_marker == "ERROR":
                importer._warn("Admonition [!ERROR] был преобразован в panel macro Confluence.")  # noqa: SLF001
            return MarkdownImportTransformResult(handled=True, replacement=macro)

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

    @staticmethod
    def _build_placeholder_block(marker: str, body_lines: list[str]) -> str:
        paragraphs: list[str] = []
        current: list[str] = []

        def flush() -> None:
            if not current:
                return
            text = " ".join(part.strip() for part in current if part.strip()).strip()
            paragraphs.append(f"<p>{html.escape(text)}</p>" if text else "<p></p>")
            current.clear()

        for line in body_lines:
            if not line.strip():
                flush()
                continue
            current.append(line)
        flush()

        if not paragraphs:
            paragraphs = ["<p></p>"]

        inner = "".join(paragraphs)
        return f'<blockquote data-admonition="{marker}">{inner}</blockquote>'
