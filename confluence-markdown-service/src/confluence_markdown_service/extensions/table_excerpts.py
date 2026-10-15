"""Table Excerpt macros from Stiltsoft Table Filter, Charts & Spreadsheets."""

from __future__ import annotations

import base64
import html
import json
import re
from uuid import uuid4
from xml.etree import ElementTree as ET

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"
_SOURCE_OPEN_RE = re.compile(
    r"^\s*<table-excerpt(?!-include\b)\b(?P<attributes>[^>]*)>\s*$",
    re.IGNORECASE,
)
_SOURCE_CLOSE_RE = re.compile(r"^\s*</table-excerpt>\s*$", re.IGNORECASE)
_INCLUDE_RE = re.compile(
    r"^\s*<table-excerpt-include\b(?P<attributes>.*?)\s*/>\s*$",
    re.IGNORECASE | re.DOTALL,
)
_ATTRIBUTE_RE = re.compile(
    r"(?P<name>[A-Za-z_:][A-Za-z0-9_.:-]*)\s*=\s*"
    r"(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)
_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
_SAFE_PARAMETER_NAME_RE = re.compile(r"[A-Za-z_:][A-Za-z0-9_.:-]*\Z")

_ATTRIBUTE_TO_PARAMETER = {
    "name": "name",
    "source": "excerptSource",
    "source-type": "type",
    "show-source": "copytable",
    "report": "merge-tables",
    "transpose": "transpose",
}
_PARAMETER_TO_ATTRIBUTE = {
    parameter_name: attribute_name
    for attribute_name, parameter_name in _ATTRIBUTE_TO_PARAMETER.items()
}


class TableExcerptsExtension(ConfluenceMarkdownExtension):
    """Bidirectional Markdown syntax for Table Excerpt macros on Server/DC."""

    name = "table_excerpts"
    description = (
        "Преобразует Markdown-блоки table-excerpt и table-excerpt-include "
        "в макросы Stiltsoft Table Filter, Charts & Spreadsheets."
    )

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def preprocess_markdown(self, markdown_text: str) -> str:
        if not self._enabled:
            return markdown_text

        lines = markdown_text.splitlines()
        output: list[str] = []
        index = 0
        fence_character = ""
        fence_length = 0

        while index < len(lines):
            line = lines[index]
            fence = _FENCE_RE.match(line)
            if fence_character:
                output.append(line)
                if fence is not None:
                    marker = fence.group("fence")
                    if marker[0] == fence_character and len(marker) >= fence_length:
                        fence_character = ""
                        fence_length = 0
                index += 1
                continue

            if fence is not None:
                marker = fence.group("fence")
                fence_character = marker[0]
                fence_length = len(marker)
                output.append(line)
                index += 1
                continue

            source_match = _SOURCE_OPEN_RE.match(line)
            if source_match is not None:
                closing_index = index + 1
                while (
                    closing_index < len(lines)
                    and _SOURCE_CLOSE_RE.match(lines[closing_index]) is None
                ):
                    closing_index += 1
                if closing_index < len(lines):
                    attributes = self._parse_attributes(source_match.group("attributes"))
                    body = self.preprocess_markdown(
                        "\n".join(lines[index + 1 : closing_index])
                    )
                    output.append(self._placeholder("table-excerpt", attributes, body))
                    index = closing_index + 1
                    continue

            if re.match(r"^\s*<table-excerpt-include\b", line, re.IGNORECASE):
                closing_index = index
                tag_lines = [line]
                while closing_index < len(lines) and "/>" not in lines[closing_index]:
                    closing_index += 1
                    if closing_index < len(lines):
                        tag_lines.append(lines[closing_index])
                include_match = _INCLUDE_RE.match("\n".join(tag_lines))
                if include_match is not None:
                    attributes = self._parse_attributes(include_match.group("attributes"))
                    output.append(self._placeholder("table-excerpt-include", attributes))
                    index = closing_index + 1
                    continue

            output.append(line)
            index += 1

        return "\n".join(output)

    def transform_import_element(
        self,
        importer,
        element: ET.Element,
    ) -> MarkdownImportTransformResult:
        if not self._enabled or importer._local_name(element.tag) != "div":  # noqa: SLF001
            return MarkdownImportTransformResult()

        macro_name = element.attrib.get("data-confluence-table-macro", "")
        if macro_name not in {"table-excerpt", "table-excerpt-include"}:
            return MarkdownImportTransformResult()

        attributes = self._decode_attributes(
            element.attrib.get("data-confluence-table-attributes", "")
        )
        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = macro_name
        macro.attrib[f"{{{_AC_URI}}}schema-version"] = "1"
        macro.attrib[f"{{{_AC_URI}}}macro-id"] = str(uuid4())

        parameters = self._parameters_from_attributes(attributes)
        for parameter in parameters.values():
            macro.append(parameter)

        if not (attributes.get("name") or attributes.get("param-name")):
            importer._warn(  # noqa: SLF001
                f"Макрос {macro_name} создан без обязательного "
                "параметра name."
            )

        if macro_name == "table-excerpt":
            body = ET.SubElement(macro, f"{{{_AC_URI}}}rich-text-body")
            text = (element.text or "").strip()
            if text:
                paragraph = ET.SubElement(body, "p")
                paragraph.text = text
            for child in list(element):
                element.remove(child)
                body.append(child)

        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        if not self._enabled:
            return MarkdownRenderResult()

        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name not in {"table-excerpt", "table-excerpt-include"}:
            return MarkdownRenderResult()

        attributes = self._attributes_from_parameters(element)
        formatted_attributes = self._format_attributes(attributes)
        if macro_name == "table-excerpt-include":
            markdown = self._format_include_tag(formatted_attributes)
            return MarkdownRenderResult(handled=True, markdown=markdown)

        body = renderer._macro_rich_text_body(element).strip()  # noqa: SLF001
        opening = f"<table-excerpt{formatted_attributes}>"
        markdown = f"{opening}\n\n{body}\n\n</table-excerpt>"
        return MarkdownRenderResult(handled=True, markdown=markdown)

    @staticmethod
    def _parse_attributes(raw_attributes: str) -> dict[str, str]:
        return {
            match.group("name"): html.unescape(match.group("value"))
            for match in _ATTRIBUTE_RE.finditer(raw_attributes)
        }

    @staticmethod
    def _placeholder(
        macro_name: str,
        attributes: dict[str, str],
        body: str = "",
    ) -> str:
        encoded = base64.urlsafe_b64encode(
            json.dumps(attributes, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        opening = (
            f'<div data-confluence-table-macro="{macro_name}" '
            f'data-confluence-table-attributes="{encoded}" markdown="1">'
        )
        if body:
            return f"{opening}\n\n{body}\n\n</div>"
        return f"{opening}</div>"

    @staticmethod
    def _decode_attributes(encoded: str) -> dict[str, str]:
        try:
            decoded = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
            value = json.loads(decoded)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        if not isinstance(value, dict):
            return {}
        return {
            str(name): str(attribute_value)
            for name, attribute_value in value.items()
        }

    def _parameters_from_attributes(
        self,
        attributes: dict[str, str],
    ) -> dict[str, ET.Element]:
        parameters: dict[str, ET.Element] = {}

        for attribute_name, parameter_name in _ATTRIBUTE_TO_PARAMETER.items():
            if attribute_name in attributes:
                parameters[parameter_name] = self._text_parameter(
                    parameter_name,
                    attributes[attribute_name],
                )

        if "page" in attributes:
            parameters["page"] = self._page_parameter(attributes["page"])

        for attribute_name, value in attributes.items():
            parameter_name = self._direct_parameter_name(attribute_name, "param-")
            if parameter_name is not None:
                parameters[parameter_name] = self._text_parameter(parameter_name, value)
                continue

            parameter_name = self._direct_parameter_name(attribute_name, "xml-param-")
            if parameter_name is not None:
                parameter = self._decode_xml_parameter(value, parameter_name)
                if parameter is not None:
                    parameters[parameter_name] = parameter
                continue

            parameter_name = self._encoded_parameter_name(attribute_name, "encoded-param-")
            if parameter_name is not None:
                parameters[parameter_name] = self._text_parameter(parameter_name, value)
                continue

            parameter_name = self._encoded_parameter_name(
                attribute_name,
                "encoded-xml-param-",
            )
            if parameter_name is not None:
                parameter = self._decode_xml_parameter(value, parameter_name)
                if parameter is not None:
                    parameters[parameter_name] = parameter

        return parameters

    def _attributes_from_parameters(self, macro: ET.Element) -> dict[str, str]:
        attributes: dict[str, str] = {}
        for parameter in macro:
            if self._local_name(parameter.tag) != "parameter":
                continue
            parameter_name = self._attribute_value(parameter, "name")
            if not parameter_name:
                continue

            if parameter_name == "page":
                page_title = self._page_title(parameter)
                if page_title is not None:
                    attributes["page"] = page_title
                    continue

            attribute_name = _PARAMETER_TO_ATTRIBUTE.get(parameter_name)
            if attribute_name is not None and not list(parameter):
                attributes[attribute_name] = parameter.text or ""
                continue

            is_xml = bool(list(parameter))
            exported_name = self._exported_parameter_name(parameter_name, is_xml=is_xml)
            if is_xml:
                clone = ET.fromstring(ET.tostring(parameter, encoding="unicode"))
                clone.tail = None
                serialized = ET.tostring(clone, encoding="unicode")
                attributes[exported_name] = base64.urlsafe_b64encode(
                    serialized.encode("utf-8")
                ).decode("ascii")
            else:
                attributes[exported_name] = parameter.text or ""
        return attributes

    @staticmethod
    def _text_parameter(name: str, value: str) -> ET.Element:
        parameter = ET.Element(f"{{{_AC_URI}}}parameter")
        parameter.attrib[f"{{{_AC_URI}}}name"] = name
        parameter.text = value
        return parameter

    @staticmethod
    def _page_parameter(page_title: str) -> ET.Element:
        parameter = ET.Element(f"{{{_AC_URI}}}parameter")
        parameter.attrib[f"{{{_AC_URI}}}name"] = "page"
        link = ET.SubElement(parameter, f"{{{_AC_URI}}}link")
        page = ET.SubElement(link, f"{{{_RI_URI}}}page")
        page.attrib[f"{{{_RI_URI}}}content-title"] = page_title
        return parameter

    @classmethod
    def _page_title(cls, parameter: ET.Element) -> str | None:
        if (parameter.text or "").strip() or len(parameter) != 1:
            return None
        link = parameter[0]
        if cls._local_name(link.tag) != "link" or len(link) != 1:
            return None
        page = link[0]
        if cls._local_name(page.tag) != "page":
            return None
        return cls._attribute_value(page, "content-title") or None

    @classmethod
    def _decode_xml_parameter(cls, encoded: str, name: str) -> ET.Element | None:
        try:
            serialized = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
            parameter = ET.fromstring(serialized)
        except (ValueError, UnicodeDecodeError, ET.ParseError):
            return None
        if cls._local_name(parameter.tag) != "parameter":
            return None
        parameter.attrib[f"{{{_AC_URI}}}name"] = name
        return parameter

    @staticmethod
    def _direct_parameter_name(attribute_name: str, prefix: str) -> str | None:
        if not attribute_name.startswith(prefix):
            return None
        parameter_name = attribute_name.removeprefix(prefix)
        return parameter_name or None

    @staticmethod
    def _encoded_parameter_name(attribute_name: str, prefix: str) -> str | None:
        if not attribute_name.startswith(prefix):
            return None
        encoded_name = attribute_name.removeprefix(prefix)
        if not encoded_name:
            return None
        encoded_name += "=" * (-len(encoded_name) % 4)
        try:
            return base64.urlsafe_b64decode(encoded_name.encode("ascii")).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None

    @staticmethod
    def _exported_parameter_name(parameter_name: str, *, is_xml: bool) -> str:
        prefix = "xml-param-" if is_xml else "param-"
        if _SAFE_PARAMETER_NAME_RE.fullmatch(parameter_name):
            return f"{prefix}{parameter_name}"
        encoded = base64.urlsafe_b64encode(parameter_name.encode("utf-8")).decode("ascii")
        encoded = encoded.rstrip("=")
        encoded_prefix = "encoded-xml-param-" if is_xml else "encoded-param-"
        return f"{encoded_prefix}{encoded}"

    @staticmethod
    def _format_attributes(attributes: dict[str, str]) -> str:
        if not attributes:
            return ""
        return "".join(
            f' {name}="{html.escape(value, quote=True)}"'
            for name, value in attributes.items()
        )

    @staticmethod
    def _format_include_tag(formatted_attributes: str) -> str:
        attributes = formatted_attributes.strip().split(" ")
        if not formatted_attributes or len(attributes) <= 2:
            return f"<table-excerpt-include{formatted_attributes} />"
        lines = formatted_attributes.strip().replace('" ', '"\n  ')
        return f"<table-excerpt-include\n  {lines}\n/>"

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].split(":", 1)[-1]

    @staticmethod
    def _attribute_value(element: ET.Element, local_name: str) -> str:
        for name, value in element.attrib.items():
            if name.rsplit("}", 1)[-1].split(":", 1)[-1] == local_name:
                return value
        return ""
