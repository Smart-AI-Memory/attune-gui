"""Tests for attune_gui.workspace — config-backed workspace path persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune_gui import workspace


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point _CONFIG_PATH at a tmp file so tests don't touch the real home dir."""
    cfg = tmp_path / ".attune-gui" / "config.json"
    monkeypatch.setattr(workspace, "_CONFIG_PATH", cfg)
    return cfg


# ---------------------------------------------------------------------------
# get_workspace
# ---------------------------------------------------------------------------


class TestGetWorkspace:
    def test_returns_none_when_config_missing(self, isolated_config: Path) -> None:
        assert workspace.get_workspace() is None

    def test_returns_none_when_config_corrupt(self, isolated_config: Path) -> None:
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text("not json {")
        assert workspace.get_workspace() is None

    def test_returns_none_when_workspace_key_missing(self, isolated_config: Path) -> None:
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({"profile": "developer"}))
        assert workspace.get_workspace() is None

    def test_returns_none_when_workspace_path_is_not_a_directory(
        self, isolated_config: Path, tmp_path: Path
    ) -> None:
        bogus = tmp_path / "not-a-dir.txt"
        bogus.write_text("file")
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({"workspace": str(bogus)}))
        assert workspace.get_workspace() is None

    def test_returns_path_when_workspace_is_valid(
        self, isolated_config: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "project"
        target.mkdir()
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({"workspace": str(target)}))
        assert workspace.get_workspace() == target

    def test_expands_tilde_in_stored_path(
        self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A `~`-prefixed value should expand to the actual home dir."""
        monkeypatch.setenv("HOME", str(tmp_path))
        target = tmp_path / "ws"
        target.mkdir()
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({"workspace": "~/ws"}))
        assert workspace.get_workspace() == target


# ---------------------------------------------------------------------------
# set_workspace
# ---------------------------------------------------------------------------


class TestSetWorkspace:
    def test_persists_path_when_directory_exists(
        self, isolated_config: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "project"
        target.mkdir()
        result = workspace.set_workspace(str(target))
        assert result == target.resolve()
        # Round-trip via the config file
        data = json.loads(isolated_config.read_text())
        assert data["workspace"] == str(target.resolve())

    def test_raises_when_path_is_not_a_directory(
        self, isolated_config: Path, tmp_path: Path
    ) -> None:
        bogus = tmp_path / "missing"
        with pytest.raises(ValueError, match="Not a directory"):
            workspace.set_workspace(str(bogus))

    def test_raises_when_path_is_a_file(self, isolated_config: Path, tmp_path: Path) -> None:
        f = tmp_path / "regular-file"
        f.write_text("hi")
        with pytest.raises(ValueError, match="Not a directory"):
            workspace.set_workspace(str(f))

    def test_preserves_other_keys_in_config(self, isolated_config: Path, tmp_path: Path) -> None:
        """Setting workspace shouldn't clobber profile or other keys."""
        target = tmp_path / "project"
        target.mkdir()
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text(json.dumps({"profile": "author"}))

        workspace.set_workspace(str(target))

        data = json.loads(isolated_config.read_text())
        assert data["profile"] == "author"
        assert data["workspace"] == str(target.resolve())

    def test_replaces_corrupt_config_cleanly(self, isolated_config: Path, tmp_path: Path) -> None:
        """If existing config is corrupt JSON, overwrite with a fresh dict."""
        target = tmp_path / "project"
        target.mkdir()
        isolated_config.parent.mkdir(parents=True, exist_ok=True)
        isolated_config.write_text("garbage {{")

        workspace.set_workspace(str(target))

        data = json.loads(isolated_config.read_text())
        assert data == {"workspace": str(target.resolve())}

    def test_creates_config_directory_if_missing(
        self, isolated_config: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / "project"
        target.mkdir()
        # isolated_config.parent does not exist yet
        assert not isolated_config.parent.exists()

        workspace.set_workspace(str(target))

        assert isolated_config.parent.is_dir()
        assert isolated_config.is_file()
