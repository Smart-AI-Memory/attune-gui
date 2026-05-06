"""Friendly guard for the unpublished ``attune_rag.editor`` submodule.

The template-editor routes lean on ``attune_rag.editor`` (lint, rename,
schema). That submodule is part of attune-rag's local development tree
but hasn't been cut into a PyPI release yet. Anyone installing
attune-gui from PyPI will have an ``attune-rag`` whose top-level
package imports cleanly but is missing ``editor``.

This helper turns the resulting ``ModuleNotFoundError`` into a
503 with an actionable message, so the editor surfaces ``Editor
backend unavailable: install a newer attune-rag`` instead of a stack
trace. Once an attune-rag release ships with the editor submodule and
attune-gui's pin is bumped to require it, this guard becomes dead and
can be deleted.

TODO(attune_rag.editor): When attune-rag ships a release containing
the ``editor`` submodule on PyPI, do the following in one PR and then
delete this file:

1. Bump the ``attune-rag`` pin in ``pyproject.toml`` to require the
   release (e.g. ``attune-rag>=X.Y.Z,<...``).
2. In each consumer module — ``routes/editor_ws.py`` (2 callsites),
   ``routes/editor_schema.py``, ``routes/editor_template.py``, and
   ``routes/editor_lint.py`` (2 callsites) — replace the lazy
   ``require_editor_submodule(...)`` calls with top-level
   ``from attune_rag import editor as editor_mod`` (or the appropriate
   submodule, e.g. ``attune_rag.editor._rename``).
3. Remove the ``# noqa: PLC0415`` comments that justify the lazy import.
4. Delete this file (``_editor_dep.py``) and its tests.

Tracker: see CHANGELOG "Unreleased" → "Pending upstream".
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from fastapi import HTTPException, status

_REQUIRED_HINT = (
    "The attune-gui template editor needs ``attune_rag.editor``, which is "
    "not in any published attune-rag release yet. Install a newer attune-rag "
    "(local dev or pre-release) to enable editor routes."
)


def require_editor_submodule(name: str) -> Any:
    """Import ``attune_rag.editor.<name>`` or raise an HTTP 503.

    ``name`` is the dotted path *after* ``attune_rag.editor`` — e.g.
    ``""`` for the package itself, ``"_rename"`` or ``"_schema"`` for
    private modules.
    """
    full = "attune_rag.editor" + (f".{name}" if name else "")
    try:
        return import_module(full)
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "editor_backend_unavailable", "message": _REQUIRED_HINT},
        ) from exc
