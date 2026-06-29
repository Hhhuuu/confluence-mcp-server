from pagecreator_core.exceptions import DuplicateTitleError, InvalidPathError
from pagecreator_core.path_parser import parse_path, parse_paths
from pagecreator_core.planner import (
    build_creation_plan,
    build_level_index,
    render_plan_structure,
)


def test_parse_path_supports_escaped_slash() -> None:
    parsed = parse_path("Root/Team // Dev/Runbook")

    assert [node.title for node in parsed.nodes] == [
        "Root",
        "Team / Dev",
        "Runbook",
    ]


def test_parse_path_rejects_duplicates_within_one_path() -> None:
    try:
        parse_path("Root/Child/Root")
    except DuplicateTitleError:
        pass
    else:
        raise AssertionError("DuplicateTitleError was not raised")


def test_parse_paths_rejects_only_blank_input() -> None:
    try:
        parse_paths(["   ", ""])
    except InvalidPathError:
        pass
    else:
        raise AssertionError("InvalidPathError was not raised")


def test_build_level_index_preserves_order_and_deduplicates_by_level() -> None:
    parsed = parse_paths(["A/B/C", "A/B/D"])
    level_index = build_level_index(parsed)

    assert [node.title for node in level_index[0]] == ["A"]
    assert [node.title for node in level_index[1]] == ["B"]
    assert [node.title for node in level_index[2]] == ["C", "D"]


def test_build_creation_plan_returns_processing_order() -> None:
    parsed = parse_paths(["A/B/C", "A/B/D"])
    plan = build_creation_plan(parsed)

    assert [item.title for item in plan.items] == ["A", "B", "C", "D"]


def test_render_plan_structure_returns_tree() -> None:
    plan = build_creation_plan(parse_paths(["A/B/C"]))

    assert render_plan_structure(plan) == "A\n\t└─ B\n\t\t└─ C"


def test_render_plan_structure_merges_shared_branches() -> None:
    plan = build_creation_plan(parse_paths(["A/B/C", "A/B/D", "A/E"]))

    assert render_plan_structure(plan) == "A\n\t└─ B\n\t\t└─ C\n\t\t└─ D\n\t└─ E"
