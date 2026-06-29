"""Загрузка прикладного конфига для page creator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict


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

    data = _read_yaml(config_path)
    return AppConfig.model_validate(data)


def _read_yaml(config_path: str | Path) -> dict[str, Any]:
    with Path(config_path).expanduser().open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}
