"""Инструменты MCP-сервера для создания страниц."""

from __future__ import annotations

from typing import List, Optional

from pagecreator_service import CreatePagesRequest, PageCreatorService


def plan_pages(
    service: PageCreatorService,
    paths: List[str],
    space_key: Optional[str] = None,
    default_space_key: Optional[str] = None,
) -> dict:
    """
    Построить план создания страниц без записи в Confluence.

    Args:
        service: Экземпляр сервисного слоя.
        paths: Список путей страниц.
        space_key: Явно заданное пространство.
        default_space_key: Пространство по умолчанию.

    Returns:
        JSON-совместимый словарь с результатом планирования.
    """

    result = service.create_pages(
        CreatePagesRequest(paths=paths, space_key=space_key, dry_run=True),
        default_space_key=default_space_key,
    )
    return result.model_dump(mode="json")


def create_pages(
    service: PageCreatorService,
    paths: List[str],
    space_key: Optional[str] = None,
    default_space_key: Optional[str] = None,
    content: str = "",
) -> dict:
    """
    Создать страницы в Confluence по списку путей.

    Args:
        service: Экземпляр сервисного слоя.
        paths: Список путей страниц.
        space_key: Явно заданное пространство.
        default_space_key: Пространство по умолчанию.
        content: Базовое содержимое создаваемых страниц.

    Returns:
        JSON-совместимый словарь с результатом выполнения.
    """

    result = service.create_pages(
        CreatePagesRequest(
            paths=paths,
            space_key=space_key,
            content=content,
            dry_run=False,
        ),
        default_space_key=default_space_key,
    )
    return result.model_dump(mode="json")
