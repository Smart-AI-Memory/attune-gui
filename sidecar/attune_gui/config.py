"""Typed config loader for attune-gui.

Single source of truth for keys that used to live across
``~/.attune-gui/config.json`` and ad-hoc environment variables. Adds an
``attune-gui config`` CLI on top so users don't have to hand-edit JSON.

Precedence (highest first):

1. Environment variable (e.g. ``ATTUNE_WORKSPACE``) — useful for CI and
   one-off runs.
2. ``~/.attune-gui/config.json`` — the persisted source of truth.
3. Built-in default — ``None`` for every key right now; the consumer
   decides what "unset" means.

Storage stays as JSON, not TOML. Adding TOML for a file with three keys
would mean a new write-side dependency (``tomli-w``) for no real win.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".attune-gui" / "config.json"

ConfigKey = Literal["workspace", "corpora_registry", "specs_root"]

_KEYS: tuple[ConfigKey, ...] = ("workspace", "corpora_registry", "specs_root")

_ENV_VARS: dict[ConfigKey, str] = {
    "workspace": "ATTUNE_WORKSPACE",
    "corpora_registry": "ATTUNE_CORPORA_REGISTRY",
    "specs_root": "ATTUNE_SPECS_ROOT",
}

_DEFAULTS: dict[ConfigKey, str | None] = {
    "workspace": None,
    "corpora_registry": None,  # consumer falls back to ~/.attune/corpora.json
    "specs_root": None,  # consumer walks up from cwd
}

KeySource = Literal["env", "file", "default"]


@dataclass(frozen=True)
class Config:
    """Resolved config snapshot. Values are post-precedence."""

    workspace: str | None
    corpora_registry: str | None
    specs_root: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "workspace": self.workspace,
            "corpora_registry": self.corpora_registry,
            "specs_root": self.specs_root,
        }


def is_valid_key(key: str) -> bool:
    return key in _KEYS


def known_keys() -> tuple[ConfigKey, ...]:
    return _KEYS


def env_var_for(key: ConfigKey) -> str:
    return _ENV_VARS[key]


def _read_file() -> dict[str, object]:
    """Return the raw JSON config dict, or ``{}`` if missing/corrupt."""
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logger.warning("config file at %s unreadable: %s", CONFIG_PATH, exc)
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("config file at %s is corrupt (%s); ignoring", CONFIG_PATH, exc)
        return {}
    if not isinstance(data, dict):
        logger.warning("config file at %s has unexpected shape; ignoring", CONFIG_PATH)
        return {}
    return data


def _write_file(data: dict[str, object]) -> None:
    """Atomically write the config dict to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".config.",
        suffix=".json.tmp",
        dir=str(CONFIG_PATH.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get(key: ConfigKey) -> str | None:
    """Return the resolved value for ``key``, applying env > file > default."""
    env_val = os.environ.get(_ENV_VARS[key], "").strip()
    if env_val:
        return env_val
    file_data = _read_file()
    file_val = file_data.get(key)
    if isinstance(file_val, str) and file_val.strip():
        return file_val
    return _DEFAULTS[key]


def get_source(key: ConfigKey) -> KeySource:
    """Tell the user where the resolved value came from. Used by ``config --list``."""
    if os.environ.get(_ENV_VARS[key], "").strip():
        return "env"
    file_data = _read_file()
    file_val = file_data.get(key)
    if isinstance(file_val, str) and file_val.strip():
        return "file"
    return "default"


def load() -> Config:
    """Resolve all keys at once."""
    return Config(
        workspace=get("workspace"),
        corpora_registry=get("corpora_registry"),
        specs_root=get("specs_root"),
    )


def set_value(key: ConfigKey, value: str) -> None:
    """Persist ``value`` to the config file. Does not validate semantics
    (e.g. directory existence) — that's the consumer's job. ``workspace``
    keeps its dir-must-exist guard via :func:`set_workspace`."""
    if key not in _KEYS:
        raise ValueError(f"unknown config key: {key!r}")
    data = _read_file()
    data[key] = value
    _write_file(data)


def unset_value(key: ConfigKey) -> bool:
    """Remove ``key`` from the config file. Returns True if it was present."""
    if key not in _KEYS:
        raise ValueError(f"unknown config key: {key!r}")
    data = _read_file()
    if key in data:
        del data[key]
        _write_file(data)
        return True
    return False
