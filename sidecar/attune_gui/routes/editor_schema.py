"""Serve the template-frontmatter JSON schema (M3 task #16).

The schema is the source of truth for both the server-side validator
(``attune_rag.editor`` lint) and the browser form. Exposing it over
HTTP keeps the form schema-driven — adding a new optional frontmatter
field is a schema-only change.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/editor", tags=["editor-schema"])


@router.get("/template-schema")
async def template_schema() -> dict[str, Any]:
    """Return the JSON schema bundled with attune-rag.

    The schema is a small static document — load it lazily so the
    sidecar's cold start does not pay for a json import we may never
    use.
    """
    from attune_rag.editor._schema import load_schema  # noqa: PLC0415

    try:
        return load_schema()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template schema not found: {exc}",
        ) from exc
