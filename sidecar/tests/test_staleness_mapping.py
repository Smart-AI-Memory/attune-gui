"""Table-driven tests for ``attune_gui.services.staleness_mapping``.

The mapping helper is the pure-function half of the staleness
plumbing: given per-feature verdicts from
``attune_author.staleness.check_staleness``, project the verdicts
onto every owned ``*.md`` template file. The cache layer is the
stateful half — tested separately in ``test_staleness_cache``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from attune_gui.services.staleness_mapping import project_verdicts


@dataclass
class _Fake:
    """Stand-in for ``attune_author.staleness.FeatureStaleness``.

    Only the two attributes ``project_verdicts`` reads (``feature``,
    ``is_stale``) need to be present.
    """

    feature: str
    is_stale: bool


def _make_template(workspace: Path, rel: str) -> Path:
    target = workspace / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("body\n", encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "is_stale,expected",
    [(False, "fresh"), (True, "stale")],
)
def test_single_feature_single_template(tmp_path: Path, is_stale: bool, expected: str) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    result = project_verdicts(tmp_path, [_Fake("auth", is_stale)])
    assert result == {Path(".help/templates/auth/concept.md"): expected}


def test_multiple_templates_in_one_feature(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    _make_template(tmp_path, ".help/templates/auth/reference.md")
    _make_template(tmp_path, ".help/templates/auth/task.md")

    result = project_verdicts(tmp_path, [_Fake("auth", True)])
    assert result == {
        Path(".help/templates/auth/concept.md"): "stale",
        Path(".help/templates/auth/reference.md"): "stale",
        Path(".help/templates/auth/task.md"): "stale",
    }


def test_multiple_features_independent_verdicts(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    _make_template(tmp_path, ".help/templates/cli/concept.md")

    result = project_verdicts(
        tmp_path,
        [_Fake("auth", False), _Fake("cli", True)],
    )
    assert result == {
        Path(".help/templates/auth/concept.md"): "fresh",
        Path(".help/templates/cli/concept.md"): "stale",
    }


def test_nested_subdir_under_feature_is_included(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/sub/nested.md")
    result = project_verdicts(tmp_path, [_Fake("auth", True)])
    assert Path(".help/templates/auth/sub/nested.md") in result


def test_non_md_files_in_feature_dir_ignored(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    (tmp_path / ".help/templates/auth/notes.txt").write_text("x", encoding="utf-8")
    (tmp_path / ".help/templates/auth/data.json").write_text("{}", encoding="utf-8")

    result = project_verdicts(tmp_path, [_Fake("auth", False)])
    assert list(result.keys()) == [Path(".help/templates/auth/concept.md")]


def test_feature_dir_missing_silently_skipped(tmp_path: Path) -> None:
    # auth has templates, ghost does not.
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    result = project_verdicts(
        tmp_path,
        [_Fake("auth", False), _Fake("ghost", True)],
    )
    assert result == {Path(".help/templates/auth/concept.md"): "fresh"}


def test_templates_root_missing_returns_empty(tmp_path: Path) -> None:
    # No .help/templates/ at all.
    result = project_verdicts(tmp_path, [_Fake("auth", True)])
    assert result == {}


def test_no_feature_entries_returns_empty(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    result = project_verdicts(tmp_path, [])
    assert result == {}


def test_file_outside_any_feature_dir_not_in_map(tmp_path: Path) -> None:
    """Top-level templates/glossary.md isn't owned by a feature."""
    _make_template(tmp_path, ".help/templates/glossary.md")
    _make_template(tmp_path, ".help/templates/auth/concept.md")

    result = project_verdicts(tmp_path, [_Fake("auth", True)])
    # glossary.md isn't projected — the cache layer treats absent → "manual".
    assert Path(".help/templates/glossary.md") not in result
    assert Path(".help/templates/auth/concept.md") in result


def test_returned_paths_are_relative_to_workspace(tmp_path: Path) -> None:
    _make_template(tmp_path, ".help/templates/auth/concept.md")
    result = project_verdicts(tmp_path, [_Fake("auth", False)])
    for key in result:
        assert not key.is_absolute()
