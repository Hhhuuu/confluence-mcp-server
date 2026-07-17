"""Поддержка date-элемента Confluence через HTML time tag."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from ..storage_normalizer import attr_value, local_name, namespace_uri
from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_SHORTCUT_RE = re.compile(r"\[date:(?P<date>\d{4}-\d{2}-\d{2})\]", re.IGNORECASE)


class DateElementExtension(ConfluenceMarkdownExtension):
    """Поддержка `[date:YYYY-MM-DD]` и `<time ...>` <-> Confluence date element."""

    name = "date_element"
    description = (
        "Поддержка элемента даты через синтаксис "
        "[date:YYYY-MM-DD] и HTML-тег <time datetime=\"YYYY-MM-DD\">."
    )

    def preprocess_markdown(self, markdown_text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            value = match.group("date")
            return f'<time datetime="{value}">{value}</time>'

        return _DATE_SHORTCUT_RE.sub(replace, markdown_text)

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if namespace_uri(element.tag):
            return MarkdownImportTransformResult()
        if local_name(element.tag) != "time":
            return MarkdownImportTransformResult()

        datetime_value = (element.attrib.get("datetime") or "").strip()
        if not _DATE_RE.match(datetime_value):
            importer._warn(  # noqa: SLF001
                "Элемент <time> без даты формата YYYY-MM-DD был оставлен как обычный HTML."
            )
            return MarkdownImportTransformResult()

        time_element = ET.Element("time")
        time_element.attrib["datetime"] = datetime_value
        text = importer._collapse_text(element).strip()  # noqa: SLF001
        time_element.text = text or datetime_value
        return MarkdownImportTransformResult(handled=True, replacement=time_element)

    def render_inline_element(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        if namespace_uri(element.tag):
            return MarkdownRenderResult()
        if local_name(element.tag) != "time":
            return MarkdownRenderResult()

        datetime_value = (attr_value(element, "datetime") or element.attrib.get("datetime") or "").strip()
        if not datetime_value:
            return MarkdownRenderResult()

        text = renderer._render_inline(element).strip()  # noqa: SLF001
        visible_text = text or datetime_value
        markdown = f'<time datetime="{datetime_value}">{visible_text}</time>'
        return MarkdownRenderResult(handled=True, markdown=markdown)
