"""Filesystem helpers shared across routes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write(target: Path, text: str) -> float:
    """Write ``text`` to ``target`` atomically; return the new mtime.

    Uses ``tempfile.mkstemp`` in the target's directory + ``os.replace``
    so a concurrent reader either sees the old file or the new one,
    never a partial write. Cleans up the temp file if anything raises
    before the rename lands.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target.stat().st_mtime
