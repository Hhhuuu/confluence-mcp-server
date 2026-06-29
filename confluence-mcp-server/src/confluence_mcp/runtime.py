"""Общие функции загрузки runtime-зависимостей для HTTP API и MCP."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from confluence_client import ConfluenceClient, ConfluenceClientConfig
from confluence_pagecreator_service import (
    PageCreatorService,
    load_app_config,
    load_secrets,
)

from .server import build_service

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "app.yaml"
_DEFAULT_SECRETS_PATH = Path(__file__).resolve().parents[3] / "secrets" / "confluence.yaml"


def resolve_config_path() -> Path:
    """
    Определить путь до прикладного конфига.

    Returns:
        Абсолютный путь до `app.yaml`.
    """

    return Path(os.getenv("PAGECREATOR_CONFIG_PATH", str(_DEFAULT_CONFIG_PATH))).expanduser()


def resolve_secrets_path() -> Path:
    """
    Определить путь до файла с секретами.

    Returns:
        Абсолютный путь до `confluence.yaml`.
    """

    return Path(os.getenv("PAGECREATOR_SECRETS_PATH", str(_DEFAULT_SECRETS_PATH))).expanduser()


def load_runtime_service() -> Tuple[PageCreatorService, Optional[str]]:
    """
    Загрузить сервисный слой и значение пространства по умолчанию.

    Returns:
        Кортеж из `PageCreatorService` и `default_space_key`.
    """

    config_path = resolve_config_path()
    secrets_path = resolve_secrets_path()
    config = load_app_config(config_path)
    service = build_service(str(config_path), str(secrets_path))
    return service, config.confluence.default_space_key


def load_runtime_client() -> Tuple[ConfluenceClient, Optional[str]]:
    """
    Загрузить клиент Confluence и значение пространства по умолчанию.

    Returns:
        Кортеж из `ConfluenceClient` и `default_space_key`.
    """

    config_path = resolve_config_path()
    secrets_path = resolve_secrets_path()
    config = load_app_config(config_path)
    secrets = load_secrets(secrets_path).confluence
    client = ConfluenceClient(
        ConfluenceClientConfig(
            base_url=config.confluence.base_url,
            deployment=config.confluence.deployment,
            auth_type=secrets.auth_type,
            username=secrets.username,
            password=secrets.password,
            api_token=secrets.api_token,
            verify_ssl=config.confluence.verify_ssl,
        )
    )
    return client, config.confluence.default_space_key
