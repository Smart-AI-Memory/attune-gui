"""Tests for the .env loader in attune_gui.main."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.main import _load_dotenv


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip env vars the loader cares about so each test starts clean."""
    for key in ("ANTHROPIC_API_KEY", "ATTUNE_TEST_KEY", "ATTUNE_OTHER"):
        monkeypatch.delenv(key, raising=False)


def _patch_candidates(tmp_path: Path, files: list[str], monkeypatch: pytest.MonkeyPatch):
    """Make ``_load_dotenv`` look only at files inside ``tmp_path``."""
    candidates = [tmp_path / name for name in files]

    def fake_init(self):
        pass  # placeholder, unused

    monkeypatch.chdir(tmp_path)
    # Override candidate list by monkeypatching Path.home so ~/.attune* resolve under tmp_path
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    return candidates


def test_loads_simple_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY=secret123\n")

    import os

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "secret123"


def test_overwrites_empty_env_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty/whitespace-only existing values should be replaced."""
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    monkeypatch.setenv("ATTUNE_TEST_KEY", "")
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY=real-value\n")

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "real-value"


def test_does_not_overwrite_real_existing_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    monkeypatch.setenv("ATTUNE_TEST_KEY", "shell-value")
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY=env-file-value\n")

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "shell-value"


def test_export_prefix_supported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    (tmp_path / ".env").write_text("export ATTUNE_TEST_KEY=exported\n")

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "exported"


def test_quoted_values_unquoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    (tmp_path / ".env").write_text(
        'ATTUNE_TEST_KEY="double-quoted"\n' "ATTUNE_OTHER='single-quoted'\n"
    )

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "double-quoted"
    assert os.environ.get("ATTUNE_OTHER") == "single-quoted"


def test_comments_and_blank_lines_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    (tmp_path / ".env").write_text(
        "# this is a comment\n" "\n" "ATTUNE_TEST_KEY=value\n" "   \n" "# another comment\n"
    )

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "value"


def test_no_env_file_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    # No .env anywhere
    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") is None


def test_malformed_lines_silently_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lines without ``=`` are skipped rather than crashing the loader."""
    import os

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "_home"))
    (tmp_path / ".env").write_text("this-is-not-a-pair\n" "ATTUNE_TEST_KEY=ok\n")

    _load_dotenv()
    assert os.environ.get("ATTUNE_TEST_KEY") == "ok"
