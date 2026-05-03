"""Cross-layer health probe.

GET /api/cowork/layers — versions + import status of rag/help/author/gui.
GET /api/cowork/corpus — corpus root + template count + summaries presence.

These probes never import the target packages — they use ``importlib.metadata``
so a missing optional dep never crashes the dashboard.
"""

from __future__ import annotations

import importlib.metadata as ilm
from typing import Any

from fastapi import APIRouter

from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork", tags=["cowork-health"])

_PACKAGES: tuple[tuple[str, str], ...] = (
    ("rag", "attune-rag"),
    ("help", "attune-help"),
    ("author", "attune-author"),
    ("gui", "attune-gui"),
)


def _probe(pkg: str) -> dict[str, Any]:
    try:
        return {"importable": True, "version": ilm.version(pkg)}
    except ilm.PackageNotFoundError:
        return {"importable": False, "version": None}


@router.get("/layers")
async def layer_health() -> dict[str, Any]:
    """Return version + importability for each attune layer."""
    return {"layers": {key: _probe(pkg) for key, pkg in _PACKAGES}}


@router.get("/corpus")
async def corpus_health() -> dict[str, Any]:
    """Return current workspace, template count, and summaries.json presence."""
    ws = get_workspace()
    if ws is None:
        return {
            "workspace": None,
            "template_count": 0,
            "summaries_present": False,
            "has_help_dir": False,
        }

    help_dir = ws / ".help"
    summaries = help_dir / "summaries.json"
    template_count = 0
    if help_dir.is_dir():
        # Count .md templates under .help/templates if it exists, else under .help
        templates_root = help_dir / "templates" if (help_dir / "templates").is_dir() else help_dir
        template_count = sum(1 for _ in templates_root.rglob("*.md"))

    return {
        "workspace": str(ws),
        "template_count": template_count,
        "summaries_present": summaries.is_file(),
        "has_help_dir": help_dir.is_dir(),
    }
