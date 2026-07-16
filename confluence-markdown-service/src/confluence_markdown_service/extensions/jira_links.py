"""Расширение для Confluence-ссылок на Jira issues."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from .base import (
    ConfluenceMarkdownExtension,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"
_JIRA_BROWSE_RE = re.compile(
    r"^(?P<base>https?://[^)\s]+)/browse/(?P<issue>[A-Z][A-Z0-9_]+-\d+)(?:[/?#].*)?$",
    re.IGNORECASE,
)


class JiraLinksExtension(ConfluenceMarkdownExtension):
    """
    Поддержка markdown-ссылок на Jira issues.

    Пример:
    [KAN-123](https://jira.example.local/browse/KAN-123)
    """

    name = "jira_links"
    description = (
        "Поддержка ссылок на Jira issues. "
        "Markdown-ссылки вида [KAN-123](https://jira.example.local/browse/KAN-123) "
        "преобразуются в Confluence link с Jira URL."
    )

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) != "a":  # noqa: SLF001
            return MarkdownImportTransformResult()

        href = (element.attrib.get("href") or "").strip()
        match = _JIRA_BROWSE_RE.match(href)
        if not match:
            return MarkdownImportTransformResult()

        issue_key = match.group("issue").upper()
        text = importer._collapse_text(element).strip() or issue_key  # noqa: SLF001

        link = ET.Element(f"{{{_AC_URI}}}link")
        resource = ET.SubElement(link, f"{{{_RI_URI}}}url")
        resource.attrib[f"{{{_RI_URI}}}value"] = href

        body = ET.SubElement(link, f"{{{_AC_URI}}}plain-text-link-body")
        body.text = text
        return MarkdownImportTransformResult(handled=True, replacement=link)

    def render_confluence_link(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        target = None
        text = ""

        for child in element:
            child_name = renderer._local_name(child.tag)  # noqa: SLF001
            child_ns = renderer._namespace_uri(child.tag)  # noqa: SLF001
            if child_ns == _RI_URI and child_name == "url":
                target = renderer._resolve_resource_element_target(child)  # noqa: SLF001
            elif child_ns == _AC_URI and child_name in {"link-body", "plain-text-link-body"}:
                text = renderer._render_inline(child).strip()  # noqa: SLF001

        if not target:
            return MarkdownRenderResult()

        match = _JIRA_BROWSE_RE.match(target)
        if not match:
            return MarkdownRenderResult()

        issue_key = match.group("issue").upper()
        link_text = text or issue_key
        return MarkdownRenderResult(
            handled=True,
            markdown=f"[{link_text}]({target})",
        )
