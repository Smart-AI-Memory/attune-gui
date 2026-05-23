"""Project per-feature staleness verdicts onto per-file template paths.

``attune_author.staleness.check_staleness`` returns one verdict per
feature in ``features.yaml``. The Templates page lists one row per
``*.md`` template file. This helper bridges the two: for every
``<workspace>/.help/templates/<feature>/*.md`` file, return the
feature's ``is_stale`` verdict. Files outside any feature directory
are returned as ``"manual"`` — they're hand-authored and not
subject to regeneration.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from attune_author.staleness import FeatureStaleness

Status = Literal["fresh", "stale", "manual"]


def project_verdicts(
    workspace: Path,
    feature_entries: list[FeatureStaleness],
) -> dict[Path, Status]:
    """Build a ``{rel_path_from_workspace → status}`` map for one workspace.

    Walks ``<workspace>/.help/templates/<feature>/*.md`` for every
    feature that appears in ``feature_entries`` and projects the
    feature's ``is_stale`` verdict onto each file. Returns paths
    relative to ``workspace`` so callers can key the cache by the
    same shape the route already has.

    Files inside a feature directory but with a non-``.md`` extension
    are skipped. Features whose template directory does not exist
    are silently ignored (no entries contributed).

    Args:
        workspace: Project root containing ``.help/``.
        feature_entries: ``check_staleness(...).help_entries``.

    Returns:
        Mapping of relative template path → ``"fresh"`` or ``"stale"``.
        Paths not in this map are by convention treated as ``"manual"``
        by the cache layer.
    """
    out: dict[Path, Status] = {}
    templates_root = workspace / ".help" / "templates"
    if not templates_root.is_dir():
        return out

    for entry in feature_entries:
        feature_dir = templates_root / entry.feature
        if not feature_dir.is_dir():
            continue
        status: Status = "stale" if entry.is_stale else "fresh"
        for md_path in feature_dir.rglob("*.md"):
            try:
                rel = md_path.relative_to(workspace)
            except ValueError:
                continue
            out[rel] = status
    return out
