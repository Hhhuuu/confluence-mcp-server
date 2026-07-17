"""Поддержка status macro Confluence через HTML status tag."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..storage_normalizer import attr_value, local_name, namespace_uri
from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"


class StatusElementExtension(ConfluenceMarkdownExtension):
    """Поддержка `<status color="Green">Text</status>` <-> Confluence status macro."""

    name = "status_element"
    description = (
        "Поддержка status macro через HTML-тег "
        '<status color="Green">Text</status>.'
    )

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if namespace_uri(element.tag):
            return MarkdownImportTransformResult()
        if local_name(element.tag) != "status":
            return MarkdownImportTransformResult()

        text = importer._collapse_text(element).strip()  # noqa: SLF001
        color = (
            element.attrib.get("color", "").strip()
            or element.attrib.get("colour", "").strip()
        )
        subtle = element.attrib.get("subtle", "").strip().lower()

        if not text:
            importer._warn("Элемент <status> без текста был пропущен.")  # noqa: SLF001
            return MarkdownImportTransformResult()

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "status"

        self._append_parameter(macro, "title", text)
        if color:
            self._append_parameter(macro, "colour", color)
        if subtle in {"true", "false"}:
            self._append_parameter(macro, "subtle", subtle)

        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name != "status":
            return MarkdownRenderResult()

        title = renderer._macro_parameter(element, "title").strip()  # noqa: SLF001
        color = renderer._macro_parameter(element, "colour").strip()  # noqa: SLF001
        subtle = renderer._macro_parameter(element, "subtle").strip()  # noqa: SLF001

        attrs: list[str] = []
        if color:
            attrs.append(f'color="{color}"')
        if subtle:
            attrs.append(f'subtle="{subtle}"')
        joined_attrs = f" {' '.join(attrs)}" if attrs else ""
        return MarkdownRenderResult(
            handled=True,
            markdown=f"<status{joined_attrs}>{title}</status>",
        )

    @staticmethod
    def _append_parameter(macro: ET.Element, name: str, value: str) -> None:
        param = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
        param.attrib[f"{{{_AC_URI}}}name"] = name
        param.text = value
