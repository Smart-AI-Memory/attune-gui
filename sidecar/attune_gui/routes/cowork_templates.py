"""Template listing for the Cowork dashboard.

GET /api/cowork/templates
    Response: {
        "templates": [
            {path, tags, summary, staleness, last_modified, manual}, ...
        ],
        "templates_root": str | null,
    }

Staleness is mtime-based (fresh / stale / very-stale) with thresholds matching
the legacy attune-gui template browser:
    - fresh:      < 14 days old
    - stale:      14 ≤ age < 60 days
    - very-stale: ≥ 60 days

Manual flag is read from YAML frontmatter (``manual: true``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
from fastapi import APIRouter

from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork", tags=["cowork-templates"])

_FRESH_DAYS = 14
_STALE_DAYS = 60


def _staleness(mtime: float) -> str:
    age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400
    if age_days < _FRESH_DAYS:
        return "fresh"
    if age_days < _STALE_DAYS:
        return "stale"
    return "very-stale"


def _templates_root() -> Path | None:
    """Resolve a templates directory to scan.

    The workspace can be either:
      - a project root containing a ``.help/`` subdir, or
      - a directory that is itself the templates root (already inside ``.help``)

    Resolution order:
      1. ``<workspace>/.help/templates``
      2. ``<workspace>/.help``
      3. ``<workspace>`` itself (if it contains any ``*.md``)
    """
    ws = get_workspace()
    if ws is None:
        return None

    candidates = [
        ws / ".help" / "templates",
        ws / ".help",
        ws,
    ]
    for c in candidates:
        if c.is_dir() and any(c.rglob("*.md")):
            return c
    return None


@router.get("/templates")
async def list_templates() -> dict[str, Any]:
    """List `.help/templates/*.md` for the active workspace, with frontmatter and mtime."""
    root = _templates_root()
    if root is None:
        return {"templates": [], "templates_root": None}

    items: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        try:
            raw = path.read_text(encoding="utf-8")
            post = frontmatter.loads(raw)
            meta = post.metadata or {}
        except Exception:  # noqa: BLE001
            meta = {}

        try:
            mtime = path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            stale = _staleness(mtime)
        except OSError:
            last_modified = None
            stale = "unknown"

        items.append(
            {
                "path": str(rel),
                "tags": list(meta.get("tags") or []),
                "summary": meta.get("summary") or "",
                "type": meta.get("type") or "",
                "staleness": stale,
                "last_modified": last_modified,
                "manual": bool(meta.get("manual")),
            }
        )

    return {"templates": items, "templates_root": str(root)}
