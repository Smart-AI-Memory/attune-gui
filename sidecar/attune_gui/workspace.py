"""Shared workspace state for attune-gui.

Thin wrapper over :mod:`attune_gui.config`. Kept as a separate module
because ``get_workspace()`` / ``set_workspace()`` have many callsites
and ``set_workspace()`` carries semantic validation (must be a real
directory) that the generic config setter doesn't.
"""

from __future__ import annotations

from pathlib import Path

from attune_gui import config


def get_workspace() -> Path | None:
    """Return the configured workspace path, or ``None`` if unset / invalid.

    Resolution order: ``ATTUNE_WORKSPACE`` env var > config file > unset.
    """
    raw = config.get("workspace")
    if not raw:
        return None
    try:
        p = Path(raw).expanduser()
    except (OSError, ValueError):
        return None
    if p.is_dir():
        return p
    return None


def set_workspace(path: str) -> Path:
    """Persist a new workspace path. Raises ``ValueError`` if not a directory."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {resolved}")
    config.set_value("workspace", str(resolved))
    return resolved
