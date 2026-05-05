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
    """Redirect ``/`` to the default Health page."""
    return RedirectResponse(url="/dashboard", status_code=307)


# ---------------------------------------------------------------------------
# Health (landing page)
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def page_health(request: Request) -> HTMLResponse:
    """Render the Health page — per-layer version probe + corpus snapshot."""
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
    """Render the Templates page. ``filter`` is one of all|manual|generated|stale."""
    from attune_gui import editor_corpora  # noqa: PLC0415
    from attune_gui.routes import cowork_templates  # noqa: PLC0415

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

    # Resolve `templates_root` to a registered corpus once per page so
    # the row link can deep-link into the schema-driven /editor instead
    # of the legacy raw-textarea preview. If the templates root isn't in
    # any registered corpus, leave `editor_corpus_id` as None and the
    # template falls back to the preview link.
    editor_corpus_id: str | None = None
    editor_path_prefix: str = ""  # rel path of templates_root WITHIN the corpus
    if data["templates_root"]:
        resolved = editor_corpora.resolve_path(data["templates_root"])
        if resolved is not None:
            entry, rel_root = resolved
            editor_corpus_id = entry.id
            # Empty when templates_root IS the corpus root; e.g. "src/help"
            # when corpus is one level up.
            editor_path_prefix = "" if rel_root == "." else rel_root.rstrip("/")

    return templates.TemplateResponse(
        request,
        "templates.html",
        _ctx(
            request,
            "templates",
            items=items,
            templates_root=data["templates_root"],
            editor_corpus_id=editor_corpus_id,
            editor_path_prefix=editor_path_prefix,
            active_filter=filter,
            total=len(data["templates"]),
        ),
    )


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------


@router.get("/dashboard/specs", response_class=HTMLResponse, include_in_schema=False)
async def page_specs(request: Request) -> HTMLResponse:
    """Render the Specs page — feature specs grouped by phase + status."""
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
    """Render the Summaries page — inline-editable view of summaries.json."""
    from attune_gui.routes import cowork_files

    summaries: dict[str, str] = {}
    error: str | None = None
    not_yet_generated = False

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
        # 404 = file simply hasn't been generated yet → friendly empty state
        # rather than a red error banner.
        if exc.status_code == 404:
            not_yet_generated = True
        else:
            error = exc.detail if isinstance(exc.detail, str) else "Could not load summaries.json"

    return templates.TemplateResponse(
        request,
        "summaries.html",
        _ctx(
            request,
            "summaries",
            summaries=summaries,
            error=error,
            not_yet_generated=not_yet_generated,
        ),
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
    """Render the Preview/Edit page for any file under a known root (templates|specs|summaries)."""
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
    """Render the Living Docs page — health, composed doc rows, workspace config."""
    from attune_gui.routes import living_docs as ld

    health = await _safe_call(ld.health()) or {}
    rows_data = await _safe_call(ld.list_rows()) or {"rows": []}
    config_data = await _safe_call(ld.get_config()) or {}

    return templates.TemplateResponse(
        request,
        "living_docs.html",
        _ctx(
            request,
            "living-docs",
            health=health,
            rows=rows_data["rows"],
            config=config_data,
        ),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@router.get("/dashboard/commands", response_class=HTMLResponse, include_in_schema=False)
async def page_commands(request: Request, profile: str = "developer") -> HTMLResponse:
    """Render the Commands page — clickable cards for each registered command."""
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
    """Render the Jobs page — history with status, last-output, and Cancel buttons."""
    from attune_gui.routes import jobs as jobs_route

    jobs_data = await _safe_call(jobs_route.list_all_jobs()) or {"jobs": []}
    return templates.TemplateResponse(
        request, "jobs.html", _ctx(request, "jobs", jobs=jobs_data["jobs"])
    )
