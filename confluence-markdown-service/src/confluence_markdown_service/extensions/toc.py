"""Расширение для работы с TOC macro."""

from __future__ import annotations

from xml.etree import ElementTree as ET
from uuid import uuid4

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_TOC_MARKERS = {"[TOC]", "[[TOC]]"}


class TocExtension(ConfluenceMarkdownExtension):
    """Поддержка `[TOC]` <-> Confluence TOC macro."""

    name = "toc"
    description = "Поддержка [TOC] и [[TOC]] для Confluence TOC macro."

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) != "p":  # noqa: SLF001
            return MarkdownImportTransformResult()

        text = importer._collapse_text(element).strip()  # noqa: SLF001
        if text not in _TOC_MARKERS:
            return MarkdownImportTransformResult()

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "toc"
        macro.attrib[f"{{{_AC_URI}}}schema-version"] = "1"
        macro.attrib[f"{{{_AC_URI}}}macro-id"] = str(uuid4())
        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name != "toc":
            return MarkdownRenderResult()
        return MarkdownRenderResult(handled=True, markdown="[TOC]")
