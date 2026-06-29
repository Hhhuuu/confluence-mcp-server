"""Подготовка Confluence storage format к экспорту в Markdown."""

from __future__ import annotations

import html.entities
import re
from typing import List
from xml.etree import ElementTree as ET

from .exceptions import MarkdownBridgeError

_NAMESPACES = {
    "ac": "urn:ac",
    "ri": "urn:ri",
}

_XML_PREDEFINED_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


def parse_storage_document(storage_value: str) -> ET.Element:
    """
    Распарсить storage-разметку Confluence в XML-дерево.

    Args:
        storage_value: Содержимое `body.storage.value`.

    Returns:
        Корневой элемент-обертка, содержащий тело страницы.

    Raises:
        MarkdownBridgeError: Если storage-разметку не удалось распарсить.
    """

    normalized_storage = _decode_non_xml_entities(storage_value or "")
    wrapped = (
        "<root "
        'xmlns:ac="urn:ac" '
        'xmlns:ri="urn:ri"'
        ">"
        f"{normalized_storage}"
        "</root>"
    )
    try:
        return ET.fromstring(wrapped)
    except ET.ParseError as exc:
        raise MarkdownBridgeError(
            f"Не удалось распарсить Confluence storage format: {exc}"
        ) from exc


def local_name(tag: str) -> str:
    """Вернуть локальное имя XML-тега без namespace."""

    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def namespace_uri(tag: str) -> str:
    """Вернуть URI namespace для XML-тега."""

    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def attr_value(element: ET.Element, name: str) -> str | None:
    """
    Получить значение обычного или namespaced-атрибута.

    Args:
        element: XML-элемент.
        name: Имя атрибута, например `href`, `ri:value`, `ac:name`.
    """

    if ":" not in name:
        return element.attrib.get(name)

    prefix, local = name.split(":", 1)
    namespace = _NAMESPACES.get(prefix)
    if not namespace:
        return None
    return element.attrib.get(f"{{{namespace}}}{local}")


def element_text_content(element: ET.Element) -> str:
    """
    Собрать текстовое содержимое элемента и всех его дочерних узлов.

    Args:
        element: XML-элемент.

    Returns:
        Текст без дополнительной markdown-обработки.
    """

    fragments: List[str] = []
    if element.text:
        fragments.append(element.text)

    for child in element:
        fragments.append(element_text_content(child))
        if child.tail:
            fragments.append(child.tail)

    return "".join(fragments)


def _decode_non_xml_entities(text: str) -> str:
    """
    Декодировать только те HTML entities, которые XML-парсер не понимает.

    Важно сохранить стандартные XML entities (`&lt;`, `&gt;`, `&amp;` и т.д.),
    иначе текст вроде `&lt;placeholder&gt;` превратится в псевдо-теги и сломает XML.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in _XML_PREDEFINED_ENTITIES:
            return match.group(0)

        html5_key = f"{name};"
        if html5_key in html.entities.html5:
            return html.entities.html5[html5_key]

        return match.group(0)

    return re.sub(r"&([A-Za-z][A-Za-z0-9]+);", replace, text)
