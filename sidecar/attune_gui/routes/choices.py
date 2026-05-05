"""Choices API — supplies finite-set values to the Commands page form.

Why this exists: the dashboard's Commands page builds an args form
from each command's ``args_schema``. Some args (notably ``feature``
on ``author.generate`` / ``author.regen`` / ``author.maintain``)
have a finite, manifest-driven set of valid values. Hard-coding them
in the schema is wrong (manifests vary per project); making them
free-text traps users into typos that surface as runtime errors.

Convention: a property with a ``ui:choicesUrl`` extension points at
an endpoint that returns ``{choices: list[str]}``. The form fetches
the URL (substituting ``{otherField}`` placeholders from sibling
input values) and renders a ``<datalist>`` autocomplete.

Endpoints:

- ``GET /api/author/features?help_dir=<path>`` — list the feature
  names from ``<help_dir>/features.yaml``. 404 if the manifest is
  missing, 400 if it's malformed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/author", tags=["choices"])


@router.get("/features")
async def list_features(
    help_dir: str | None = Query(
        default=None,
        description="Path to a `.help/` directory containing `features.yaml`.",
    ),
    project_path: str | None = Query(
        default=None,
        description="Project root; the manifest is read from `<project_path>/.help/`.",
    ),
) -> dict[str, Any]:
    """Return the feature names from ``<help_dir>/features.yaml``.

    Pass *one of*:

    - ``help_dir`` — direct path to a ``.help/`` directory (matches the
      ``author.generate`` form's field shape).
    - ``project_path`` — a project root; the manifest is read from
      ``<project_path>/.help/`` (matches the ``author.regen`` form).

    Both are resolved against the sidecar's CWD if not absolute, so
    what the form sees matches what the executor will see.
    """
    if help_dir and project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ambiguous_args",
                "message": "Pass exactly one of help_dir or project_path.",
            },
        )
    if not help_dir and not project_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "missing_arg",
                "message": "Pass help_dir or project_path.",
            },
        )
    if project_path:
        help_dir = str(Path(project_path).expanduser().resolve() / ".help")
    # Lazy-import the manifest loader so cold-start stays fast and
    # the dependency on attune-help stays optional at import time.
    try:
        from attune_help.manifest import load_manifest  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "missing_dep",
                "message": (
                    f"attune-help isn't installed: {exc}. Install with "
                    "`pip install attune-help`."
                ),
            },
        ) from exc

    resolved = Path(help_dir).expanduser().resolve()
    if not resolved.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "help_dir_missing",
                "message": f"No directory at {resolved}.",
            },
        )

    try:
        manifest = load_manifest(resolved)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "manifest_missing", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "manifest_malformed", "message": str(exc)},
        ) from exc

    return {
        "choices": sorted(manifest.features.keys()),
        "help_dir": str(resolved),
    }
