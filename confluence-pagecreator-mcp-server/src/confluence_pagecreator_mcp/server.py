"""Каркас MCP-сервера для создания страниц."""

from __future__ import annotations

from confluence_pagecreator_service import (
    PageCreatorService,
    load_app_config,
    load_secrets,
)

from .tools import create_pages, plan_pages


def build_service(
    config_path: str,
    secrets_path: str,
) -> PageCreatorService:
    """
    Собрать сервис создания страниц из конфигурации и секретов.

    Args:
        config_path: Путь до прикладного конфига.
        secrets_path: Путь до файла с секретами.

    Returns:
        Готовый экземпляр `PageCreatorService`.
    """

    app_config = load_app_config(config_path)
    secrets = load_secrets(secrets_path).confluence
    return PageCreatorService.from_config(app_config, secrets)


def build_toolset(
    config_path: str,
    secrets_path: str,
) -> dict[str, object]:
    """
    Собрать набор функций, который позже будет зарегистрирован как MCP tools.

    Сейчас это транспортный каркас без привязки к конкретной MCP-библиотеке.

    Args:
        config_path: Путь до прикладного конфига.
        secrets_path: Путь до файла с секретами.

    Returns:
        Словарь с функциями-инструментами.
    """

    service = build_service(config_path, secrets_path)
    app_config = load_app_config(config_path)
    default_space_key = app_config.confluence.default_space_key

    return {
        "plan_pages": lambda paths, space_key=None: plan_pages(
            service=service,
            paths=paths,
            space_key=space_key,
            default_space_key=default_space_key,
        ),
        "create_pages": lambda paths, space_key=None, content="": create_pages(
            service=service,
            paths=paths,
            space_key=space_key,
            default_space_key=default_space_key,
            content=content,
        ),
    }
