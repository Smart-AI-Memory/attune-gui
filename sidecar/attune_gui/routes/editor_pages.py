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

import json
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
_MANIFEST_PATH = _BUNDLE_DIR / ".vite" / "manifest.json"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _read_bundle_assets() -> tuple[str, str]:
    """Return ``(js_filename, css_filename)`` for the editor bundle.

    Vite emits content-hashed filenames plus ``.vite/manifest.json``
    mapping logical sources (``src/main.ts``, ``style.css``) to their
    hashed output. The route reads it on every request — the file is
    tiny (<1 KB) and only changes on rebuild, so a cache layer would
    add complexity for no measurable win.

    Falls back to the legacy unhashed names (``editor.js`` /
    ``editor.css``) if the manifest is missing — handy during a stale
    install where the old deterministic-named bundle is still on disk.
    Returns sentinel ``("dev.js", "dev.css")`` if neither is present so
    the page still renders (with a broken bundle URL the browser will
    surface clearly).
    """
    if _MANIFEST_PATH.is_file():
        try:
            data = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
            entry = data.get("src/main.ts") or {}
            css_entry = data.get("style.css") or {}
            js = entry.get("file")
            css = css_entry.get("file") or (entry.get("css") or [None])[0]
            if js and css:
                return js, css
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read editor manifest: %s", exc)

    legacy_js = _BUNDLE_DIR / "editor.js"
    legacy_css = _BUNDLE_DIR / "editor.css"
    if legacy_js.is_file() and legacy_css.is_file():
        return "editor.js", "editor.css"

    return "dev.js", "dev.css"


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
    js_file, css_file = _read_bundle_assets()
    return templates.TemplateResponse(
        request,
        "editor.html",
        {
            "corpus_id": corpus or "",
            "rel_path": path or "",
            "session_token": current_session_token(),
            "bundle_js": js_file,
            "bundle_css": css_file,
        },
    )
