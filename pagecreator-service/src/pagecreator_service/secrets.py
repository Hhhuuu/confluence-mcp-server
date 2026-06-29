"""Загрузка секретов для page creator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict


class ConfluenceSecrets(BaseModel):
    """
    Секреты для подключения к Confluence.

    Attributes:
        auth_type: Тип авторизации: `basic` или `api_token`.
        username: Имя пользователя или email. Для token-only режима может отсутствовать.
        password: Пароль для basic auth.
        api_token: API token или personal access token.
    """

    model_config = ConfigDict(extra="ignore")

    auth_type: str = "basic"
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None


class SecretStore(BaseModel):
    """Корневой контейнер секретов."""

    model_config = ConfigDict(extra="ignore")

    confluence: ConfluenceSecrets


def load_secrets(secret_path: str | Path) -> SecretStore:
    """
    Загрузить секреты из YAML-файла.

    Args:
        secret_path: Путь до файла с секретами.

    Returns:
        Объект `SecretStore`.
    """

    data = _read_yaml(secret_path)
    return SecretStore.model_validate(data)


def load_secrets_from_env() -> ConfluenceSecrets:
    """
    Загрузить секреты из переменных окружения.

    Returns:
        Объект `ConfluenceSecrets`.

    Raises:
        ValueError: Если обязательные переменные окружения не заданы.
    """

    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "basic")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_PASSWORD")
    api_token = os.getenv("CONFLUENCE_API_TOKEN")

    if auth_type == "basic":
        if not username or not password:
            raise ValueError(
                "Для basic auth через окружение нужны CONFLUENCE_USERNAME и CONFLUENCE_PASSWORD."
            )
        return ConfluenceSecrets(
            auth_type=auth_type,
            username=username,
            password=password,
        )

    if auth_type == "api_token":
        if not api_token:
            raise ValueError(
                "Для api_token auth через окружение нужна CONFLUENCE_API_TOKEN."
            )
        return ConfluenceSecrets(
            auth_type=auth_type,
            username=username,
            api_token=api_token,
        )

    raise ValueError("Поддерживаются только auth_type=basic и auth_type=api_token.")


def _read_yaml(secret_path: Union[str, Path]) -> dict[str, Any]:
    with Path(secret_path).expanduser().open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}
