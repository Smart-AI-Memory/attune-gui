"""Tests for _resolve_project_paths path validation."""

from __future__ import annotations

import os
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


def test_legacy_defaults_pass_through():
    """No project_path, no project_root, no help_dir → resolves to cwd-based defaults."""
    root, help_dir = _resolve_project_paths({})
    assert root == Path(os.getcwd()).resolve()
    assert help_dir == Path(os.getcwd()).resolve() / ".help"
