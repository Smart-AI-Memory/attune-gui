"""FastAPI app factory — wires routes, CORS, and the origin guard.

Mounts the new Cowork dashboard at ``/`` (Jinja2 server-rendered) and keeps
the legacy React UI available at ``/legacy/`` for fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from attune_gui import __version__
from attune_gui.routes import (  # noqa: F401
    cowork_files,
    cowork_health,
    cowork_pages,
    cowork_specs,
    cowork_templates,
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

# Package-relative dirs.
_PKG_DIR = Path(__file__).parent
_STATIC_DIR = _PKG_DIR / "static"  # legacy React build output
_CW_STATIC_DIR = _PKG_DIR / "static_cw"  # Cowork dashboard CSS/JS


def create_app() -> FastAPI:
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

    # ---- JSON APIs (existing) -------------------------------------------------
    app.include_router(system.router)
    app.include_router(fs.router)
    app.include_router(rag.router)
    app.include_router(jobs.router)
    app.include_router(help.router)
    app.include_router(search.router)
    app.include_router(profile.router)
    app.include_router(living_docs.router)

    # ---- Cowork JSON APIs ----------------------------------------------------
    app.include_router(cowork_health.router)
    app.include_router(cowork_specs.router)
    app.include_router(cowork_templates.router)
    app.include_router(cowork_files.router)

    # ---- Cowork dashboard CSS/JS --------------------------------------------
    if _CW_STATIC_DIR.is_dir():
        app.mount("/cw-static", StaticFiles(directory=_CW_STATIC_DIR), name="cw-static")

    # ---- Legacy React UI at /legacy/ ----------------------------------------
    _mount_legacy_ui(app)

    # ---- Cowork HTML pages (registered LAST so /api/* still resolves first) -
    # The pages router defines /, /dashboard, /dashboard/<page>. Specific
    # routes registered above (/api/*) take precedence; the HTML routes are
    # only matched when no JSON route does.
    app.include_router(cowork_pages.router)

    return app


def _mount_legacy_ui(app: FastAPI) -> None:
    """Mount the React UI at ``/legacy/`` so the new dashboard owns ``/``."""
    if _STATIC_DIR.is_dir() and (_STATIC_DIR / "index.html").is_file():
        app.mount(
            "/legacy",
            StaticFiles(directory=_STATIC_DIR, html=True),
            name="legacy-ui",
        )
        return

    # Development fallback: serve the Vite build output.
    repo_root = Path(__file__).resolve().parents[2]
    dist_ui = repo_root / "ui" / "dist"
    if dist_ui.is_dir() and (dist_ui / "index.html").is_file():
        app.mount(
            "/legacy",
            StaticFiles(directory=dist_ui, html=True),
            name="legacy-ui-dist",
        )
        return

    @app.get("/legacy", response_class=HTMLResponse)
    async def _legacy_placeholder() -> str:
        return (
            "<h1>Legacy React UI not built</h1>"
            "<p>Run <code>cd ui && npm run build</code> to enable the legacy UI.</p>"
            "<p><a href='/dashboard'>← Back to dashboard</a></p>"
        )

    @app.get("/robots.txt", response_class=PlainTextResponse)
    async def _robots() -> str:
        return "User-agent: *\nDisallow: /\n"
