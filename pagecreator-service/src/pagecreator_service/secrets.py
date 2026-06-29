"""Загрузка секретов для page creator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .exceptions import (
    InvalidSecretsError,
    SecretsFileNotFoundError,
)


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

    path = Path(secret_path).expanduser()
    if not path.exists():
        raise SecretsFileNotFoundError(path)
    if not path.is_file():
        raise InvalidSecretsError(f"Путь секретов не является файлом: {path}.")

    data = _read_yaml(path)
    try:
        secrets = SecretStore.model_validate(data)
    except ValidationError as exc:
        raise InvalidSecretsError(
            f"Некорректный формат secrets/confluence.yaml: {_format_validation_error(exc)}"
        ) from exc

    _validate_secrets(secrets.confluence)
    return secrets


def load_secrets_from_env() -> ConfluenceSecrets:
    """
    Загрузить секреты из переменных окружения.

    Returns:
        Объект `ConfluenceSecrets`.

    Raises:
        InvalidSecretsError: Если обязательные переменные окружения не заданы
            или задан неподдерживаемый тип авторизации.
    """

    auth_type = os.getenv("CONFLUENCE_AUTH_TYPE", "basic")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_PASSWORD")
    api_token = os.getenv("CONFLUENCE_API_TOKEN")

    if auth_type == "basic":
        if not username or not password:
            raise InvalidSecretsError(
                "Для basic auth через окружение нужны CONFLUENCE_USERNAME и CONFLUENCE_PASSWORD."
            )
        return ConfluenceSecrets(
            auth_type=auth_type,
            username=username,
            password=password,
        )

    if auth_type == "api_token":
        if not api_token:
            raise InvalidSecretsError(
                "Для api_token auth через окружение нужна CONFLUENCE_API_TOKEN."
            )
        return ConfluenceSecrets(
            auth_type=auth_type,
            username=username,
            api_token=api_token,
        )

    raise InvalidSecretsError("Поддерживаются только auth_type=basic и auth_type=api_token.")


def _read_yaml(secret_path: Union[str, Path]) -> dict[str, Any]:
    with Path(secret_path).expanduser().open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise InvalidSecretsError(
            "Файл secrets/confluence.yaml должен содержать YAML-объект верхнего уровня."
        )
    return data


def _validate_secrets(secrets: ConfluenceSecrets) -> None:
    auth_type = secrets.auth_type.strip().lower()
    secrets.auth_type = auth_type

    if auth_type == "basic":
        if not secrets.username or not secrets.password:
            raise InvalidSecretsError(
                "Для auth_type=basic в secrets/confluence.yaml нужны username и password."
            )
        return

    if auth_type == "api_token":
        if not secrets.api_token:
            raise InvalidSecretsError(
                "Для auth_type=api_token в secrets/confluence.yaml нужен api_token."
            )
        return

    raise InvalidSecretsError(
        "Поле confluence.auth_type должно быть равно 'basic' или 'api_token'."
    )


def _format_validation_error(error: ValidationError) -> str:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ()))
        error_type = item.get("type", "")

        if error_type == "missing" and location:
            messages.append(f"отсутствует обязательное поле {location}")
            continue

        detail = item.get("msg", "неизвестная ошибка валидации")
        if location:
            messages.append(f"{location}: {detail}")
        else:
            messages.append(detail)

    return "; ".join(messages)
