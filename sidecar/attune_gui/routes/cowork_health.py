"""Cross-layer health probe.

GET /api/cowork/layers — versions + import status of rag/help/author/gui.
GET /api/cowork/corpus — corpus root + template count + summaries presence.

These probes never import the target packages — they use ``importlib.metadata``
so a missing optional dep never crashes the dashboard.
"""

from __future__ import annotations

import importlib.metadata as ilm
import sys
from pathlib import Path
from typing import Any

import yaml
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
    """Return version + importability for each attune layer.

    Also surfaces the interpreter probing for metadata — a "not installed"
    result is usually an env-mismatch (dashboard running under a different
    Python than the venv that has the package), so the interpreter path
    makes the situation self-diagnosing.
    """
    vi = sys.version_info
    return {
        "layers": {key: _probe(pkg) for key, pkg in _PACKAGES},
        "interpreter": sys.executable,
        "python_version": f"{vi.major}.{vi.minor}.{vi.micro}",
    }


def _probe_manifest(ws: Path) -> tuple[str | None, int]:
    """Locate features.yaml under the workspace and count its features.

    Checks ``<ws>/.help/features.yaml`` first (project-root workspace),
    then ``<ws>/features.yaml`` (workspace pointed directly at a .help dir).
    """
    for candidate in (ws / ".help" / "features.yaml", ws / "features.yaml"):
        if not candidate.is_file():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return str(candidate), 0
        features = data.get("features") if isinstance(data, dict) else None
        count = len(features) if isinstance(features, dict) else 0
        return str(candidate), count
    return None, 0


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
            "manifest_path": None,
            "feature_count": 0,
        }

    help_dir = ws / ".help"
    summaries = help_dir / "summaries.json"
    template_count = 0
    if help_dir.is_dir():
        # Count .md templates under .help/templates if it exists, else under .help
        templates_root = help_dir / "templates" if (help_dir / "templates").is_dir() else help_dir
        template_count = sum(1 for _ in templates_root.rglob("*.md"))

    manifest_path, feature_count = _probe_manifest(ws)

    return {
        "workspace": str(ws),
        "template_count": template_count,
        "summaries_present": summaries.is_file(),
        "has_help_dir": help_dir.is_dir(),
        "manifest_path": manifest_path,
        "feature_count": feature_count,
    }
