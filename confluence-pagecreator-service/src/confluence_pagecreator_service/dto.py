"""DTO сервисного слоя page creator."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CreatePagesRequest(BaseModel):
    """
    Входные данные сценария создания страниц.

    Attributes:
        paths: Список путей страниц.
        space_key: Явно заданное пространство. Если не передано,
            используется значение по умолчанию из конфига.
        content: Базовое содержимое создаваемых страниц.
        dry_run: Если `True`, страницы не создаются, а только строится план.
    """

    paths: List[str]
    space_key: Optional[str] = None
    content: str = ""
    dry_run: bool = False


class PlannedPage(BaseModel):
    """Один элемент результата планирования или создания."""

    title: str
    level: int
    parent_title: Optional[str] = None
    page_id: Optional[str] = None
    page_url: Optional[str] = None
    action: str


class CreatePagesResult(BaseModel):
    """
    Результат выполнения сценария создания страниц.

    Attributes:
        space_key: Пространство, в котором выполнялась обработка.
        structure: Текстовое представление структуры страниц.
        items: Список элементов результата в порядке обработки.
    """

    space_key: str
    structure: str
    items: List[PlannedPage] = Field(default_factory=list)
