"""Локальный HTTP API для ручной проверки page creator."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple, Union

from confluence_markdown_service import (
    ConfluenceMarkdownExporter,
    ConfluenceMarkdownImporter,
    MarkdownBridgeError,
    export_page_to_markdown_file,
)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from confluence_pagecreator_core import build_creation_plan, parse_paths, render_plan_structure
from confluence_pagecreator_service import (
    ConfigFileNotFoundError,
    CreatePagesRequest,
    InvalidConfigError,
    InvalidSecretsError,
    PageCreatorService,
    SecretsFileNotFoundError,
    load_app_config,
)

from .runtime import (
    load_runtime_client,
    load_runtime_service,
    resolve_config_path,
    resolve_secrets_path,
)

app = FastAPI(
    title="PageCreator Preview API",
    version="0.1.0",
    description="Локальный API для проверки логики планирования и создания страниц.",
)


class PlanRequest(BaseModel):
    """
    Входные данные для предварительного просмотра плана.

    Attributes:
        paths: Список путей страниц.
    """

    paths: List[str] = Field(default_factory=list)


class CreateRequest(BaseModel):
    """
    Входные данные для создания страниц.

    Attributes:
        paths: Список путей страниц.
        space_key: Явно заданное пространство.
        content: Базовое содержимое новых страниц.
    """

    paths: List[str] = Field(default_factory=list)
    space_key: Optional[str] = None
    content: str = ""


class MarkdownPreviewRequest(BaseModel):
    """
    Входные данные для preview markdown -> storage.

    Attributes:
        markdown: Исходный Markdown.
    """

    markdown: str = ""


class MarkdownCreateRequest(BaseModel):
    """
    Входные данные для создания страницы из Markdown.

    Attributes:
        title: Заголовок новой страницы.
        markdown: Исходный Markdown.
        parent_id: Идентификатор родительской страницы.
        space_key: Ключ пространства. Если не задан, берется из конфига.
    """

    title: str
    markdown: str = ""
    parent_id: str
    space_key: Optional[str] = None


class MarkdownUpdateRequest(BaseModel):
    """
    Входные данные для обновления страницы из Markdown.

    Attributes:
        page_id: Идентификатор страницы.
        markdown: Исходный Markdown.
        title: Необязательная замена заголовка страницы.
    """

    page_id: str
    markdown: str = ""
    title: Optional[str] = None


class MarkdownFilePreviewRequest(BaseModel):
    """Входные данные для preview markdown-файла."""

    file_path: str


class MarkdownFileCreateRequest(BaseModel):
    """Входные данные для создания страницы из markdown-файла."""

    title: str
    file_path: str
    parent_id: str
    space_key: Optional[str] = None


class MarkdownFileUpdateRequest(BaseModel):
    """Входные данные для обновления страницы из markdown-файла."""

    page_id: str
    file_path: str
    title: Optional[str] = None


class MarkdownFileExportRequest(BaseModel):
    """Входные данные для выгрузки страницы в markdown-файл."""

    output_path: str


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Проверить, что локальный API запущен.

    Returns:
        Короткий статус сервиса.
    """

    return {"status": "ok"}


@app.post("/api/v1/plan")
def plan(payload: PlanRequest) -> dict:
    """
    Построить план создания страниц без обращения к Confluence.

    Args:
        payload: Набор путей, которые нужно разобрать.

    Returns:
        JSON-совместимая структура с разобранными путями, плоским планом
        и текстовым деревом.
    """

    try:
        parsed_paths = parse_paths(payload.paths)
        plan_result = build_creation_plan(parsed_paths)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "paths": [
            {
                "raw_path": parsed_path.raw_path,
                "nodes": [
                    {
                        "title": node.title,
                        "level": node.level,
                        "parent_title": node.parent_title,
                    }
                    for node in parsed_path.nodes
                ],
            }
            for parsed_path in plan_result.paths
        ],
        "items": [
            {
                "title": item.title,
                "level": item.level,
                "parent_title": item.parent_title,
            }
            for item in plan_result.items
        ],
        "structure": render_plan_structure(plan_result),
    }


@app.post("/api/v1/create")
def create(payload: CreateRequest) -> dict:
    """
    Создать страницы в Confluence по заданным путям.

    Для работы endpoint нужны корректные `config/app.yaml`
    и `secrets/confluence.yaml`, если `space_key` не передан явно.

    Args:
        payload: Данные для сценария создания страниц.

    Returns:
        JSON-совместимый результат сервисного слоя.
    """

    try:
        service, default_space_key = _load_service()
        result = service.create_pages(
            CreatePagesRequest(
                paths=payload.paths,
                space_key=payload.space_key,
                content=payload.content,
                dry_run=False,
            ),
            default_space_key=default_space_key,
        )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.get("/api/v1/config")
def show_config() -> Dict[str, Union[str, None, bool]]:
    """
    Показать, какой конфиг будет использоваться локальным API.

    Returns:
        Информация о путях и основных параметрах подключения.
    """

    config_path = resolve_config_path()
    secrets_path = resolve_secrets_path()
    try:
        config = load_app_config(config_path)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "config_path": str(config_path),
        "secrets_path": str(secrets_path),
        "base_url": config.confluence.base_url,
        "verify_ssl": config.confluence.verify_ssl,
        "default_space_key": config.confluence.default_space_key,
    }


@app.get("/api/v1/client/me")
def client_me() -> dict:
    """
    Проверить авторизацию и получить текущего пользователя Confluence.

    Returns:
        Данные текущего пользователя из Confluence Cloud.
    """

    try:
        with _load_client() as client:
            user = client.current_user()
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return user.model_dump(mode="json")


@app.get("/api/v1/client/space/{space_key}")
def client_space(space_key: str) -> dict:
    """
    Получить информацию о пространстве Confluence.

    Args:
        space_key: Ключ пространства.

    Returns:
        Данные пространства и его домашней страницы.
    """

    try:
        with _load_client() as client:
            space = client.get_space(space_key)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return space.model_dump(mode="json")


@app.get("/api/v1/client/page/search")
def client_page_search(title: str, space_key: Optional[str] = None) -> dict:
    """
    Найти страницы по заголовку в пространстве.

    Args:
        title: Заголовок страницы.
        space_key: Ключ пространства. Если не передан, берется из конфига.

    Returns:
        Список найденных страниц.
    """

    try:
        config = load_app_config(resolve_config_path())
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    effective_space_key = space_key or config.confluence.default_space_key
    if not effective_space_key:
        raise HTTPException(status_code=400, detail="Не указан space_key и в конфиге нет значения по умолчанию.")

    try:
        with _load_client() as client:
            pages = client.find_page(title=title, space_key=effective_space_key)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return pages.model_dump(mode="json")


@app.get("/api/v1/page/{page_id}/markdown")
def export_page_markdown(page_id: str) -> dict:
    """
    Выгрузить страницу Confluence в Markdown.

    Args:
        page_id: Идентификатор страницы Confluence.

    Returns:
        Заголовок страницы, markdown-представление и предупреждения о потерях.
    """

    try:
        with _load_client() as client:
            exporter = ConfluenceMarkdownExporter(client)
            result = exporter.export_page_to_markdown(page_id)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/{page_id}/markdown/file")
def export_page_markdown_to_file(page_id: str, payload: MarkdownFileExportRequest) -> dict:
    """
    Выгрузить страницу Confluence сразу в Markdown-файл на диске.
    """

    try:
        with _load_client() as client:
            result = export_page_to_markdown_file(
                client=client,
                page_id=page_id,
                output_path=payload.output_path,
            )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/preview")
def preview_markdown(payload: MarkdownPreviewRequest) -> dict:
    """
    Предварительно преобразовать Markdown в Confluence storage format.
    """

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.preview_markdown_to_storage(payload.markdown)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/preview-file")
def preview_markdown_file(payload: MarkdownFilePreviewRequest) -> dict:
    """
    Предварительно преобразовать Markdown-файл в Confluence storage format.
    """

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.preview_markdown_file_to_storage(payload.file_path)
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/create")
def create_page_from_markdown(payload: MarkdownCreateRequest) -> dict:
    """
    Создать страницу Confluence из Markdown.
    """

    try:
        config = load_app_config(resolve_config_path())
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    effective_space_key = payload.space_key or config.confluence.default_space_key
    if not effective_space_key:
        raise HTTPException(status_code=400, detail="Не указан space_key и в конфиге нет значения по умолчанию.")

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.create_page_from_markdown(
                title=payload.title,
                markdown_text=payload.markdown,
                parent_id=payload.parent_id,
                space_key=effective_space_key,
            )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/create-file")
def create_page_from_markdown_file(payload: MarkdownFileCreateRequest) -> dict:
    """
    Создать страницу Confluence из markdown-файла.
    """

    try:
        config = load_app_config(resolve_config_path())
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    effective_space_key = payload.space_key or config.confluence.default_space_key
    if not effective_space_key:
        raise HTTPException(status_code=400, detail="Не указан space_key и в конфиге нет значения по умолчанию.")

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.create_page_from_markdown_file(
                title=payload.title,
                file_path=payload.file_path,
                parent_id=payload.parent_id,
                space_key=effective_space_key,
            )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/update")
def update_page_from_markdown(payload: MarkdownUpdateRequest) -> dict:
    """
    Обновить существующую страницу Confluence содержимым из Markdown.
    """

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.update_page_from_markdown(
                page_id=payload.page_id,
                markdown_text=payload.markdown,
                title=payload.title,
            )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


@app.post("/api/v1/page/markdown/update-file")
def update_page_from_markdown_file(payload: MarkdownFileUpdateRequest) -> dict:
    """
    Обновить существующую страницу Confluence содержимым из markdown-файла.
    """

    try:
        with _load_client() as client:
            importer = ConfluenceMarkdownImporter(client)
            result = importer.update_page_from_markdown_file(
                page_id=payload.page_id,
                file_path=payload.file_path,
                title=payload.title,
            )
    except (ConfigFileNotFoundError, SecretsFileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except (InvalidConfigError, InvalidSecretsError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except MarkdownBridgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result.model_dump(mode="json")


def _load_service() -> Tuple[PageCreatorService, Optional[str]]:
    return load_runtime_service()


def _load_client():
    client, _ = load_runtime_client()
    return client
