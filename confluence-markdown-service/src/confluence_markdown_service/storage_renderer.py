"""Рендеринг Confluence storage format в Markdown."""

from __future__ import annotations

import html
import re
from typing import Any, List, Sequence
from xml.etree import ElementTree as ET

from .extensions import ConfluenceMarkdownExtension, build_markdown_extension_registry
from .storage_normalizer import attr_value, element_text_content, local_name, namespace_uri

_AC_URI = "urn:ac"
_RI_URI = "urn:ri"
_TABLE_MODES = {"auto", "markdown", "html"}


class StorageMarkdownRenderer:
    """
    Ограниченный renderer Confluence storage format в Markdown.

    Renderer ориентирован на текст и базовые Markdown-конструкции.
    Неизвестные макросы и нестандартные блоки не валят экспорт: по возможности
    они упрощаются до текстового содержимого с предупреждением.
    """

    def __init__(
        self,
        *,
        enabled_extensions: Sequence[str] | None = None,
        extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
        table_mode: str = "auto",
        builtin_extension_options: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.warnings: list[str] = []
        if table_mode not in _TABLE_MODES:
            supported = ", ".join(sorted(_TABLE_MODES))
            raise ValueError(f"Неизвестный table_mode '{table_mode}'. Поддерживаются: {supported}.")
        self._table_mode = table_mode
        self._registry = build_markdown_extension_registry(
            enabled_extensions=enabled_extensions,
            extra_extensions=extra_extensions,
            builtin_extension_options=builtin_extension_options,
        )

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
        if not text:
            text = self._fallback_element_text(element)
        return [text] if text else []

    def _render_macro(self, element: ET.Element) -> str:
        for extension in self._registry.extensions:
            result = extension.render_macro(self, element)
            if result.handled:
                return result.markdown

        macro_name = self._macro_name(element)

        if macro_name == "markdown":
            body = self._macro_plain_text_body(element)
            if body:
                self._warn("Макрос markdown был выгружен как обычный markdown-текст.")
                return body.strip()

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

        plain_text = self._macro_plain_text_body(element)
        if plain_text:
            self._warn(f"Макрос {macro_name} был упрощен до plain-text содержимого.")
            return plain_text.strip()

        rich_text = self._macro_rich_text_body(element)
        if rich_text:
            self._warn(f"Макрос {macro_name} был упрощен до текстового содержимого.")
            return rich_text

        fallback_text = self._fallback_element_text(element)
        if fallback_text:
            self._warn(f"Макрос {macro_name} был упрощен до извлеченного текста.")
            return fallback_text

        self._warn(f"Макрос {macro_name} был пропущен при экспорте.")
        return ""

    def _macro_name(self, element: ET.Element) -> str:
        return attr_value(element, "ac:name") or attr_value(element, "name") or "unknown"

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
        effective_mode = self._resolve_table_mode(element)
        if effective_mode == "html":
            return self._render_table_as_html(element)

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

    def _resolve_table_mode(self, element: ET.Element) -> str:
        if self._table_mode in {"markdown", "html"}:
            return self._table_mode

        if self._table_is_complex(element):
            self._warn(
                "Таблица экспортирована как HTML, потому что содержит сложные элементы "
                "или форматирование, которое плохо переносится в markdown-table."
            )
            return "html"
        return "markdown"

    def _table_is_complex(self, element: ET.Element) -> bool:
        for cell in element.iter():
            cell_name = local_name(cell.tag)
            if cell_name not in {"th", "td"}:
                continue

            if any(
                attr_value(cell, attr_name) not in {None, "", "1"}
                for attr_name in ("colspan", "rowspan")
            ):
                return True

            if self._cell_has_complex_content(cell):
                return True
        return False

    def _cell_has_complex_content(self, cell: ET.Element) -> bool:
        block_children = 0
        for child in cell:
            name = local_name(child.tag)
            ns = namespace_uri(child.tag)

            if name == "br":
                return True
            if name in {"ul", "ol", "pre", "blockquote", "table", "hr"}:
                return True
            if ns == _AC_URI and name in {"structured-macro", "image"}:
                return True
            if name == "p":
                block_children += 1
                if block_children > 1:
                    return True
            if name == "div":
                return True
            if child.tail and "\n" in child.tail.strip():
                return True

        text = element_text_content(cell)
        return "\n" in text.strip()

    def _render_table_as_html(self, element: ET.Element) -> str:
        parts: list[str] = ["<table>"]
        grouped = self._group_table_rows(element)

        if grouped["thead"]:
            parts.append("<thead>")
            for row in grouped["thead"]:
                parts.append(self._render_table_row_as_html(row))
            parts.append("</thead>")

        if grouped["tbody"]:
            parts.append("<tbody>")
            for row in grouped["tbody"]:
                parts.append(self._render_table_row_as_html(row))
            parts.append("</tbody>")
        elif grouped["body"]:
            parts.append("<tbody>")
            for row in grouped["body"]:
                parts.append(self._render_table_row_as_html(row))
            parts.append("</tbody>")

        if grouped["tfoot"]:
            parts.append("<tfoot>")
            for row in grouped["tfoot"]:
                parts.append(self._render_table_row_as_html(row))
            parts.append("</tfoot>")

        parts.append("</table>")
        return "\n".join(parts)

    def _group_table_rows(self, element: ET.Element) -> dict[str, list[ET.Element]]:
        thead: list[ET.Element] = []
        tbody: list[ET.Element] = []
        tfoot: list[ET.Element] = []
        body: list[ET.Element] = []

        for child in element:
            name = local_name(child.tag)
            if name == "thead":
                thead.extend([row for row in child if local_name(row.tag) == "tr"])
            elif name == "tbody":
                tbody.extend([row for row in child if local_name(row.tag) == "tr"])
            elif name == "tfoot":
                tfoot.extend([row for row in child if local_name(row.tag) == "tr"])
            elif name == "tr":
                body.append(child)

        return {"thead": thead, "tbody": tbody, "tfoot": tfoot, "body": body}

    def _render_table_row_as_html(self, row: ET.Element) -> str:
        cells: list[str] = []
        for cell in row:
            cell_name = local_name(cell.tag)
            if cell_name not in {"th", "td"}:
                continue
            cells.append(self._render_table_cell_as_html(cell, cell_name))
        return f"<tr>{''.join(cells)}</tr>"

    def _render_table_cell_as_html(self, cell: ET.Element, tag_name: str) -> str:
        attrs: list[str] = []
        for attr_name in ("colspan", "rowspan"):
            value = attr_value(cell, attr_name) or cell.attrib.get(attr_name)
            if value:
                attrs.append(f' {attr_name}="{html.escape(value, quote=True)}"')

        content = self._render_table_cell_content_as_html(cell)
        return f"<{tag_name}{''.join(attrs)}>{content}</{tag_name}>"

    def _render_table_cell_content_as_html(self, cell: ET.Element) -> str:
        fragments: list[str] = []
        if cell.text and cell.text.strip():
            fragments.append(html.escape(self._normalize_inline_text(cell.text)))

        for child in cell:
            fragments.append(self._render_element_as_html(child))
            if child.tail and child.tail.strip():
                fragments.append(html.escape(self._normalize_inline_text(child.tail)))

        return "".join(fragment for fragment in fragments if fragment)

    def _render_element_as_html(self, element: ET.Element) -> str:
        name = local_name(element.tag)
        ns = namespace_uri(element.tag)

        if ns == _AC_URI and name == "structured-macro":
            return self._render_macro_as_html(element)
        if ns == _AC_URI and name == "link":
            return self._render_confluence_link_as_html(element)
        if ns == _AC_URI and name == "image":
            return self._render_image_as_html(element)

        if name in {"p", "div", "section", "article"}:
            return f"<p>{self._render_table_cell_content_as_html(element)}</p>"
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return f"<{name}>{self._render_table_cell_content_as_html(element)}</{name}>"
        if name == "span":
            return f"<span>{self._render_table_cell_content_as_html(element)}</span>"
        if name in {"strong", "b"}:
            return f"<strong>{self._render_table_cell_content_as_html(element)}</strong>"
        if name in {"em", "i"}:
            return f"<em>{self._render_table_cell_content_as_html(element)}</em>"
        if name == "code":
            content = html.escape(element_text_content(element).strip())
            return f"<code>{content}</code>" if content else ""
        if name == "pre":
            content = html.escape(element_text_content(element))
            return f"<pre>{content}</pre>" if content else ""
        if name == "br":
            return "<br/>"
        if name in {"ul", "ol"}:
            return self._render_list_as_html(element, ordered=(name == "ol"))
        if name == "blockquote":
            return f"<blockquote>{self._render_table_cell_content_as_html(element)}</blockquote>"
        if name == "hr":
            return "<hr/>"
        if name == "a":
            href = attr_value(element, "href") or element.attrib.get("href") or ""
            text = self._render_table_cell_content_as_html(element) or html.escape(href)
            if href:
                escaped_href = html.escape(href, quote=True)
                return f'<a href="{escaped_href}">{text}</a>'
            return text
        if name == "time":
            datetime_value = attr_value(element, "datetime") or element.attrib.get("datetime") or ""
            text = self._render_table_cell_content_as_html(element)
            escaped_datetime = html.escape(datetime_value, quote=True)
            return f'<time datetime="{escaped_datetime}">{text}</time>'

        return html.escape(self._fallback_element_text(element))

    def _render_macro_as_html(self, element: ET.Element) -> str:
        macro_name = self._macro_name(element)
        if macro_name == "status":
            title = html.escape(self._macro_parameter(element, "title").strip())
            colour = html.escape(self._macro_parameter(element, "colour").strip(), quote=True)
            subtle = html.escape(self._macro_parameter(element, "subtle").strip(), quote=True)
            attrs: list[str] = []
            if colour:
                attrs.append(f' color="{colour}"')
            if subtle:
                attrs.append(f' subtle="{subtle}"')
            return f"<status{''.join(attrs)}>{title}</status>"
        if macro_name == "code":
            language = html.escape(self._macro_parameter(element, "language").strip(), quote=True)
            title = html.escape(self._macro_parameter(element, "title").strip(), quote=True)
            body = html.escape(self._macro_plain_text_body(element))
            attrs: list[str] = []
            if language:
                attrs.append(f' data-language="{language}"')
            if title:
                attrs.append(f' data-title="{title}"')
            return f"<pre{''.join(attrs)}><code>{body}</code></pre>"

        rich_text = self._macro_rich_text_body(element)
        if rich_text:
            return f"<div>{html.escape(rich_text)}</div>"
        plain_text = self._macro_plain_text_body(element)
        if plain_text:
            return html.escape(plain_text)
        return html.escape(self._fallback_element_text(element))

    def _render_confluence_link_as_html(self, element: ET.Element) -> str:
        target = ""
        text = ""
        for child in element:
            child_name = local_name(child.tag)
            child_ns = namespace_uri(child.tag)
            if child_ns == _RI_URI:
                target = self._resolve_resource_element_target(child) or ""
            elif child_ns == _AC_URI and child_name in {"link-body", "plain-text-link-body"}:
                text = self._render_table_cell_content_as_html(child)
        text = text or html.escape(target)
        if not target:
            return text
        escaped_target = html.escape(target, quote=True)
        return f'<a href="{escaped_target}">{text}</a>'

    def _render_image_as_html(self, element: ET.Element) -> str:
        target = self._resolve_confluence_resource_target(element)
        if not target:
            return ""
        alt = html.escape(self._image_alt_text(element, target), quote=True)
        escaped_target = html.escape(target, quote=True)
        attrs = self._image_dimension_attrs(element)
        return f'<img src="{escaped_target}" alt="{alt}"{attrs}/>'

    def _render_list_as_html(self, element: ET.Element, *, ordered: bool) -> str:
        tag = "ol" if ordered else "ul"
        items: list[str] = []
        for child in element:
            if local_name(child.tag) != "li":
                continue
            items.append(f"<li>{self._render_table_cell_content_as_html(child)}</li>")
        return f"<{tag}>{''.join(items)}</{tag}>"

    def _render_image(self, element: ET.Element) -> str:
        target = self._resolve_confluence_resource_target(element)
        if not target:
            self._warn("Изображение без attachment/url было пропущено при экспорте.")
            return ""

        alt = self._image_alt_text(element, target)
        if self._image_has_dimensions(element):
            escaped_target = html.escape(target, quote=True)
            escaped_alt = html.escape(alt, quote=True)
            attrs = self._image_dimension_attrs(element)
            return f'<img src="{escaped_target}" alt="{escaped_alt}"{attrs}/>'
        return f"![{alt}]({target})"

    @staticmethod
    def _image_alt_text(element: ET.Element, target: str) -> str:
        alt = attr_value(element, "ac:alt") or attr_value(element, "alt")
        if alt:
            return alt
        if target.startswith("attachment:"):
            return target.removeprefix("attachment:")
        return target.split("/")[-1]

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

        for extension in self._registry.extensions:
            result = extension.render_inline_element(self, element)
            if result.handled:
                return result.markdown

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
        for extension in self._registry.extensions:
            result = extension.render_confluence_link(self, element)
            if result.handled:
                return result.markdown

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

    @staticmethod
    def _local_name(tag: str) -> str:
        return local_name(tag)

    @staticmethod
    def _namespace_uri(tag: str) -> str:
        return namespace_uri(tag)

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

    @staticmethod
    def _image_has_dimensions(element: ET.Element) -> bool:
        return bool(
            attr_value(element, "ac:width")
            or element.attrib.get(f"{{{_AC_URI}}}width")
            or attr_value(element, "ac:height")
            or element.attrib.get(f"{{{_AC_URI}}}height")
        )

    @staticmethod
    def _image_dimension_attrs(element: ET.Element) -> str:
        width = (
            attr_value(element, "ac:width")
            or element.attrib.get(f"{{{_AC_URI}}}width")
            or ""
        ).strip()
        height = (
            attr_value(element, "ac:height")
            or element.attrib.get(f"{{{_AC_URI}}}height")
            or ""
        ).strip()
        attrs: list[str] = []
        if width:
            attrs.append(f' width="{html.escape(width, quote=True)}"')
        if height:
            attrs.append(f' height="{html.escape(height, quote=True)}"')
        return "".join(attrs)

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

    def _fallback_element_text(self, element: ET.Element) -> str:
        """
        Аварийно извлечь текст из неизвестного блока или макроса.

        Метод не пытается сохранить форматирование 1:1, но помогает
        не потерять полезное текстовое содержимое полностью.
        """

        text = self._normalize_inline_text(element_text_content(element))
        return text.strip()

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
