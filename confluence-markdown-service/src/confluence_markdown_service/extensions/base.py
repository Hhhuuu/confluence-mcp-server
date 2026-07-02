"""Базовые контракты для расширений markdown bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from ..importer import ConfluenceMarkdownImporter
    from ..storage_renderer import StorageMarkdownRenderer


@dataclass(frozen=True)
class MarkdownImportTransformResult:
    """Результат обработки XML-элемента на этапе Markdown -> Confluence."""

    handled: bool = False
    replacement: Optional[ET.Element] = None


@dataclass(frozen=True)
class MarkdownRenderResult:
    """Результат обработки macro/block на этапе Confluence -> Markdown."""

    handled: bool = False
    markdown: str = ""


@dataclass(frozen=True)
class ExtensionInfo:
    """Краткая информация о доступном расширении."""

    name: str
    description: str


class ConfluenceMarkdownExtension:
    """
    Базовый класс расширения markdown bridge.

    Расширение может участвовать в двух направлениях:
    - preprocess Markdown перед конвертацией в XHTML
    - transform XHTML/storage узлов при импорте в Confluence
    - render Confluence macro обратно в markdown
    """

    name: str = "base"
    description: str = "Базовое расширение"

    def preprocess_markdown(self, markdown_text: str) -> str:
        """Изменить raw markdown перед стандартной markdown-конвертацией."""

        return markdown_text

    def transform_import_element(
        self,
        importer: ConfluenceMarkdownImporter,
        element: ET.Element,
    ) -> MarkdownImportTransformResult:
        """Обработать XML-элемент на этапе Markdown -> Confluence."""

        return MarkdownImportTransformResult()

    def render_macro(
        self,
        renderer: StorageMarkdownRenderer,
        element: ET.Element,
    ) -> MarkdownRenderResult:
        """Обработать Confluence macro/block на этапе Confluence -> Markdown."""

        return MarkdownRenderResult()
