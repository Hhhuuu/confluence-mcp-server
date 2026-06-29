"""Загрузка прикладного конфига для page creator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError
from yaml import YAMLError

from .exceptions import ConfigFileNotFoundError, InvalidConfigError


class ConfluenceAppConfig(BaseModel):
    """
    Конфигурация подключения к Confluence.

    Attributes:
        base_url: Базовый URL Confluence.
        deployment: Тип развертывания: `cloud` или `server`.
        verify_ssl: Нужно ли проверять SSL-сертификат.
        default_space_key: Пространство по умолчанию.
    """

    model_config = ConfigDict(extra="ignore")

    base_url: str
    deployment: str = "cloud"
    verify_ssl: bool = True
    default_space_key: Optional[str] = None


class AppConfig(BaseModel):
    """Корневой конфиг приложения."""

    model_config = ConfigDict(extra="ignore")

    confluence: ConfluenceAppConfig


def load_app_config(config_path: str | Path) -> AppConfig:
    """
    Загрузить прикладной конфиг из YAML-файла.

    Args:
        config_path: Путь до файла конфигурации.

    Returns:
        Объект `AppConfig`.
    """

    path = Path(config_path).expanduser()
    if not path.exists():
        raise ConfigFileNotFoundError(path)
    if not path.is_file():
        raise InvalidConfigError(f"Путь конфигурации не является файлом: {path}.")

    data = _read_yaml(path)
    try:
        config = AppConfig.model_validate(data)
    except ValidationError as exc:
        raise InvalidConfigError(
            f"Некорректный формат config/app.yaml: {_format_validation_error(exc)}"
        ) from exc

    deployment = config.confluence.deployment.strip().lower()
    if deployment not in {"cloud", "server"}:
        raise InvalidConfigError(
            "Поле confluence.deployment должно быть равно 'cloud' или 'server'."
        )
    config.confluence.deployment = deployment
    return config


def _read_yaml(config_path: str | Path) -> dict[str, Any]:
    try:
        with Path(config_path).expanduser().open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except YAMLError as exc:
        raise InvalidConfigError(f"Файл config/app.yaml содержит некорректный YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise InvalidConfigError("Файл config/app.yaml должен содержать YAML-объект верхнего уровня.")
    return data


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
