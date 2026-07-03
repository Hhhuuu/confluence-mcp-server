"""Расширение для работы с TOC macro."""

from __future__ import annotations

from xml.etree import ElementTree as ET
from uuid import uuid4
import re

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_TOC_PATTERN = re.compile(r"^\[\[?TOC(?:\s+maxLevel=(?P<max_level>\d+))?\]\]?$", re.IGNORECASE)


class TocExtension(ConfluenceMarkdownExtension):
    """Поддержка `[TOC]` <-> Confluence TOC macro."""

    name = "toc"
    description = "Поддержка [TOC], [[TOC]] и параметра maxLevel для Confluence TOC macro."

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) != "p":  # noqa: SLF001
            return MarkdownImportTransformResult()

        text = importer._collapse_text(element).strip()  # noqa: SLF001
        match = _TOC_PATTERN.match(text)
        if not match:
            return MarkdownImportTransformResult()

        max_level = match.group("max_level")

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "toc"
        macro.attrib[f"{{{_AC_URI}}}schema-version"] = "1"
        macro.attrib[f"{{{_AC_URI}}}macro-id"] = str(uuid4())
        if max_level:
            parameter = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
            parameter.attrib[f"{{{_AC_URI}}}name"] = "maxLevel"
            parameter.text = max_level
        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name != "toc":
            return MarkdownRenderResult()

        max_level = renderer._macro_parameter(element, "maxLevel").strip()  # noqa: SLF001
        markdown = f"[TOC maxLevel={max_level}]" if max_level else "[TOC]"
        return MarkdownRenderResult(handled=True, markdown=markdown)
