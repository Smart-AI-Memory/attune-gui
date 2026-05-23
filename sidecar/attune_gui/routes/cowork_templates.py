"""Template listing for the Cowork dashboard.

GET /api/cowork/templates
    Response: {
        "templates": [
            {path, tags, summary, staleness, last_modified, manual}, ...
        ],
        "templates_root": str | null,
    }

Staleness is the semantic-hash verdict from
:mod:`attune_gui.services.staleness_cache` — one of
``fresh`` / ``stale`` / ``manual`` / ``unknown``. The field
answers "would ``author.maintain`` regenerate this file?" so the
dashboard agrees with the Commands page. ``last_modified`` stays
as informational metadata only — no longer drives the badge.

Manual flag is read from YAML frontmatter (``status: manual``, the
key attune-author honours; legacy ``manual: true`` files still read
true for the badge but get migrated on the next pin write).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
from fastapi import APIRouter

from attune_gui.services import staleness_cache
from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork", tags=["cowork-templates"])


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
    """List `.help/templates/*.md` for the active workspace.

    Each template's ``staleness`` field reflects the
    semantic-hash verdict from ``attune-author``, looked up via
    :mod:`attune_gui.services.staleness_cache`. ``last_modified``
    remains as informational metadata only.
    """
    root = _templates_root()
    if root is None:
        return {"templates": [], "templates_root": None}

    workspace = get_workspace()
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
        except OSError:
            last_modified = None

        stale = (
            staleness_cache.get_template_staleness(workspace, path)
            if workspace is not None
            else "unknown"
        )

        items.append(
            {
                "path": str(rel),
                "tags": list(meta.get("tags") or []),
                "summary": meta.get("summary") or "",
                "type": meta.get("type") or "",
                "staleness": stale,
                "last_modified": last_modified,
                "manual": meta.get("status") == "manual" or bool(meta.get("manual")),
            }
        )

    return {"templates": items, "templates_root": str(root)}
