"""Рендеринг Confluence storage format в Markdown."""

from __future__ import annotations

import re
from typing import List
from xml.etree import ElementTree as ET

from .storage_normalizer import attr_value, element_text_content, local_name, namespace_uri

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"


class StorageMarkdownRenderer:
    """
    Ограниченный renderer Confluence storage format в Markdown.

    Renderer ориентирован на текст и базовые Markdown-конструкции.
    Неизвестные макросы не валят экспорт: они пропускаются с предупреждением.
    """

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def render_document(self, root: ET.Element) -> str:
        """
        Преобразовать XML-документ Confluence в Markdown.

        Args:
            root: Корневой элемент-обертка.

        Returns:
            Markdown-документ.
        """

        blocks = self._render_blocks(root, list_depth=0)
        joined = "\n\n".join(block for block in blocks if block.strip())
        return self._normalize_document(joined)

    def _render_blocks(self, parent: ET.Element, list_depth: int) -> List[str]:
        blocks: List[str] = []

        leading_text = self._normalize_inline_text(parent.text or "")
        if leading_text:
            blocks.append(leading_text)

        for child in parent:
            blocks.extend(self._render_block(child, list_depth=list_depth))
            tail = self._normalize_inline_text(child.tail or "")
            if tail:
                blocks.append(tail)

        return [block for block in blocks if block and block.strip()]

    def _render_block(self, element: ET.Element, list_depth: int) -> List[str]:
        name = local_name(element.tag)
        ns = namespace_uri(element.tag)

        if ns == _AC_URI and name == "structured-macro":
            rendered = self._render_macro(element)
            return [rendered] if rendered else []

        if ns == _AC_URI and name in {"layout", "layout-section", "layout-cell", "rich-text-body"}:
            return self._render_blocks(element, list_depth=list_depth)

        if ns == _AC_URI and name == "plain-text-body":
            text = element.text or ""
            return [text.strip()] if text.strip() else []

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1])
            text = self._render_inline(element).strip()
            return [f"{'#' * level} {text}"] if text else []

        if name == "p":
            text = self._render_inline(element).strip()
            return [text] if text else []

        if name == "blockquote":
            inner = self._render_blocks(element, list_depth=list_depth)
            if not inner:
                return []
            merged = "\n\n".join(inner)
            prefixed = "\n".join(
                f"> {line}" if line.strip() else ">"
                for line in merged.splitlines()
            )
            return [prefixed]

        if name == "pre":
            return [self._render_preformatted(element)]

        if name == "ul":
            return [self._render_list(element, ordered=False, depth=list_depth)]

        if name == "ol":
            return [self._render_list(element, ordered=True, depth=list_depth)]

        if name == "hr":
            return ["---"]

        if name == "table":
            table = self._render_table(element)
            return [table] if table else []

        if ns == _AC_URI and name == "image":
            image = self._render_image(element)
            return [image] if image else []

        if name in {"div", "section", "article"}:
            return self._render_blocks(element, list_depth=list_depth)

        text = self._render_inline(element).strip()
        return [text] if text else []

    def _render_macro(self, element: ET.Element) -> str:
        macro_name = attr_value(element, "ac:name") or attr_value(element, "name") or "unknown"

        if macro_name == "code":
            language = self._macro_parameter(element, "language") or ""
            body = self._macro_plain_text_body(element)
            return self._fenced_code_block(body, language)

        if macro_name == "toc":
            return "[TOC]"

        if macro_name == "noformat":
            body = self._macro_plain_text_body(element)
            return self._fenced_code_block(body, "")

        if macro_name in {"info", "note", "warning", "tip"}:
            body = self._macro_rich_text_body(element)
            if body:
                self._warn(f"Макрос {macro_name} был упрощен до обычной цитаты.")
                quoted = "\n".join(
                    f"> {line}" if line.strip() else ">"
                    for line in body.splitlines()
                )
                return quoted
            self._warn(f"Макрос {macro_name} был пропущен при экспорте.")
            return ""

        rich_text = self._macro_rich_text_body(element)
        if rich_text:
            self._warn(f"Макрос {macro_name} был упрощен до текстового содержимого.")
            return rich_text

        self._warn(f"Макрос {macro_name} был пропущен при экспорте.")
        return ""

    def _render_preformatted(self, element: ET.Element) -> str:
        language = ""
        body = ""

        for child in element:
            if local_name(child.tag) == "code":
                body = element_text_content(child)
                break

        if not body:
            body = element_text_content(element)

        return self._fenced_code_block(body, language)

    def _render_list(self, element: ET.Element, ordered: bool, depth: int) -> str:
        lines: List[str] = []
        index = 1

        for child in element:
            if local_name(child.tag) != "li":
                continue

            indent = "  " * depth
            marker = f"{index}." if ordered else "-"
            main_text = self._render_list_item_text(child).strip()
            lines.append(f"{indent}{marker} {main_text}".rstrip())

            nested_blocks = self._render_nested_lists(child, depth + 1)
            if nested_blocks:
                lines.append(nested_blocks)

            if ordered:
                index += 1

        return "\n".join(line for line in lines if line.strip())

    def _render_list_item_text(self, element: ET.Element) -> str:
        fragments: List[str] = []

        if element.text:
            fragments.append(self._normalize_inline_text(element.text))

        for child in element:
            name = local_name(child.tag)
            ns = namespace_uri(child.tag)

            if name in {"ul", "ol"}:
                continue

            if ns == _AC_URI and name == "structured-macro":
                rendered = self._render_macro(child)
            else:
                rendered = self._render_inline_element(child)

            if rendered:
                fragments.append(rendered)
            if child.tail:
                fragments.append(self._normalize_inline_text(child.tail))

        return self._normalize_inline_text("".join(fragments)).strip()

    def _render_nested_lists(self, element: ET.Element, depth: int) -> str:
        nested: List[str] = []
        for child in element:
            name = local_name(child.tag)
            if name == "ul":
                nested.append(self._render_list(child, ordered=False, depth=depth))
            elif name == "ol":
                nested.append(self._render_list(child, ordered=True, depth=depth))
        return "\n".join(block for block in nested if block.strip())

    def _render_table(self, element: ET.Element) -> str:
        rows: List[List[str]] = []
        has_header = False

        for row in element.iter():
            if local_name(row.tag) != "tr":
                continue
            cells: List[str] = []
            row_has_header = False
            for cell in row:
                cell_name = local_name(cell.tag)
                if cell_name not in {"th", "td"}:
                    continue
                if cell_name == "th":
                    row_has_header = True
                cells.append(self._render_inline(cell).strip())
            if cells:
                rows.append(cells)
                has_header = has_header or row_has_header

        if not rows:
            return ""

        if not has_header:
            self._warn("Таблица без заголовка была экспортирована с первой строкой в роли header.")

        width = len(rows[0])
        normalized = [row + [""] * (width - len(row)) for row in rows]
        header = normalized[0]
        separator = ["---"] * width
        body_rows = normalized[1:]

        markdown_rows = [
            f"| {' | '.join(header)} |",
            f"| {' | '.join(separator)} |",
        ]
        markdown_rows.extend(f"| {' | '.join(row)} |" for row in body_rows)
        return "\n".join(markdown_rows)

    def _render_image(self, element: ET.Element) -> str:
        target = self._resolve_confluence_resource_target(element)
        if not target:
            self._warn("Изображение без attachment/url было пропущено при экспорте.")
            return ""

        alt = target.split("/")[-1]
        if target.startswith("attachment:"):
            alt = target.removeprefix("attachment:")
        return f"![{alt}]({target})"

    def _render_inline(self, element: ET.Element) -> str:
        fragments: List[str] = []

        if element.text:
            fragments.append(self._normalize_inline_text(element.text))

        for child in element:
            fragments.append(self._render_inline_element(child))
            if child.tail:
                fragments.append(self._normalize_inline_text(child.tail))

        return self._normalize_inline_text("".join(fragments))

    def _render_inline_element(self, element: ET.Element) -> str:
        name = local_name(element.tag)
        ns = namespace_uri(element.tag)

        if ns == _AC_URI and name == "structured-macro":
            return self._render_macro(element)

        if ns == _AC_URI and name == "link":
            return self._render_confluence_link(element)

        if ns == _AC_URI and name == "image":
            return self._render_image(element)

        if ns == _AC_URI and name in {"plain-text-link-body", "link-body", "layout", "layout-section", "layout-cell", "placeholder"}:
            return self._render_inline(element)

        if name in {"strong", "b"}:
            text = self._render_inline(element).strip()
            return f"**{text}**" if text else ""

        if name in {"em", "i"}:
            text = self._render_inline(element).strip()
            return f"*{text}*" if text else ""

        if name == "code":
            text = element_text_content(element).strip()
            return f"`{text}`" if text else ""

        if name == "br":
            return "\n"

        if name == "a":
            href = attr_value(element, "href") or ""
            text = self._render_inline(element).strip() or href
            return f"[{text}]({href})" if href else text

        if name in {"span", "div", "p"}:
            return self._render_inline(element)

        return self._render_inline(element)

    def _render_confluence_link(self, element: ET.Element) -> str:
        text = ""
        target = None

        for child in element:
            child_name = local_name(child.tag)
            child_ns = namespace_uri(child.tag)

            if child_ns == _RI_URI:
                target = self._resolve_resource_element_target(child)
            elif child_ns == _AC_URI and child_name in {"link-body", "plain-text-link-body"}:
                text = self._render_inline(child).strip()

        target = target or ""
        text = text or target

        if target:
            return f"[{text}]({target})"
        return text

    def _resolve_confluence_resource_target(self, element: ET.Element) -> str | None:
        for child in element:
            if namespace_uri(child.tag) == _RI_URI:
                return self._resolve_resource_element_target(child)
        return None

    def _resolve_resource_element_target(self, element: ET.Element) -> str | None:
        name = local_name(element.tag)

        if name == "url":
            return attr_value(element, "ri:value") or attr_value(element, "value")

        if name == "attachment":
            filename = attr_value(element, "ri:filename") or attr_value(element, "filename")
            return f"attachment:{filename}" if filename else None

        if name == "page":
            title = (
                attr_value(element, "ri:content-title")
                or attr_value(element, "ri:page-title")
                or attr_value(element, "content-title")
            )
            return f"page:{title}" if title else None

        return None

    def _macro_parameter(self, element: ET.Element, name: str) -> str:
        for child in element:
            if namespace_uri(child.tag) == _AC_URI and local_name(child.tag) == "parameter":
                parameter_name = attr_value(child, "ac:name") or attr_value(child, "name")
                if parameter_name == name:
                    return element_text_content(child).strip()
        return ""

    def _macro_plain_text_body(self, element: ET.Element) -> str:
        for child in element:
            if namespace_uri(child.tag) == _AC_URI and local_name(child.tag) == "plain-text-body":
                return (child.text or "").strip()
        return ""

    def _macro_rich_text_body(self, element: ET.Element) -> str:
        for child in element:
            if namespace_uri(child.tag) == _AC_URI and local_name(child.tag) == "rich-text-body":
                blocks = self._render_blocks(child, list_depth=0)
                return "\n\n".join(block for block in blocks if block.strip())
        return ""

    @staticmethod
    def _fenced_code_block(body: str, language: str) -> str:
        code = body.strip("\n")
        return f"```{language}\n{code}\n```".rstrip()

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    @staticmethod
    def _normalize_inline_text(text: str) -> str:
        if not text:
            return ""
        normalized = text.replace("\xa0", " ")
        normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)
        normalized = re.sub(r" *\n *", "\n", normalized)
        return normalized

    @staticmethod
    def _normalize_document(text: str) -> str:
        normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
        return normalized.strip()
