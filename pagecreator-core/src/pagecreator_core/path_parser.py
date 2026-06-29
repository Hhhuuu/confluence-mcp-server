"""Утилиты для разбора путей создания страниц."""

from __future__ import annotations

import re
from typing import Iterable, Optional

from .exceptions import DuplicateTitleError, InvalidPathError
from .models import LevelNode, ParsedPath

_PATH_SPLIT_RE = re.compile(r"(?<!/)/(?!/)")


def parse_path(raw_path: str) -> ParsedPath:
    """
    Разобрать один путь в структуру узлов.

    Метод сохраняет текущее legacy-поведение Java-реализации:
    одинарный `/` разделяет уровни, а двойной `//` трактуется
    как обычный символ `/` внутри названия страницы.

    Args:
        raw_path: Исходный путь, например `Root/Child/Page`.

    Returns:
        Нормализованный объект `ParsedPath`.

    Raises:
        InvalidPathError: Если путь пустой или содержит пустые сегменты.
        DuplicateTitleError: Если в одном пути встречаются одинаковые названия.
    """

    if raw_path is None or not raw_path.strip():
        raise InvalidPathError("Путь не должен быть пустым.")

    raw_parts = _PATH_SPLIT_RE.split(raw_path)
    titles = [part.replace("//", "/").strip() for part in raw_parts if part.strip()]
    if not titles:
        raise InvalidPathError("Путь должен содержать хотя бы одно название страницы.")

    duplicates = _find_duplicates(titles)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise DuplicateTitleError(f"В пути найдены повторяющиеся названия: {duplicate_list}.")

    nodes: list[LevelNode] = []
    parent_title: Optional[str] = None
    for level, title in enumerate(titles):
        if not title:
            raise InvalidPathError("Путь содержит пустое название страницы.")
        nodes.append(LevelNode(title=title, level=level, parent_title=parent_title))
        parent_title = title

    return ParsedPath(raw_path=raw_path, nodes=tuple(nodes))


def parse_paths(raw_paths: Iterable[str]) -> list[ParsedPath]:
    """
    Разобрать несколько путей и вернуть список нормализованных структур.

    Пустые элементы входной последовательности пропускаются.
    Если после фильтрации не остается ни одного пути, метод
    завершится ошибкой.

    Args:
        raw_paths: Набор строковых путей.

    Returns:
        Список объектов `ParsedPath` в исходном порядке.

    Raises:
        InvalidPathError: Если после фильтрации не осталось ни одного пути.
        DuplicateTitleError: Если в одном из путей есть повторяющиеся названия.
    """

    parsed_paths: list[ParsedPath] = []
    for raw_path in raw_paths:
        if raw_path is None or not raw_path.strip():
            continue
        parsed_paths.append(parse_path(raw_path))

    if not parsed_paths:
        raise InvalidPathError("Нужно передать хотя бы один непустой путь.")

    return parsed_paths


def _find_duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
