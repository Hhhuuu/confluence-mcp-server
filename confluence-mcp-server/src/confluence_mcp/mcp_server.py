"""Реализация общего MCP-сервера для сценариев работы с Confluence."""

from __future__ import annotations

import os
from typing import List, Literal, Optional

from confluence_markdown_service import (
    ConfluenceMarkdownExporter,
    ConfluenceMarkdownImporter,
    export_page_to_markdown_file,
    export_page_tree_to_markdown_files,
    list_builtin_markdown_extensions,
)
from mcp.server.fastmcp import FastMCP
from confluence_pagecreator_service import CreatePagesRequest, load_app_config

from .proofread import (
    build_page_comment_body_storage,
    check_text_with_languagetool,
    markdown_to_plain_text,
)
from .runtime import (
    load_runtime_client,
    load_runtime_service,
    resolve_config_path,
    resolve_secrets_path,
)

mcp = FastMCP(
    name="confluence-mcp",
    instructions=(
        "Инструменты для создания структуры страниц, экспорта и импорта Markdown, "
        "а также для отладки доступа к пространствам и страницам Confluence."
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
        "jira_server_id": _jira_builtin_options().get("jira_server_id"),
        "jira_server_name": _jira_builtin_options().get("jira_server_name"),
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
    content_format: Literal["markdown", "storage"] = "markdown",
) -> dict:
    prepared_content = content
    if content and content_format == "markdown":
        client, _ = load_runtime_client()
        try:
            importer = ConfluenceMarkdownImporter(
                client,
                builtin_extension_options=_builtin_extension_options(),
            )
            prepared_content = importer.preview_markdown_to_storage(content).storage
        finally:
            client.close()

    service, default_space_key = load_runtime_service()
    result = service.create_pages(
        CreatePagesRequest(
            paths=paths,
            space_key=space_key,
            content=prepared_content,
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
    name="move_page",
    description=(
        "Изменить порядок или положение страницы: before/after — до/после "
        "целевой страницы, append — последней дочерней страницей цели."
    ),
)
def move_page(
    page_id: str,
    target_page_id: str,
    position: Literal["before", "after", "append"],
) -> dict:
    client, _ = load_runtime_client()
    try:
        result = client.move_page(
            page_id=page_id,
            target_page_id=target_page_id,
            position=position,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="list_markdown_extensions",
    description="Показать встроенные markdown-расширения для Confluence markdown bridge.",
)
def list_markdown_extensions() -> dict:
    return {
        "extensions": [
            extension.__dict__
            for extension in list_builtin_markdown_extensions()
        ]
    }


@mcp.tool(
    name="export_page_to_markdown",
    description="Выгрузить страницу Confluence в Markdown с предупреждениями о потерянных макросах.",
)
def export_page_to_markdown(
    page_id: str,
    enabled_extensions: Optional[List[str]] = None,
    table_mode: str = "auto",
) -> dict:
    client, _ = load_runtime_client()
    try:
        exporter = ConfluenceMarkdownExporter(
            client,
            enabled_extensions=enabled_extensions,
            table_mode=table_mode,
            builtin_extension_options=_builtin_extension_options(),
        )
        result = exporter.export_page_to_markdown(page_id)
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="export_page_to_markdown_file",
    description="Выгрузить страницу Confluence в Markdown-файл на локальном диске.",
)
def export_page_to_markdown_file_tool(
    page_id: str,
    output_path: str,
    enabled_extensions: Optional[List[str]] = None,
    table_mode: str = "auto",
) -> dict:
    client, _ = load_runtime_client()
    try:
        result = export_page_to_markdown_file(
            client=client,
            page_id=page_id,
            output_path=output_path,
            enabled_extensions=enabled_extensions,
            table_mode=table_mode,
            builtin_extension_options=_builtin_extension_options(),
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="export_page_tree_to_markdown_files",
    description="Выгрузить страницу и все её дочерние страницы в дерево локальных Markdown-файлов.",
)
def export_page_tree_to_markdown_files_tool(
    page_id: str,
    output_dir: str,
    enabled_extensions: Optional[List[str]] = None,
    table_mode: str = "auto",
) -> dict:
    client, _ = load_runtime_client()
    try:
        result = export_page_tree_to_markdown_files(
            client=client,
            root_page_id=page_id,
            output_dir=output_dir,
            enabled_extensions=enabled_extensions,
            table_mode=table_mode,
            builtin_extension_options=_builtin_extension_options(),
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="preview_markdown_to_storage",
    description="Преобразовать Markdown в Confluence storage format без публикации страницы.",
)
def preview_markdown_to_storage(markdown_text: str, enabled_extensions: Optional[List[str]] = None) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
        result = importer.preview_markdown_to_storage(markdown_text)
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="preview_markdown_file_to_storage",
    description="Преобразовать локальный Markdown-файл в Confluence storage format без публикации.",
)
def preview_markdown_file_to_storage(file_path: str, enabled_extensions: Optional[List[str]] = None) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
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
    enabled_extensions: Optional[List[str]] = None,
) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
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
    enabled_extensions: Optional[List[str]] = None,
) -> dict:
    client, default_space_key = load_runtime_client()
    effective_space_key = space_key or default_space_key
    if not effective_space_key:
        client.close()
        raise ValueError("Не указан space_key и отсутствует значение по умолчанию.")

    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
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
    enabled_extensions: Optional[List[str]] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
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
    enabled_extensions: Optional[List[str]] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        importer = ConfluenceMarkdownImporter(
            client,
            enabled_extensions=enabled_extensions,
            builtin_extension_options=_builtin_extension_options(),
        )
        result = importer.update_page_from_markdown_file(
            page_id=page_id,
            file_path=file_path,
            title=title,
        )
        return result.model_dump(mode="json")
    finally:
        client.close()


@mcp.tool(
    name="proofread_confluence_page",
    description=(
        "Проверить орфографию и пунктуацию страницы Confluence через LanguageTool "
        "без записи комментариев."
    ),
)
def proofread_confluence_page(
    page_id: str,
    language: str = "ru-RU",
    max_suggestions: int = 20,
    languagetool_url: Optional[str] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        exporter = ConfluenceMarkdownExporter(
            client,
            builtin_extension_options=_builtin_extension_options(),
        )
        exported = exporter.export_page_to_markdown(page_id)
        plain_text = markdown_to_plain_text(exported.markdown)
        result = check_text_with_languagetool(
            plain_text,
            language=language,
            languagetool_url=languagetool_url or os.getenv("LANGUAGETOOL_URL", "http://127.0.0.1:8010"),
            max_suggestions=max_suggestions,
        )
        payload = result.to_dict()
        payload.update(
            {
                "page_id": exported.page_id,
                "title": exported.title,
                "space_key": exported.space_key,
                "warnings": exported.warnings,
                "dry_run": True,
            }
        )
        return payload
    finally:
        client.close()


@mcp.tool(
    name="add_proofread_inline_comments",
    description=(
        "Проверить страницу Confluence через LanguageTool и добавить найденные "
        "замечания как inline comments в Cloud или обычный page comment в Server/Data Center. "
        "Этот tool пишет комментарии в Confluence."
    ),
)
def add_proofread_inline_comments(
    page_id: str,
    language: str = "ru-RU",
    max_comments: int = 20,
    languagetool_url: Optional[str] = None,
) -> dict:
    client, _ = load_runtime_client()
    try:
        exporter = ConfluenceMarkdownExporter(
            client,
            builtin_extension_options=_builtin_extension_options(),
        )
        exported = exporter.export_page_to_markdown(page_id)
        plain_text = markdown_to_plain_text(exported.markdown)
        result = check_text_with_languagetool(
            plain_text,
            language=language,
            languagetool_url=languagetool_url or os.getenv("LANGUAGETOOL_URL", "http://127.0.0.1:8010"),
            max_suggestions=max_comments,
        )

        deployment = getattr(getattr(client, "_config", None), "deployment", "cloud")
        if deployment != "cloud":
            suggestions = result.suggestions[:max_comments]
            if not suggestions:
                return {
                    "page_id": exported.page_id,
                    "title": exported.title,
                    "language": language,
                    "comment_mode": "page_comment",
                    "created_count": 0,
                    "failed_count": 0,
                    "suggestion_count": 0,
                    "comment": None,
                    "truncated": result.truncated,
                }
            created = client.create_page_comment(
                page_id=exported.page_id,
                body_storage=build_page_comment_body_storage(suggestions),
            )
            return {
                "page_id": exported.page_id,
                "title": exported.title,
                "language": language,
                "comment_mode": "page_comment",
                "created_count": 1,
                "failed_count": 0,
                "suggestion_count": len(suggestions),
                "comment": created,
                "truncated": result.truncated,
            }

        created_comments = []
        failed_comments = []
        for suggestion in result.suggestions[:max_comments]:
            try:
                created = client.create_inline_comment(
                    page_id=exported.page_id,
                    body_storage=suggestion.comment_body_storage,
                    text_selection=suggestion.text_selection,
                    text_selection_match_count=suggestion.text_selection_match_count,
                    text_selection_match_index=suggestion.text_selection_match_index,
                )
                created_comments.append(
                    {
                        "suggestion": suggestion.to_dict(),
                        "comment": created,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - возвращаем частичный результат пользователю
                failed_comments.append(
                    {
                        "suggestion": suggestion.to_dict(),
                        "error": str(exc),
                    }
                )

        return {
            "page_id": exported.page_id,
            "title": exported.title,
            "language": language,
            "comment_mode": "inline_comment",
            "created_count": len(created_comments),
            "failed_count": len(failed_comments),
            "created_comments": created_comments,
            "failed_comments": failed_comments,
            "truncated": result.truncated,
        }
    finally:
        client.close()


def _jira_builtin_options() -> dict[str, str]:
    config = load_app_config(resolve_config_path())
    jira_options: dict[str, str] = {}
    if config.confluence.jira_server_id:
        jira_options["jira_server_id"] = config.confluence.jira_server_id
    if config.confluence.jira_server_name:
        jira_options["jira_server_name"] = config.confluence.jira_server_name
    return jira_options


def _builtin_extension_options() -> dict:
    jira_options = _jira_builtin_options()
    config = load_app_config(resolve_config_path())
    options: dict = {
        "mermaid_diagrams": {"enabled": config.confluence.deployment == "server"}
    }
    if jira_options:
        options["jira_links"] = jira_options
    return options


def main() -> None:
    """
    Запустить MCP-сервер.

    По умолчанию сервер стартует в `stdio`-режиме.
    """

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
