"""Исключения для конфигурации и секретов сервисного слоя."""

from __future__ import annotations

from pathlib import Path


class PageCreatorServiceError(Exception):
    """Базовое исключение сервисного слоя."""


class ConfigFileNotFoundError(PageCreatorServiceError):
    """
    Ошибка отсутствующего файла конфигурации.

    Attributes:
        path: Путь до отсутствующего файла.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Не найден файл конфигурации: {path}. "
            f"Создайте его на основе config/app.yaml.example."
        )


class SecretsFileNotFoundError(PageCreatorServiceError):
    """
    Ошибка отсутствующего файла секретов.

    Attributes:
        path: Путь до отсутствующего файла.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(
            f"Не найден файл секретов: {path}. "
            f"Создайте его на основе secrets/confluence.yaml.example."
        )


class InvalidConfigError(PageCreatorServiceError):
    """Ошибка некорректного прикладного конфига."""


class InvalidSecretsError(PageCreatorServiceError):
    """Ошибка некорректных секретов подключения."""


class InvalidPathError(PageCreatorServiceError):
    """
    Ошибка пустого или некорректного пути страницы.

    Используется при разборе путей для сценария создания структуры.
    """


class DuplicateTitleError(PageCreatorServiceError):
    """
    Ошибка повторяющегося названия страницы внутри одного пути.

    Повтор названий внутри одного пути запрещен, чтобы план
    создания страниц был однозначным.
    """
