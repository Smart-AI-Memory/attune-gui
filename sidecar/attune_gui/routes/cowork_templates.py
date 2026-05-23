"""Template listing for the Cowork dashboard.

GET /api/cowork/templates
    Response: {
        "templates": [
            {path, tags, summary, staleness, last_modified, manual}, ...
        ],
        "templates_root": str | null,
    }

Staleness reflects **content drift** of the template's underlying source
files, not file mtime — the dashboard now agrees with
``attune-author status``. Values:

    - ``fresh``    — source hash matches; template is current.
    - ``stale``    — source hash drifted, or no stored hash recorded yet.
    - ``unknown``  — file is not under a feature managed by the manifest
      (no ``.help/features.yaml``, or template lives outside any
      ``<feature>/`` subdirectory).

``very-stale`` is no longer emitted (calendar-age model is retired);
consumers that branch on it remain harmless.

Manual flag is read from YAML frontmatter (``status: manual``, the
key attune-author honours; legacy ``manual: true`` files still read
true for the badge but get migrated on the next pin write).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter
from attune_author import check_workspace_staleness
from fastapi import APIRouter

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

    Each item gets a content-drift ``staleness`` value sourced from
    ``attune_author.check_workspace_staleness`` — same definition the
    ``attune-author status`` CLI uses. Templates whose feature isn't in
    the manifest (or workspaces without a manifest at all) report
    ``"unknown"``.
    """
    root = _templates_root()
    if root is None:
        return {"templates": [], "templates_root": None}

    ws = get_workspace()
    stale_features: set[str] = set()
    known_features: set[str] = set()
    if ws is not None:
        report = check_workspace_staleness(ws)
        stale_features = set(report.stale_features)
        known_features = {e.feature for e in report.help_entries}

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

        # Feature name is the first path component when the layout is
        # `<feature>/<kind>.md` (the canonical `.help/templates/` shape).
        # Anything flatter than that has no managed feature to compare
        # against.
        feature_name = rel.parts[0] if len(rel.parts) >= 2 else None
        if feature_name and feature_name in stale_features:
            stale = "stale"
        elif feature_name and feature_name in known_features:
            stale = "fresh"
        else:
            stale = "unknown"

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
