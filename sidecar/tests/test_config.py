"""Tests for attune_gui.config — typed loader + env precedence + CLI plumbing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune_gui import config
from attune_gui.main import _build_parser, _config_command


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / ".attune-gui" / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", cfg)
    monkeypatch.delenv("ATTUNE_WORKSPACE", raising=False)
    monkeypatch.delenv("ATTUNE_CORPORA_REGISTRY", raising=False)
    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    return cfg


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_default_when_nothing_set(self, isolated: Path) -> None:
        assert config.get("specs_root") is None
        assert config.get_source("specs_root") == "default"

    def test_file_overrides_default(self, isolated: Path, tmp_path: Path) -> None:
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text(json.dumps({"specs_root": str(tmp_path)}))
        assert config.get("specs_root") == str(tmp_path)
        assert config.get_source("specs_root") == "file"

    def test_env_overrides_file(
        self, isolated: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text(json.dumps({"specs_root": "/from-file"}))
        monkeypatch.setenv("ATTUNE_SPECS_ROOT", "/from-env")
        assert config.get("specs_root") == "/from-env"
        assert config.get_source("specs_root") == "env"

    def test_empty_env_var_is_ignored(
        self, isolated: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A whitespace-only env value should not shadow the file value."""
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text(json.dumps({"specs_root": "/from-file"}))
        monkeypatch.setenv("ATTUNE_SPECS_ROOT", "  ")
        assert config.get("specs_root") == "/from-file"


# ---------------------------------------------------------------------------
# File handling
# ---------------------------------------------------------------------------


class TestFileHandling:
    def test_corrupt_file_treated_as_empty(self, isolated: Path, caplog) -> None:
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text("not json {")
        with caplog.at_level("WARNING"):
            assert config.get("workspace") is None
        assert any("corrupt" in r.message for r in caplog.records)

    def test_unexpected_shape_treated_as_empty(self, isolated: Path) -> None:
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text("[]")
        assert config.get("workspace") is None

    def test_set_value_writes_atomically(self, isolated: Path) -> None:
        config.set_value("corpora_registry", "/x/y/corpora.json")
        data = json.loads(isolated.read_text())
        assert data["corpora_registry"] == "/x/y/corpora.json"

    def test_set_value_preserves_other_keys(self, isolated: Path) -> None:
        isolated.parent.mkdir(parents=True, exist_ok=True)
        isolated.write_text(json.dumps({"workspace": "/a", "profile": "x"}))
        config.set_value("corpora_registry", "/b/corpora.json")
        data = json.loads(isolated.read_text())
        assert data["workspace"] == "/a"
        assert data["profile"] == "x"
        assert data["corpora_registry"] == "/b/corpora.json"

    def test_set_value_rejects_unknown_key(self, isolated: Path) -> None:
        with pytest.raises(ValueError, match="unknown config key"):
            config.set_value("not_a_key", "x")  # type: ignore[arg-type]

    def test_unset_removes_key(self, isolated: Path) -> None:
        config.set_value("corpora_registry", "/x")
        assert config.unset_value("corpora_registry") is True
        assert config.get("corpora_registry") is None

    def test_unset_returns_false_when_absent(self, isolated: Path) -> None:
        assert config.unset_value("corpora_registry") is False


# ---------------------------------------------------------------------------
# CLI subcommand
# ---------------------------------------------------------------------------


class TestConfigCli:
    def test_list_prints_all_keys(self, isolated: Path, capsys) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "list"]))
        out = capsys.readouterr().out
        assert rc == 0
        assert "workspace" in out
        assert "corpora_registry" in out
        assert "specs_root" in out
        assert "<unset>" in out  # nothing configured yet

    def test_get_prints_value(self, isolated: Path, capsys) -> None:
        config.set_value("corpora_registry", "/x/corpora.json")
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "get", "corpora_registry"]))
        out = capsys.readouterr().out
        assert rc == 0
        assert out.strip() == "/x/corpora.json"

    def test_get_returns_1_when_unset(self, isolated: Path) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "get", "corpora_registry"]))
        assert rc == 1

    def test_get_rejects_unknown_key(self, isolated: Path) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "get", "nope"]))
        assert rc == 2

    def test_set_persists(self, isolated: Path) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "set", "specs_root", "/some/specs"]))
        assert rc == 0
        assert config.get("specs_root") == "/some/specs"

    def test_set_workspace_validates_directory(self, isolated: Path, tmp_path: Path) -> None:
        parser = _build_parser()
        rc = _config_command(
            parser.parse_args(["config", "set", "workspace", str(tmp_path / "nope")])
        )
        assert rc == 1  # ValueError surfaced

    def test_set_workspace_succeeds_for_real_dir(self, isolated: Path, tmp_path: Path) -> None:
        target = tmp_path / "ws"
        target.mkdir()
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "set", "workspace", str(target)]))
        assert rc == 0
        assert config.get("workspace") == str(target.resolve())

    def test_unset_removes(self, isolated: Path) -> None:
        config.set_value("specs_root", "/x")
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "unset", "specs_root"]))
        assert rc == 0
        assert config.get("specs_root") is None

    def test_set_rejects_unknown_key(self, isolated: Path, capsys) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "set", "nope", "value"]))
        err = capsys.readouterr().err
        assert rc == 2
        assert "unknown key" in err

    def test_unset_rejects_unknown_key(self, isolated: Path, capsys) -> None:
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "unset", "nope"]))
        err = capsys.readouterr().err
        assert rc == 2
        assert "unknown key" in err

    def test_unset_returns_0_when_key_absent(self, isolated: Path, capsys) -> None:
        """unset on a key that was never set still exits cleanly with rc=0."""
        parser = _build_parser()
        rc = _config_command(parser.parse_args(["config", "unset", "specs_root"]))
        out = capsys.readouterr().out
        assert rc == 0
        assert "was not set" in out

    def test_set_workspace_invalid_path_prints_to_stderr(
        self, isolated: Path, tmp_path: Path, capsys
    ) -> None:
        parser = _build_parser()
        rc = _config_command(
            parser.parse_args(["config", "set", "workspace", str(tmp_path / "nope")])
        )
        err = capsys.readouterr().err
        assert rc == 1
        assert "Not a directory" in err
