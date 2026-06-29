"""Модели результата для markdown bridge."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MarkdownExportResult(BaseModel):
    """
    Результат экспорта страницы Confluence в Markdown.

    Attributes:
        page_id: Идентификатор страницы Confluence.
        title: Заголовок страницы.
        space_key: Ключ пространства, если удалось определить.
        markdown: Сгенерированный Markdown.
        warnings: Предупреждения о потерянных или упрощенных конструкциях.
    """

    page_id: str
    title: str
    space_key: Optional[str] = None
    markdown: str
    warnings: List[str] = Field(default_factory=list)
