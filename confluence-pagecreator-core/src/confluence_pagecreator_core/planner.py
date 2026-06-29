"""Вспомогательные функции для построения плана по дереву страниц."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from .models import CreationPlan, CreationPlanItem, LevelNode, ParsedPath


def build_level_index(paths: Iterable[ParsedPath]) -> "OrderedDict[int, list[LevelNode]]":
    """
    Сгруппировать узлы по уровням, сохранив порядок первого появления.

    В пределах одного уровня одинаковые узлы повторно не добавляются.
    Это повторяет идею Java-реализации, где элементы уровня
    собираются в структуру без дублей с сохранением порядка.

    Args:
        paths: Последовательность уже разобранных путей.

    Returns:
        Упорядоченный словарь, где ключом выступает уровень,
        а значением список уникальных узлов этого уровня.
    """

    grouped: "OrderedDict[int, list[LevelNode]]" = OrderedDict()
    seen_per_level: dict[int, set[LevelNode]] = {}

    for parsed_path in paths:
        for node in parsed_path.nodes:
            grouped.setdefault(node.level, [])
            seen_per_level.setdefault(node.level, set())
            if node in seen_per_level[node.level]:
                continue
            grouped[node.level].append(node)
            seen_per_level[node.level].add(node)

    return grouped


def build_creation_plan(paths: Iterable[ParsedPath]) -> CreationPlan:
    """
    Построить плоский план обработки страниц из набора путей.

    План формируется по уровням: сначала корневые элементы, затем
    дочерние. Внутри уровня сохраняется порядок первого появления.

    Args:
        paths: Последовательность уже разобранных путей.

    Returns:
        Объект `CreationPlan`, пригодный для сервисного слоя.
    """

    normalized_paths = tuple(paths)
    level_index = build_level_index(normalized_paths)
    items: list[CreationPlanItem] = []

    for level in level_index:
        for node in level_index[level]:
            items.append(
                CreationPlanItem(
                    title=node.title,
                    level=node.level,
                    parent_title=node.parent_title,
                )
            )

    return CreationPlan(paths=normalized_paths, items=tuple(items))


def render_plan_structure(plan: CreationPlan) -> str:
    """
    Построить текстовое представление плана страниц.

    Формат близок к выводу Java-плагина и подходит для логирования
    или режима предварительного просмотра.

    Args:
        plan: План, построенный на основе набора путей.

    Returns:
        Строка с древовидным представлением структуры страниц.
    """

    tree: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for parsed_path in plan.paths:
        current_level = tree
        for node in parsed_path.nodes:
            current_level = current_level.setdefault(node.title, OrderedDict())

    lines: list[str] = []
    _render_tree(tree, lines=lines, level=0)
    return "\n".join(lines)


def _render_tree(
    tree: "OrderedDict[str, OrderedDict]",
    lines: list[str],
    level: int,
) -> None:
    for title, children in tree.items():
        prefix = "\t" * level
        if level == 0:
            lines.append(title)
        else:
            lines.append(f"{prefix}└─ {title}")
        _render_tree(children, lines=lines, level=level + 1)
