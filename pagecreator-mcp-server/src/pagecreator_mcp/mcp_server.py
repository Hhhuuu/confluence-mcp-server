"""Реализация MCP-сервера для PageCreator."""

from __future__ import annotations

import os
from typing import List, Optional

from confluence_markdown_service import (
    ConfluenceMarkdownExporter,
    ConfluenceMarkdownImporter,
    export_page_to_markdown_file,
)
from mcp.server.fastmcp import FastMCP
from pagecreator_service import CreatePagesRequest

from .runtime import (
    load_runtime_client,
    load_runtime_service,
    resolve_config_path,
    resolve_secrets_path,
)

mcp = FastMCP(
    name="confluence-mcp",
    instructions=(
        "Инструменты для планирования и создания иерархии страниц в Confluence Cloud, "
        "а также для отладки доступа к пространствам и страницам."
    ),
    host=os.getenv("PAGECREATOR_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("PAGECREATOR_MCP_PORT", "8000")),
)


@mcp.tool(
    name="show_runtime_config",
    description="Показать текущие пути к конфигу и секретам, а также активный base_url и default_space_key.",
)
def show_runtime_config() -> dict:
    config_path = resolve_config_path()
    secrets_path = resolve_secrets_path()
    service, default_space_key = load_runtime_service()
    del service
    client, _ = load_runtime_client()
    try:
        base_url = client._config.base_url  # noqa: SLF001
    finally:
        client.close()

    return {
        "config_path": str(config_path),
        "secrets_path": str(secrets_path),
        "base_url": base_url,
        "default_space_key": default_space_key,
    }


@mcp.tool(
    name="plan_pages",
    description="Построить план создания страниц без записи в Confluence.",
)
def plan_pages(paths: List[str], space_key: Optional[str] = None) -> dict:
    service, default_space_key = load_runtime_service()
    result = service.create_pages(
        CreatePagesRequest(paths=paths, space_key=space_key, dry_run=True),
        default_space_key=default_space_key,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="create_pages",
    description="Создать страницы в Confluence по переданным путям.",
)
def create_pages(
    paths: List[str],
    space_key: Optional[str] = None,
    content: str = "",
) -> dict:
    service, default_space_key = load_runtime_service()
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


@mcp.tool(
    name="get_current_user",
    description="Проверить авторизацию и вернуть текущего пользователя Confluence Cloud.",
)
def get_current_user() -> dict:
    client, _ = load_runtime_client()
    try:
        user = client.current_user()
        return user.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="get_space",
    description="Получить информацию о пространстве Confluence, включая домашнюю страницу.",
)
def get_space(space_key: Optional[str] = None) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        space = client.get_space(effective_space_key)
        return space.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="find_page",
    description="Найти страницы по заголовку в указанном пространстве.",
)
def find_page(title: str, space_key: Optional[str] = None) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        pages = client.find_page(title=title, space_key=effective_space_key)
        return pages.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="get_page",
    description="Получить страницу по id. При include_storage=true возвращает body.storage и пространство.",
)
def get_page(page_id: str, include_storage: bool = False) -> dict:
    client, _ = load_runtime_client()
    try:
        if include_storage:
            page = client.find_page_by_id_with_storage(page_id)
        else:
            page = client.find_page_by_id(page_id)
        return page.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="export_page_to_markdown",
    description="Выгрузить страницу Confluence в Markdown с предупреждениями о потерянных макросах.",
)
def export_page_to_markdown(page_id: str) -> dict:
    client, _ = load_runtime_client()
    try:
        exporter = ConfluenceMarkdownExporter(client)
        result = exporter.export_page_to_markdown(page_id)
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="export_page_to_markdown_file",
    description="Выгрузить страницу Confluence в Markdown-файл на локальном диске.",
)
def export_page_to_markdown_file_tool(page_id: str, output_path: str) -> dict:
    client, _ = load_runtime_client()
    try:
        result = export_page_to_markdown_file(
            client=client,
            page_id=page_id,
            output_path=output_path,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="preview_markdown_to_storage",
    description="Преобразовать Markdown в Confluence storage format без публикации страницы.",
)
def preview_markdown_to_storage(markdown_text: str) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.preview_markdown_to_storage(markdown_text)
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="preview_markdown_file_to_storage",
    description="Преобразовать локальный Markdown-файл в Confluence storage format без публикации.",
)
def preview_markdown_file_to_storage(file_path: str) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.preview_markdown_file_to_storage(file_path)
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="create_page_from_markdown",
    description="Создать страницу Confluence из Markdown под указанным parent_id.",
)
def create_page_from_markdown(
    title: str,
    markdown_text: str,
    parent_id: str,
    space_key: Optional[str] = None,
) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.create_page_from_markdown(
            title=title,
            markdown_text=markdown_text,
            parent_id=parent_id,
            space_key=effective_space_key,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="create_page_from_markdown_file",
    description="Создать страницу Confluence из локального Markdown-файла.",
)
def create_page_from_markdown_file(
    title: str,
    file_path: str,
    parent_id: str,
    space_key: Optional[str] = None,
) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.create_page_from_markdown_file(
            title=title,
            file_path=file_path,
            parent_id=parent_id,
            space_key=effective_space_key,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="update_page_from_markdown",
    description="Обновить существующую страницу Confluence содержимым из Markdown.",
)
def update_page_from_markdown(
    page_id: str,
    markdown_text: str,
    title: Optional[str] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.update_page_from_markdown(
            page_id=page_id,
            markdown_text=markdown_text,
            title=title,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="update_page_from_markdown_file",
    description="Обновить страницу Confluence содержимым из локального Markdown-файла.",
)
def update_page_from_markdown_file(
    page_id: str,
    file_path: str,
    title: Optional[str] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(client)
        result = importer.update_page_from_markdown_file(
            page_id=page_id,
            file_path=file_path,
            title=title,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


def main() -> None:
    """
    Запустить MCP-сервер.

    По умолчанию сервер стартует в `stdio`-режиме.
    """

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
