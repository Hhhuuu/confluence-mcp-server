"""Модели результата для markdown bridge."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MarkdownAttachmentResult(BaseModel):
    """
    Информация о локальном файле, который был загружен во вложения страницы.

    Attributes:
        filename: Имя вложения в Confluence.
        source_path: Локальный путь до исходного файла.
        attachment_id: Идентификатор вложения в Confluence.
        action: `created`, если вложение создано, или `updated`, если обновлено.
    """

    filename: str
    source_path: str
    attachment_id: Optional[str] = None
    action: str


class MarkdownTreeExportItem(BaseModel):
    """
    Информация об одной выгруженной странице дерева.

    Attributes:
        page_id: Идентификатор страницы Confluence.
        title: Заголовок страницы.
        depth: Глубина относительно корня.
        output_path: Путь до созданного Markdown-файла.
        warnings: Предупреждения конкретно для этой страницы.
    """

    page_id: str
    title: str
    depth: int
    output_path: str
    warnings: List[str] = Field(default_factory=list)


class MarkdownTreeExportResult(BaseModel):
    """
    Результат выгрузки дерева страниц в набор Markdown-файлов.

    Attributes:
        root_page_id: Идентификатор корневой страницы.
        root_title: Заголовок корневой страницы.
        output_dir: Базовая директория выгрузки.
        items: Список выгруженных страниц.
        warnings: Общие предупреждения по всей операции.
    """

    root_page_id: str
    root_title: str
    output_dir: str
    items: List[MarkdownTreeExportItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MarkdownExportResult(BaseModel):
    """
    Результат экспорта страницы Confluence в Markdown.

    Attributes:
        page_id: Идентификатор страницы Confluence.
        title: Заголовок страницы.
        space_key: Ключ пространства, если удалось определить.
        markdown: Сгенерированный Markdown.
        output_path: Путь до файла, если результат был сохранен на диск.
        warnings: Предупреждения о потерянных или упрощенных конструкциях.
    """

    page_id: str
    title: str
    space_key: Optional[str] = None
    markdown: str
    output_path: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class MarkdownPreviewResult(BaseModel):
    """
    Результат предварительного преобразования Markdown в storage format.

    Attributes:
        storage: Содержимое, готовое для публикации в `body.storage.value`.
        source_path: Путь до исходного Markdown-файла, если preview строился из файла.
        warnings: Предупреждения об упрощениях или неподдерживаемых конструкциях.
    """

    storage: str
    source_path: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class MarkdownPublishResult(BaseModel):
    """
    Результат публикации Markdown в Confluence.

    Attributes:
        title: Заголовок опубликованной страницы.
        page_id: Идентификатор страницы.
        page_url: URL страницы.
        source_path: Путь до исходного Markdown-файла, если публикация шла из файла.
        warnings: Предупреждения, полученные при преобразовании Markdown в storage.
    """

    title: str
    page_id: str
    page_url: str
    source_path: Optional[str] = None
    attachments: List[MarkdownAttachmentResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
