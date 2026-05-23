"""In-memory freshness cache for the Templates page.

The Templates page shows one badge per ``*.md`` template:

* ``fresh``   — ``attune-author`` would not regenerate this file.
* ``stale``   — ``attune-author`` would regenerate this file.
* ``manual``  — file isn't owned by any feature in ``features.yaml``;
                it's hand-authored and never auto-regenerated.
* ``unknown`` — staleness check unavailable (attune-author not
                importable, no manifest, or the check raised).

The signal comes from
:func:`attune_author.staleness.check_staleness`, which returns
per-feature verdicts. We project those verdicts onto every
``*.md`` template file in
``<workspace>/.help/templates/<feature>/`` via
:mod:`attune_gui.services.staleness_mapping`.

The cache is populated lazily on first query for a given
workspace — one ``check_staleness`` call seeds every path. It's
in-memory only (no persistence) and cleared on sidecar restart.
Invalidation is explicit, called from three sites that mutate the
templates on disk: ``author.maintain``, the editor save endpoint,
and the watchfiles WebSocket.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

Status = Literal["fresh", "stale", "manual", "unknown"]

_CACHE: dict[Path, dict[Path, Status]] = {}
_DEGRADED_LOGGED: set[Path] = set()


def get_template_staleness(workspace: Path, template_path: Path) -> Status:
    """Return the staleness verdict for ``template_path`` inside ``workspace``.

    ``template_path`` may be absolute or relative to ``workspace``.
    On a cache miss, populates the entire workspace in one
    ``check_staleness`` call, then returns the per-path lookup.

    Returns ``"unknown"`` if the staleness check can't run
    (attune-author missing, no manifest, etc.) and logs the
    degrade once per workspace.
    """
    workspace = workspace.resolve()
    rel = _to_rel(workspace, template_path)
    if rel is None:
        return "manual"

    if workspace not in _CACHE:
        _CACHE[workspace] = _build_for_workspace(workspace)

    entries = _CACHE[workspace]
    if entries is _DEGRADED:
        return "unknown"
    return entries.get(rel, "manual")


def invalidate_workspace(workspace: Path) -> None:
    """Drop the entire entry for ``workspace``. Next query repopulates."""
    workspace = workspace.resolve()
    _CACHE.pop(workspace, None)
    _DEGRADED_LOGGED.discard(workspace)


def invalidate_path(workspace: Path, template_path: Path) -> None:
    """Drop the cache entry for one file.

    Subsequent queries for that file re-populate the *whole*
    workspace, since semantic-hash verdicts are per-feature and
    a single-file refresh isn't meaningful. Cheap enough — the
    expensive part is ``check_staleness`` itself.
    """
    workspace = workspace.resolve()
    rel = _to_rel(workspace, template_path)
    if rel is None:
        return
    entries = _CACHE.get(workspace)
    if entries is None or entries is _DEGRADED:
        return
    if rel in entries:
        # Drop the whole workspace; next get_template_staleness rebuilds.
        invalidate_workspace(workspace)


def _to_rel(workspace: Path, template_path: Path) -> Path | None:
    if template_path.is_absolute():
        try:
            return template_path.resolve().relative_to(workspace)
        except ValueError:
            return None
    return template_path


# Sentinel: workspace's staleness check failed; treat all paths as "unknown".
_DEGRADED: dict[Path, Status] = {}


def _build_for_workspace(workspace: Path) -> dict[Path, Status]:
    """Run ``check_staleness`` once and project onto every owned path.

    Returns ``_DEGRADED`` (the empty-dict sentinel) if the check
    cannot run; the caller treats that as "unknown" for every
    lookup.
    """
    try:
        from attune_author.manifest import load_manifest  # noqa: PLC0415
        from attune_author.staleness import check_staleness  # noqa: PLC0415
    except ImportError as exc:
        _log_degrade(workspace, f"attune-author not importable: {exc}")
        return _DEGRADED

    help_dir = workspace / ".help"
    if not (help_dir / "features.yaml").is_file():
        _log_degrade(workspace, f"no features.yaml at {help_dir}")
        return _DEGRADED

    try:
        manifest = load_manifest(help_dir)
        report = check_staleness(manifest, help_dir, workspace)
    except Exception as exc:  # noqa: BLE001
        _log_degrade(workspace, f"check_staleness raised: {exc}")
        return _DEGRADED

    from attune_gui.services.staleness_mapping import project_verdicts  # noqa: PLC0415

    return dict(project_verdicts(workspace, report.help_entries))


def _log_degrade(workspace: Path, reason: str) -> None:
    if workspace in _DEGRADED_LOGGED:
        return
    _DEGRADED_LOGGED.add(workspace)
    logger.warning(
        "staleness check unavailable for workspace %s — %s; "
        "Templates page will show 'unknown' badges",
        workspace,
        reason,
    )


def _reset_for_tests() -> None:
    """Clear all in-process state. Tests only — never call from app code."""
    _CACHE.clear()
    _DEGRADED_LOGGED.clear()
