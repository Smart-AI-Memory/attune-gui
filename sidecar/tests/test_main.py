"""Tests for sidecar/attune_gui/main.py — argparse, dotenv, port selection.

Avoids exercising ``main()`` directly because it would start a real uvicorn
server. Instead, we test the parsing and helper functions that are
deterministic and side-effect-light.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from attune_gui.main import (
    _build_parser,
    _config_command,
    _load_dotenv,
    _pick_free_port,
)

# ---------------------------------------------------------------------------
# _pick_free_port
# ---------------------------------------------------------------------------


def test_pick_free_port_returns_int_in_user_range() -> None:
    port = _pick_free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535


# ---------------------------------------------------------------------------
# argparse construction
# ---------------------------------------------------------------------------


def test_parser_defaults_to_no_command_and_auto_port() -> None:
    args = _build_parser().parse_args([])
    assert args.command is None
    assert args.port is None
    assert args.open is False
    assert args.reload is False
    assert args.log_level == "info"


def test_parser_accepts_explicit_port_and_flags() -> None:
    args = _build_parser().parse_args(["--port", "9999", "--open", "--reload"])
    assert args.port == 9999
    assert args.open is True
    assert args.reload is True


def test_parser_rejects_invalid_log_level() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["--log-level", "verbose"])


def test_parser_config_subcommand_has_required_action() -> None:
    """``attune-gui config`` without an action must error."""
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["config"])


def test_parser_config_get_requires_key() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["config", "get"])


def test_parser_config_list_parses_cleanly() -> None:
    args = _build_parser().parse_args(["config", "list"])
    assert args.command == "config"
    assert args.config_action == "list"


def test_parser_config_set_captures_key_value() -> None:
    args = _build_parser().parse_args(["config", "set", "workspace", "./fake-workspace"])
    assert args.config_action == "set"
    assert args.key == "workspace"
    assert args.value == "./fake-workspace"


# ---------------------------------------------------------------------------
# _load_dotenv
# ---------------------------------------------------------------------------


def test_load_dotenv_reads_cwd_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY_A=alpha\n")
    monkeypatch.delenv("ATTUNE_TEST_KEY_A", raising=False)
    _load_dotenv()
    assert os.environ["ATTUNE_TEST_KEY_A"] == "alpha"


def test_load_dotenv_skips_comments_and_blank_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "# header comment\n"
        "\n"
        "ATTUNE_TEST_KEY_B=beta\n"
        "  # indented comment\n"
        "MALFORMED_NO_EQUALS_SIGN\n"
    )
    monkeypatch.delenv("ATTUNE_TEST_KEY_B", raising=False)
    _load_dotenv()
    assert os.environ["ATTUNE_TEST_KEY_B"] == "beta"


def test_load_dotenv_strips_export_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('export ATTUNE_TEST_KEY_C="gamma"\n')
    monkeypatch.delenv("ATTUNE_TEST_KEY_C", raising=False)
    _load_dotenv()
    assert os.environ["ATTUNE_TEST_KEY_C"] == "gamma"


def test_load_dotenv_does_not_overwrite_real_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY_D=fromfile\n")
    monkeypatch.setenv("ATTUNE_TEST_KEY_D", "fromenv")
    _load_dotenv()
    assert os.environ["ATTUNE_TEST_KEY_D"] == "fromenv"


def test_load_dotenv_treats_empty_env_var_as_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A whitespace-only env var should be overwritten by a real .env value."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ATTUNE_TEST_KEY_E=loaded\n")
    monkeypatch.setenv("ATTUNE_TEST_KEY_E", "   ")
    _load_dotenv()
    assert os.environ["ATTUNE_TEST_KEY_E"] == "loaded"


# ---------------------------------------------------------------------------
# _config_command — exit codes
# ---------------------------------------------------------------------------


def _ns(**kwargs: Any) -> Any:
    """Build an argparse-Namespace-shaped object for _config_command."""
    import argparse

    return argparse.Namespace(**kwargs)


def test_config_command_get_unknown_key_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = _config_command(_ns(config_action="get", key="not_a_real_key"))
    assert rc == 2
    err = capsys.readouterr().err
    assert "not_a_real_key" in err


def test_config_command_set_unknown_key_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = _config_command(_ns(config_action="set", key="bogus_key", value="x"))
    assert rc == 2


def test_config_command_unset_unknown_key_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = _config_command(_ns(config_action="unset", key="bogus_key"))
    assert rc == 2


def test_config_command_unknown_action_returns_2() -> None:
    rc = _config_command(_ns(config_action="totally-unknown"))
    assert rc == 2
