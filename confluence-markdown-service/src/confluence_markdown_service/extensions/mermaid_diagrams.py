"""Расширение Mermaid Diagrams for Confluence от Stratus Add-ons."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import html
from pathlib import Path
import re
from uuid import uuid4
from xml.etree import ElementTree as ET

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_MERMAID_FENCE_RE = re.compile(
    r'^```mermaid(?:\s+\{title="(?P<title>[^"]+)"\})?\s*$'
)


@dataclass(frozen=True)
class GeneratedMermaidAttachment:
    """Сгенерированный текстовый attachment с исходником Mermaid."""

    filename: str
    content: str


class MermaidDiagramsExtension(ConfluenceMarkdownExtension):
    """Поддержка attachment-based macro `mermaid-cloud`."""

    name = "mermaid_diagrams"
    description = (
        "Преобразует fenced-блоки mermaid в macro mermaid-cloud плагина "
        "Mermaid Diagrams for Confluence; исходник хранится в attachment."
    )

    def __init__(
        self,
        attachment_contents: dict[str, str] | None = None,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        self.generated_attachments: list[GeneratedMermaidAttachment] = []
        self._revisions: dict[str, int] = {}
        self._attachment_contents = dict(attachment_contents or {})

    def preprocess_markdown(self, markdown_text: str) -> str:
        self.generated_attachments = []
        self._revisions = {}
        if not self._enabled:
            return markdown_text
        lines = markdown_text.splitlines()
        output: list[str] = []
        index = 0
        diagram_index = 0

        while index < len(lines):
            header = _MERMAID_FENCE_RE.match(lines[index])
            if header is None:
                output.append(lines[index])
                index += 1
                continue

            closing_index = index + 1
            body_lines: list[str] = []
            while closing_index < len(lines) and lines[closing_index].strip() != "```":
                body_lines.append(lines[closing_index])
                closing_index += 1
            if closing_index >= len(lines):
                output.append(lines[index])
                index += 1
                continue

            diagram_index += 1
            title = (header.group("title") or "").strip()
            filename = self._attachment_filename(title, diagram_index)
            content = "\n".join(body_lines).rstrip() + "\n"
            self.generated_attachments.append(
                GeneratedMermaidAttachment(filename=filename, content=content)
            )
            encoded_code = base64.b64encode(content.encode("utf-8")).decode("ascii")
            output.append(
                '<div data-confluence-mermaid="true" '
                f'data-mermaid-filename="{html.escape(filename, quote=True)}" '
                f'data-mermaid-code="{encoded_code}"></div>'
            )
            index = closing_index + 1

        return "\n".join(output)

    def set_revision(self, filename: str, revision: int) -> None:
        self._revisions[filename] = revision

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if not self._enabled:
            return MarkdownImportTransformResult()
        if importer._local_name(element.tag) != "div":  # noqa: SLF001
            return MarkdownImportTransformResult()
        if element.attrib.get("data-confluence-mermaid") != "true":
            return MarkdownImportTransformResult()

        filename = element.attrib.get("data-mermaid-filename", "").strip()
        if not filename:
            return MarkdownImportTransformResult()

        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "mermaid-cloud"
        macro.attrib[f"{{{_AC_URI}}}macro-id"] = str(uuid4())
        self._append_parameter(macro, "filename", filename)
        self._append_parameter(macro, "revision", str(self._revisions.get(filename, 1)))
        self._append_parameter(macro, "toolbar", "bottom")
        return MarkdownImportTransformResult(handled=True, replacement=macro)

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        if not self._enabled:
            return MarkdownRenderResult()
        if renderer._macro_name(element) != "mermaid-cloud":  # noqa: SLF001
            return MarkdownRenderResult()

        filename = renderer._macro_parameter(element, "filename").strip()  # noqa: SLF001
        source = self._attachment_contents.get(filename)
        if source is None:
            renderer._warn(  # noqa: SLF001
                f"Не удалось загрузить Mermaid attachment '{filename}'."
            )
            source = f"%% Mermaid source attachment: {filename}"
        markdown = renderer._fenced_code_block(source.rstrip(), "mermaid")  # noqa: SLF001
        return MarkdownRenderResult(handled=True, markdown=markdown)

    @staticmethod
    def _attachment_filename(title: str, index: int) -> str:
        if not title:
            return f"mermaid-diagram-{index}.mmd"
        safe_title = Path(title).name.strip().replace("/", "-").replace("\\", "-")
        return safe_title if safe_title.lower().endswith(".mmd") else f"{safe_title}.mmd"

    @staticmethod
    def _append_parameter(macro: ET.Element, name: str, value: str) -> None:
        parameter = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
        parameter.attrib[f"{{{_AC_URI}}}name"] = name
        parameter.text = value
