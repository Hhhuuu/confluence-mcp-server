"""Расширение для Confluence-ссылок на Jira issues."""

from __future__ import annotations

import html
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
_JIRA_TAG_RE = re.compile(
    r'^\s*<jira\b(?P<attrs>[^>]*)>(?P<body>.*?)</jira>\s*$',
    re.IGNORECASE | re.DOTALL,
)
_JIRA_SELF_CLOSING_TAG_RE = re.compile(
    r'^\s*<jira\b(?P<attrs>[^>]*)/>\s*$',
    re.IGNORECASE | re.DOTALL,
)
_JIRA_ATTR_RE = re.compile(r'(?P<name>[A-Za-z_:][A-Za-z0-9_:-]*)="(?P<value>[^"]*)"')


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
        "или custom-теги <jira ...> преобразуются в Confluence jira macro "
        "или в обычный Confluence link с Jira URL."
    )

    def __init__(
        self,
        *,
        jira_server_id: str | None = None,
        jira_server_name: str | None = None,
    ) -> None:
        self._jira_server_id = (jira_server_id or "").strip()
        self._jira_server_name = (jira_server_name or "").strip()

    def preprocess_markdown(self, markdown_text: str) -> str:
        lines = markdown_text.splitlines()
        output: list[str] = []

        for line in lines:
            parsed = self._parse_jira_tag(line)
            if not parsed:
                output.append(line)
                continue

            issue_key, server_id, server_name, label = parsed
            attrs = [f'data-jira-key="{html.escape(issue_key, quote=True)}"']
            if server_id:
                attrs.append(f'data-jira-server-id="{html.escape(server_id, quote=True)}"')
            if server_name:
                attrs.append(f'data-jira-server-name="{html.escape(server_name, quote=True)}"')
            visible_text = html.escape(label or issue_key)
            output.append(f"<jira {' '.join(attrs)}>{visible_text}</jira>")

        return "\n".join(output)

    def transform_import_element(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        if importer._local_name(element.tag) == "jira":  # noqa: SLF001
            return self._transform_jira_placeholder(importer, element)
        if importer._local_name(element.tag) != "a":  # noqa: SLF001
            return MarkdownImportTransformResult()

        href = (element.attrib.get("href") or "").strip()
        match = _JIRA_BROWSE_RE.match(href)
        if not match:
            return MarkdownImportTransformResult()

        issue_key = match.group("issue").upper()
        text = importer._collapse_text(element).strip() or issue_key  # noqa: SLF001

        if self._has_macro_config():
            macro = self._build_jira_macro(
                issue_key=issue_key,
                server_id=self._jira_server_id,
                server_name=self._jira_server_name,
            )
            return MarkdownImportTransformResult(handled=True, replacement=macro)

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

    def render_macro(self, renderer, element: ET.Element) -> MarkdownRenderResult:
        macro_name = renderer._macro_name(element)  # noqa: SLF001
        if macro_name != "jira":
            return MarkdownRenderResult()

        issue_key = renderer._macro_parameter(element, "key").strip()  # noqa: SLF001
        server_id = renderer._macro_parameter(element, "serverId").strip()  # noqa: SLF001
        server_name = renderer._macro_parameter(element, "server").strip()  # noqa: SLF001
        if not issue_key:
            return MarkdownRenderResult()

        attrs = [f'key="{issue_key}"']
        if server_id:
            attrs.append(f'serverId="{server_id}"')
        if server_name:
            attrs.append(f'server="{server_name}"')

        return MarkdownRenderResult(
            handled=True,
            markdown=f"<jira {' '.join(attrs)}>{issue_key}</jira>",
        )

    def _transform_jira_placeholder(self, importer, element: ET.Element) -> MarkdownImportTransformResult:
        issue_key = (element.attrib.get("data-jira-key") or "").strip().upper()
        if not issue_key:
            importer._warn("Элемент <jira> без key был пропущен.")  # noqa: SLF001
            return MarkdownImportTransformResult()

        server_id = (
            element.attrib.get("data-jira-server-id", "").strip()
            or self._jira_server_id
        )
        server_name = (
            element.attrib.get("data-jira-server-name", "").strip()
            or self._jira_server_name
        )

        if server_id and server_name:
            return MarkdownImportTransformResult(
                handled=True,
                replacement=self._build_jira_macro(
                    issue_key=issue_key,
                    server_id=server_id,
                    server_name=server_name,
                ),
            )

        importer._warn(  # noqa: SLF001
            "Для <jira> не настроены jira_server_id/jira_server_name, поэтому native jira macro "
            "не был создан."
        )
        return MarkdownImportTransformResult()

    def _build_jira_macro(
        self,
        *,
        issue_key: str,
        server_id: str,
        server_name: str,
    ) -> ET.Element:
        macro = ET.Element(f"{{{_AC_URI}}}structured-macro")
        macro.attrib[f"{{{_AC_URI}}}name"] = "jira"
        self._append_parameter(macro, "serverId", server_id)
        self._append_parameter(macro, "server", server_name)
        self._append_parameter(macro, "key", issue_key)
        return macro

    def _has_macro_config(self) -> bool:
        return bool(self._jira_server_id and self._jira_server_name)

    @staticmethod
    def _append_parameter(macro: ET.Element, name: str, value: str) -> None:
        param = ET.SubElement(macro, f"{{{_AC_URI}}}parameter")
        param.attrib[f"{{{_AC_URI}}}name"] = name
        param.text = value

    @staticmethod
    def _parse_jira_tag(line: str) -> tuple[str, str, str, str] | None:
        match = _JIRA_TAG_RE.match(line) or _JIRA_SELF_CLOSING_TAG_RE.match(line)
        if not match:
            return None

        attrs = {
            attr_match.group("name"): attr_match.group("value")
            for attr_match in _JIRA_ATTR_RE.finditer(match.group("attrs") or "")
        }
        issue_key = (attrs.get("key") or "").strip().upper()
        if not issue_key:
            return None

        server_id = (attrs.get("serverId") or attrs.get("server-id") or "").strip()
        server_name = (attrs.get("server") or attrs.get("serverName") or attrs.get("server-name") or "").strip()
        body = (match.groupdict().get("body") or "").strip()
        return issue_key, server_id, server_name, body
