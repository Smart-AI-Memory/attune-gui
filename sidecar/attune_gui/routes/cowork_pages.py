"""HTML page routes for the Cowork dashboard.

Pages are server-rendered with Jinja2. Data comes from the existing JSON
APIs (called in-process via the route handlers, not over HTTP) so the page
templates stay declarative and the JSON API stays the single source of truth.

Routes:
    GET /                  → redirect to /dashboard
    GET /dashboard         → Health (cross-layer + corpus snapshot)
    GET /dashboard/templates
    GET /dashboard/specs
    GET /dashboard/summaries
    GET /dashboard/preview
    GET /dashboard/commands
    GET /dashboard/jobs
    GET /dashboard/living-docs

Existing JSON APIs power the pages:
    /api/cowork/layers, /api/cowork/corpus, /api/cowork/specs,
    /api/cowork/templates, /api/cowork/files/...
    /api/commands, /api/jobs, /api/living-docs/health, /api/living-docs/docs,
    /api/living-docs/queue, /api/living-docs/config
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cowork-pages"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _safe_call(coro):  # type: ignore[no-untyped-def]
    """Call a route coroutine and swallow exceptions into ``None`` for templates."""
    try:
        return await coro
    except Exception:  # noqa: BLE001
        logger.exception("page-data fetch failed")
        return None


def _ctx(request: Request, active: str, **extra: Any) -> dict[str, Any]:
    # ``request`` is accepted for symmetry with older Starlette but is not
    # placed in the context — TemplateResponse(request, name, context)
    # injects it automatically in modern Starlette.
    del request
    return {
        "active": active,
        "nav": [
            {"slug": "health", "label": "Health", "href": "/dashboard"},
            {"slug": "templates", "label": "Templates", "href": "/dashboard/templates"},
            {"slug": "specs", "label": "Specs", "href": "/dashboard/specs"},
            {"slug": "summaries", "label": "Summaries", "href": "/dashboard/summaries"},
            {"slug": "living-docs", "label": "Living Docs", "href": "/dashboard/living-docs"},
            {"slug": "commands", "label": "Commands", "href": "/dashboard/commands"},
            {"slug": "jobs", "label": "Jobs", "href": "/dashboard/jobs"},
        ],
        **extra,
    }


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=307)


# ---------------------------------------------------------------------------
# Health (landing page)
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def page_health(request: Request) -> HTMLResponse:
    from attune_gui.routes import cowork_health

    layers = await _safe_call(cowork_health.layer_health()) or {"layers": {}}
    corpus = await _safe_call(cowork_health.corpus_health()) or {}
    return templates.TemplateResponse(
        request, "health.html", _ctx(request, "health", layers=layers["layers"], corpus=corpus)
    )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get("/dashboard/templates", response_class=HTMLResponse, include_in_schema=False)
async def page_templates(request: Request, filter: str = "all") -> HTMLResponse:
    from attune_gui.routes import cowork_templates

    data = await _safe_call(cowork_templates.list_templates()) or {
        "templates": [],
        "templates_root": None,
    }
    items = data["templates"]
    if filter == "manual":
        items = [t for t in items if t["manual"]]
    elif filter == "generated":
        items = [t for t in items if not t["manual"]]
    elif filter == "stale":
        items = [t for t in items if t["staleness"] in ("stale", "very-stale")]
    return templates.TemplateResponse(
        request,
        "templates.html",
        _ctx(
            request,
            "templates",
            items=items,
            templates_root=data["templates_root"],
            active_filter=filter,
            total=len(data["templates"]),
        ),
    )


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------


@router.get("/dashboard/specs", response_class=HTMLResponse, include_in_schema=False)
async def page_specs(request: Request) -> HTMLResponse:
    from attune_gui.routes import cowork_specs

    data = await _safe_call(cowork_specs.list_specs()) or {"specs": [], "specs_root": None}
    return templates.TemplateResponse(
        request,
        "specs.html",
        _ctx(request, "specs", specs=data["specs"], specs_root=data["specs_root"]),
    )


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


@router.get("/dashboard/summaries", response_class=HTMLResponse, include_in_schema=False)
async def page_summaries(request: Request) -> HTMLResponse:
    from attune_gui.routes import cowork_files

    summaries: dict[str, str] = {}
    error: str | None = None
    try:
        data = await cowork_files.read_file(root="summaries", path="summaries.json")
        try:
            summaries = json.loads(data["content"])
            if not isinstance(summaries, dict):
                error = "summaries.json is not a JSON object."
                summaries = {}
        except json.JSONDecodeError as exc:
            error = f"Invalid JSON in summaries.json: {exc}"
    except HTTPException as exc:
        error = exc.detail if isinstance(exc.detail, str) else "Could not load summaries.json"

    return templates.TemplateResponse(
        request, "summaries.html", _ctx(request, "summaries", summaries=summaries, error=error)
    )


# ---------------------------------------------------------------------------
# Preview / Edit
# ---------------------------------------------------------------------------


@router.get("/dashboard/preview", response_class=HTMLResponse, include_in_schema=False)
async def page_preview(
    request: Request,
    root: str = "templates",
    path: str = "",
) -> HTMLResponse:
    from attune_gui.routes import cowork_files

    file_data: dict[str, Any] | None = None
    rendered_html: str | None = None
    error: str | None = None

    if not path:
        error = "No file path provided. Use ?root=…&path=…"
    else:
        try:
            file_data = await cowork_files.read_file(root, path)
            r = await cowork_files.render_file(root, path)
            rendered_html = r["html"]
        except HTTPException as exc:
            error = exc.detail if isinstance(exc.detail, str) else "Could not load file."

    return templates.TemplateResponse(
        request,
        "preview.html",
        _ctx(
            request,
            "preview",
            file=file_data,
            rendered_html=rendered_html,
            error=error,
            root=root,
            path=path,
        ),
    )


# ---------------------------------------------------------------------------
# Living Docs
# ---------------------------------------------------------------------------


@router.get("/dashboard/living-docs", response_class=HTMLResponse, include_in_schema=False)
async def page_living_docs(request: Request) -> HTMLResponse:
    from attune_gui.routes import living_docs as ld

    health = await _safe_call(ld.health()) or {}
    docs_data = await _safe_call(ld.list_docs()) or {"docs": []}
    queue_data = await _safe_call(ld.list_queue()) or {"queue": []}
    config_data = await _safe_call(ld.get_config()) or {}

    return templates.TemplateResponse(
        request,
        "living_docs.html",
        _ctx(
            request,
            "living-docs",
            health=health,
            docs=docs_data["docs"],
            queue=queue_data["queue"],
            config=config_data,
        ),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@router.get("/dashboard/commands", response_class=HTMLResponse, include_in_schema=False)
async def page_commands(request: Request, profile: str = "developer") -> HTMLResponse:
    from attune_gui.routes import jobs as jobs_route

    cmds_data = await _safe_call(jobs_route.commands(profile=profile)) or {"commands": []}
    return templates.TemplateResponse(
        request,
        "commands.html",
        _ctx(
            request,
            "commands",
            commands=cmds_data["commands"],
            profile=profile,
        ),
    )


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@router.get("/dashboard/jobs", response_class=HTMLResponse, include_in_schema=False)
async def page_jobs(request: Request) -> HTMLResponse:
    from attune_gui.routes import jobs as jobs_route

    jobs_data = await _safe_call(jobs_route.list_all_jobs()) or {"jobs": []}
    return templates.TemplateResponse(
        request, "jobs.html", _ctx(request, "jobs", jobs=jobs_data["jobs"])
    )
