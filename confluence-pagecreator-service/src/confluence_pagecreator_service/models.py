"""Доменные модели для разбора путей и построения плана страниц."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LevelNode:
    """
    Один узел страницы в разобранном пути.

    Attributes:
        title: Название страницы на текущем уровне.
        level: Уровень вложенности, начиная с `0`.
        parent_title: Название родительской страницы или `None`
            для корневого уровня.
    """

    title: str
    level: int
    parent_title: Optional[str] = None


@dataclass(frozen=True)
class ParsedPath:
    """
    Нормализованное представление одного пути.

    Attributes:
        raw_path: Исходная строка пути в том виде, в котором она была передана.
        nodes: Последовательность разобранных узлов пути.
    """

    raw_path: str
    nodes: tuple[LevelNode, ...]


@dataclass(frozen=True)
class CreationPlanItem:
    """
    Один элемент плана создания или поиска страницы.

    Attributes:
        title: Название страницы.
        level: Уровень вложенности, начиная с `0`.
        parent_title: Название родительской страницы или `None` для корня.
    """

    title: str
    level: int
    parent_title: Optional[str] = None


@dataclass(frozen=True)
class CreationPlan:
    """
    План обработки страниц, полученный из набора путей.

    Attributes:
        paths: Нормализованные пути, из которых был построен план.
        items: Плоский список элементов плана в порядке обработки.
    """

    paths: tuple[ParsedPath, ...]
    items: tuple[CreationPlanItem, ...]
