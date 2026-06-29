"""Ядро доменной логики создания страниц."""

from .exceptions import DuplicateTitleError, InvalidPathError
from .models import CreationPlan, CreationPlanItem, LevelNode, ParsedPath
from .path_parser import parse_path, parse_paths
from .planner import build_creation_plan, build_level_index, render_plan_structure

__all__ = [
    "CreationPlan",
    "CreationPlanItem",
    "DuplicateTitleError",
    "InvalidPathError",
    "LevelNode",
    "ParsedPath",
    "build_creation_plan",
    "build_level_index",
    "parse_path",
    "parse_paths",
    "render_plan_structure",
]
