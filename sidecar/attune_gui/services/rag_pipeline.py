"""Workspace-keyed RagPipeline cache shared across route handlers.

Owns ``pipeline_for(workspace)`` (D4 of the architecture-realignment
spec, finding #5) — the public successor to the old
``attune_gui.routes.rag._get_pipeline``. Other route modules
(``routes.rag``, ``routes.search``, ``routes.living_docs``) import
from here instead of crossing into ``routes.rag``'s private surface.
``commands.py``'s ``_author_proxy(invalidate_after=True)`` likewise
imports :func:`invalidate` from here.

The module also exposes :func:`workspace_from_request` so HTTP route
handlers don't each have to re-import :mod:`attune_gui.workspace`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune_rag import RagPipeline

logger = logging.getLogger(__name__)

# Workspace-keyed pipeline cache. The empty ``Path()`` is a
# sentinel for the "no workspace configured" fallback that loads
# the bundled AttuneHelpCorpus.
_PIPELINES: dict[Path, RagPipeline] = {}
_DEFAULT_KEY = Path()


def pipeline_for(workspace: Path | None = None) -> RagPipeline:
    """Return a cached :class:`attune_rag.RagPipeline` for ``workspace``.

    When ``workspace/.help/templates/`` exists, the pipeline loads
    that directory as a :class:`attune_rag.DirectoryCorpus` so
    queries retrieve from the project's own templates. Otherwise
    the pipeline falls back to attune-rag's bundled
    ``AttuneHelpCorpus``.

    The cache is process-global; pipelines are reused until
    :func:`invalidate` drops the entry (typically after a
    template-regeneration run).
    """

    from attune_rag import DirectoryCorpus, QueryExpander, RagPipeline  # noqa: PLC0415

    key = workspace if workspace is not None else _DEFAULT_KEY

    if key not in _PIPELINES:
        corpus = None
        if workspace is not None:
            corpus_dir = workspace / ".help" / "templates"
            if corpus_dir.is_dir():
                corpus = DirectoryCorpus(corpus_dir)
        _PIPELINES[key] = RagPipeline(corpus=corpus, expander=QueryExpander())

    return _PIPELINES[key]


def invalidate(workspace: Path | None) -> None:
    """Drop the cached pipeline for ``workspace`` (or the default fallback).

    The next :func:`pipeline_for` call rebuilds the pipeline from
    scratch, picking up any new templates on disk. Safe to call when
    no entry exists for the key.
    """

    key = workspace if workspace is not None else _DEFAULT_KEY
    _PIPELINES.pop(key, None)


def workspace_from_request() -> Path | None:
    """Resolve the current workspace for HTTP route handlers."""

    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    return get_workspace()
