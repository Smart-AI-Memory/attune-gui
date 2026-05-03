"""Spec listing — scans the workspace ``specs/`` directory.

GET /api/cowork/specs
    Response: {"specs": [{feature, files, phase, status}, ...]}

Phase is inferred from which spec files exist (requirements/design/tasks).
Status is read from the most-advanced file's ``**Status**:`` line.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork", tags=["cowork-specs"])

_STATUS_RE = re.compile(r"\*\*Status\*\*:\s*(\S+)")
_PHASE_FILES = ("requirements.md", "design.md", "tasks.md")
_PHASE_LABELS = {
    "requirements.md": "Requirements",
    "design.md": "Design",
    "tasks.md": "Tasks",
}


def _read_status(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _STATUS_RE.search(text)
    return m.group(1).strip() if m else None


def _scan_feature(feat_dir: Path) -> dict[str, Any]:
    present = [name for name in _PHASE_FILES if (feat_dir / name).is_file()]
    if not present:
        return {
            "feature": feat_dir.name,
            "files": [],
            "phase": None,
            "phase_label": None,
            "status": None,
        }

    most_advanced = present[-1]  # _PHASE_FILES is in order
    status = _read_status(feat_dir / most_advanced)

    return {
        "feature": feat_dir.name,
        "files": present,
        "phase": most_advanced,
        "phase_label": _PHASE_LABELS[most_advanced],
        "status": status,
    }


def _specs_root() -> Path | None:
    """Find the workspace ``specs/`` directory.

    Search order:
      1. ``ATTUNE_SPECS_ROOT`` env var (if set and a real dir)
      2. ``<workspace>/specs/``
      3. ``<workspace>/.help/specs/``
      4. ``Path.cwd() / "specs"``
      5. Walk up from cwd looking for the first ``specs/`` dir
    """
    import os

    env = os.environ.get("ATTUNE_SPECS_ROOT")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p

    ws = get_workspace()
    candidates: list[Path] = []
    if ws is not None:
        candidates.extend([ws / "specs", ws / ".help" / "specs"])
    candidates.append(Path.cwd() / "specs")

    for c in candidates:
        if c.is_dir():
            return c

    # Walk up from cwd
    cur = Path.cwd().resolve()
    for _ in range(8):  # cap depth so we don't crawl forever
        candidate = cur / "specs"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


@router.get("/specs")
async def list_specs() -> dict[str, Any]:
    """Return a list of feature specs found under the workspace specs root."""
    root = _specs_root()
    if root is None:
        return {"specs": [], "specs_root": None}

    specs = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        # Skip dot-dirs like .git
        if child.name.startswith("."):
            continue
        specs.append(_scan_feature(child))

    return {"specs": specs, "specs_root": str(root)}
