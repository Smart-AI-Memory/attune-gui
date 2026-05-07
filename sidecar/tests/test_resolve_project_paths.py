"""Tests for _resolve_project_paths path validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.commands import _resolve_project_paths


def test_absolute_project_path_resolves():
    home = str(Path.home())
    root, help_dir = _resolve_project_paths({"project_path": home})
    assert root == Path(home).resolve()
    assert help_dir == Path(home).resolve() / ".help"


def test_tilde_project_path_expands():
    root, help_dir = _resolve_project_paths({"project_path": "~"})
    assert root == Path.home().resolve()
    assert help_dir == Path.home().resolve() / ".help"


def test_relative_project_path_rejected():
    with pytest.raises(ValueError, match="must be an absolute path"):
        _resolve_project_paths({"project_path": "Users/me/project"})


def test_dotted_relative_project_path_rejected():
    with pytest.raises(ValueError, match="must be an absolute path"):
        _resolve_project_paths({"project_path": "./project"})


def test_legacy_relative_project_root_rejected():
    with pytest.raises(ValueError, match="project_root must be an absolute path"):
        _resolve_project_paths({"project_root": "some/dir"})


def test_legacy_relative_help_dir_rejected():
    with pytest.raises(ValueError, match="help_dir must be an absolute path"):
        _resolve_project_paths(
            {"project_root": str(Path.home()), "help_dir": "rel/help"},
        )


def test_no_paths_uses_workspace(tmp_path, monkeypatch):
    """No project_path, no project_root, no help_dir → falls back to configured workspace."""
    monkeypatch.setattr("attune_gui.workspace.get_workspace", lambda: tmp_path)
    root, help_dir = _resolve_project_paths({})
    assert root == tmp_path
    assert help_dir == tmp_path / ".help"


def test_no_paths_no_workspace_raises(monkeypatch):
    """No paths and no workspace configured → clear error."""
    monkeypatch.setattr("attune_gui.workspace.get_workspace", lambda: None)
    with pytest.raises(ValueError, match="no workspace configured"):
        _resolve_project_paths({})


def test_explicit_project_root_skips_workspace(tmp_path, monkeypatch):
    """Explicit project_root / help_dir legacy args win over workspace."""
    monkeypatch.setattr("attune_gui.workspace.get_workspace", lambda: None)
    root, help_dir = _resolve_project_paths(
        {"project_root": str(tmp_path), "help_dir": str(tmp_path / ".help")}
    )
    assert root == tmp_path
    assert help_dir == tmp_path / ".help"


# -- features.yaml auto-promotion ------------------------------------


def test_help_dir_autopromotes_when_picker_landed_on_subdir(tmp_path):
    """If help_dir resolves to .help/templates but features.yaml is in
    .help, the resolver promotes to the parent.
    """
    help_root = tmp_path / ".help"
    help_root.mkdir()
    (help_root / "features.yaml").write_text("version: 1\nfeatures: {}\n")
    templates = help_root / "templates"
    templates.mkdir()

    root, help_dir = _resolve_project_paths(
        {"project_root": str(tmp_path), "help_dir": str(templates)}
    )
    assert root == tmp_path
    assert help_dir == help_root


def test_help_dir_unchanged_when_features_yaml_present(tmp_path):
    """If features.yaml is already in the chosen help_dir, no promotion."""
    help_root = tmp_path / ".help"
    help_root.mkdir()
    (help_root / "features.yaml").write_text("version: 1\nfeatures: {}\n")

    root, help_dir = _resolve_project_paths(
        {"project_root": str(tmp_path), "help_dir": str(help_root)}
    )
    assert help_dir == help_root


def test_help_dir_unchanged_when_neither_dir_has_manifest(tmp_path):
    """Walk only goes one level — if neither the chosen dir nor its
    parent has features.yaml, return the original path unchanged so the
    downstream loader produces the same FileNotFoundError as before.
    """
    help_root = tmp_path / ".help"
    templates = help_root / "templates"
    templates.mkdir(parents=True)

    root, help_dir = _resolve_project_paths(
        {"project_root": str(tmp_path), "help_dir": str(templates)}
    )
    assert help_dir == templates


def test_project_path_autopromotes_help_dir(tmp_path):
    """project_path convenience key also gets the auto-promotion check
    when .help itself is a stub (rare but possible if a layout lib
    rewrites the canonical name)."""
    # Here .help has no features.yaml; verify resolver still returns
    # .help unchanged because the parent (tmp_path) doesn't have one
    # either — i.e. we don't accidentally promote past the help dir.
    (tmp_path / ".help").mkdir()
    root, help_dir = _resolve_project_paths({"project_path": str(tmp_path)})
    assert help_dir == tmp_path / ".help"
