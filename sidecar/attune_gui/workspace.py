"""Shared workspace state for attune-gui.

Reads / writes ~/.attune-gui/config.json["workspace"].
"""

from __future__ import annotations

import json
from pathlib import Path

_CONFIG_PATH = Path.home() / ".attune-gui" / "config.json"


def get_workspace() -> Path | None:
    """Return the configured workspace path, or None if unset / invalid."""
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        ws = data.get("workspace", "")
        if ws:
            p = Path(ws).expanduser()
            if p.is_dir():
                return p
    except (OSError, json.JSONDecodeError):
        pass
    return None


def set_workspace(path: str) -> Path:
    """Persist a new workspace path. Raises ValueError if not a directory."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {resolved}")
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    data["workspace"] = str(resolved)
    _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return resolved
