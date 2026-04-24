"""FastAPI app factory — wires routes, CORS, and the origin guard."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from attune_gui import __version__
from attune_gui.routes import rag, system
from attune_gui.security import origin_guard

logger = logging.getLogger(__name__)

# Package-relative static dir. In dev the UI is served from ui/src directly;
# this fallback lets the sidecar host the UI itself once it's been copied in.
_STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="attune-gui sidecar",
        version=__version__,
        description="Local FastAPI bridge to attune-rag / attune-author / attune-ai.",
        dependencies=[Depends(origin_guard)],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(system.router)
    app.include_router(rag.router)

    # Serve the UI. Prefer the packaged static dir; fall back to the repo
    # checkout layout (ui/src) for development.
    _mount_ui(app)

    return app


def _mount_ui(app: FastAPI) -> None:
    if _STATIC_DIR.is_dir() and (_STATIC_DIR / "index.html").is_file():
        app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="ui")
        return

    # Development fallback: serve from ui/src relative to the repo root.
    repo_root = Path(__file__).resolve().parents[3]
    dev_ui = repo_root / "ui" / "src"
    if dev_ui.is_dir() and (dev_ui / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dev_ui, html=True), name="ui-dev")
        return

    # Last-resort placeholder so / isn't a 404 in surprise deployments.
    @app.get("/", response_class=HTMLResponse)
    async def _placeholder() -> str:
        return (
            "<h1>attune-gui sidecar</h1>"
            "<p>UI not found. Expected one of:</p>"
            f"<ul><li><code>{_STATIC_DIR}/index.html</code></li>"
            f"<li><code>{dev_ui}/index.html</code></li></ul>"
        )

    @app.get("/robots.txt", response_class=PlainTextResponse)
    async def _robots() -> str:
        return "User-agent: *\nDisallow: /\n"
