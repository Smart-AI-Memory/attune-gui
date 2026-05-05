"""FastAPI app factory — wires routes, CORS, and the origin guard.

Serves the Cowork dashboard (Jinja2) at ``/`` and the JSON APIs under
``/api/*``. The legacy React UI was retired in 0.5.0.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from attune_gui import __version__
from attune_gui.routes import (  # noqa: F401
    choices,
    cowork_files,
    cowork_health,
    cowork_pages,
    cowork_specs,
    cowork_templates,
    editor_corpus,
    editor_health,
    editor_lint,
    editor_pages,
    editor_schema,
    editor_template,
    editor_ws,
    fs,
    help,
    jobs,
    living_docs,
    profile,
    rag,
    search,
    system,
)
from attune_gui.security import origin_guard

logger = logging.getLogger(__name__)

# Cowork dashboard CSS/JS lives next to the package.
_CW_STATIC_DIR = Path(__file__).parent / "static_cw"

# Template-editor frontend bundle (Vite output from editor-frontend/).
# Built artifacts are committed; consumers do not need Node at install time.
_EDITOR_STATIC_DIR = Path(__file__).parent / "static" / "editor"


def create_app() -> FastAPI:
    """Build the FastAPI app with origin-guard, CORS, and all routers wired."""
    app = FastAPI(
        title="attune-gui sidecar",
        version=__version__,
        description=(
            "Local FastAPI bridge to attune-rag / attune-author / attune-help (Living Docs)."
        ),
        dependencies=[Depends(origin_guard)],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # ---- JSON APIs (existing) -----------------------------------------------
    app.include_router(system.router)
    app.include_router(fs.router)
    app.include_router(rag.router)
    app.include_router(jobs.router)
    app.include_router(choices.router)
    app.include_router(help.router)
    app.include_router(search.router)
    app.include_router(profile.router)
    app.include_router(living_docs.router)
    app.include_router(editor_corpus.router)
    app.include_router(editor_health.router)
    app.include_router(editor_lint.router)
    app.include_router(editor_schema.router)
    app.include_router(editor_template.router)
    app.include_router(editor_ws.router)

    # ---- Template editor HTML shell -----------------------------------------
    # Registered after the JSON routes (which use /api/* prefixes) so the
    # /editor page handler is unambiguous.
    app.include_router(editor_pages.router)

    # ---- Cowork JSON APIs ----------------------------------------------------
    app.include_router(cowork_health.router)
    app.include_router(cowork_specs.router)
    app.include_router(cowork_templates.router)
    app.include_router(cowork_files.router)

    # ---- Cowork dashboard CSS/JS --------------------------------------------
    if _CW_STATIC_DIR.is_dir():
        app.mount("/cw-static", StaticFiles(directory=_CW_STATIC_DIR), name="cw-static")

    # ---- Template-editor frontend bundle ------------------------------------
    if _EDITOR_STATIC_DIR.is_dir():
        app.mount(
            "/static/editor",
            StaticFiles(directory=_EDITOR_STATIC_DIR),
            name="editor-static",
        )

    # ---- robots --------------------------------------------------------------
    @app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def _robots() -> str:
        return "User-agent: *\nDisallow: /\n"

    # ---- Cowork HTML pages (registered LAST so /api/* still resolves first) -
    # The pages router defines /, /dashboard, /dashboard/<page>. Specific
    # routes registered above (/api/*) take precedence; the HTML routes are
    # only matched when no JSON route does.
    app.include_router(cowork_pages.router)

    return app
