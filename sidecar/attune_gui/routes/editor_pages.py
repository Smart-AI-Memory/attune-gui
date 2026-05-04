"""HTML shell for the template editor.

A single Jinja2 page at ``/editor`` that hosts the pre-bundled CodeMirror
frontend. The shell stays declarative — all interactive logic lives in
``static/editor/editor.{js,css}``.

Query params (parsed client-side, echoed in the bootstrap script tag):

    /editor?corpus=<id>&path=<rel>

If either is missing the page renders an empty-state shell; the user
can still pick a corpus and path from the UI once it lands.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from attune_gui.security import current_session_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["editor-pages"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_BUNDLE_DIR = Path(__file__).resolve().parent.parent / "static" / "editor"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _bundle_version() -> str:
    """Return a cache-busting tag for ``/static/editor/editor.{js,css}``.

    Uses the bundle's mtime if it exists; falls back to ``dev`` so the
    /editor route still renders even before the first ``make
    build-editor``. Browsers cache the deterministic filename
    aggressively — bumping the version string on each rebuild forces a
    fresh fetch.
    """
    bundle = _BUNDLE_DIR / "editor.js"
    if bundle.is_file():
        return str(int(bundle.stat().st_mtime))
    return "dev"


@router.get("/editor", response_class=HTMLResponse, include_in_schema=False)
async def editor_page(
    request: Request,
    corpus: str | None = None,
    path: str | None = None,
) -> HTMLResponse:
    """Render the editor HTML shell.

    The shell carries:
      - the CodeMirror bundle from ``/static/editor/``
      - the per-process session token (so the bundle can echo it as
        ``X-Attune-Client`` on mutating requests)
      - the requested corpus + path so the bundle can fetch the
        template on first paint without a second roundtrip.
    """
    return templates.TemplateResponse(
        request,
        "editor.html",
        {
            "corpus_id": corpus or "",
            "rel_path": path or "",
            "session_token": current_session_token(),
            "bundle_version": _bundle_version(),
        },
    )
