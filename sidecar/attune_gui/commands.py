"""Command registry — the canonical list of what the GUI can run.

Each CommandSpec names an executor (async), a JSON Schema for its args so
the UI can render a form, and human-facing metadata. Adding a command is
one entry in COMMANDS; the UI discovers it automatically via
/api/commands.

Profiles
--------
Each CommandSpec declares which profiles can see it:
  "developer" — full attune package user (all commands)
  "author"    — tech writers / doc authors (rag, author, help, doc + memory)

GET /api/commands?profile=author returns only commands visible to that profile.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from attune_gui.jobs import JobContext

logger = logging.getLogger(__name__)


def _orchestration_dispatcher(orchestration_name: str) -> ExecutorFn:
    """Build an executor that hands the call off to attune-author's orchestration runtime.

    The gui keeps a thin :class:`CommandSpec` so its profile filtering,
    job runner, and ``GET /api/commands`` continue to work with no
    changes. The actual executor body lives in attune-author. The
    returned closure converts the gui's :class:`JobContext` into the
    orchestration-runtime equivalent and unwraps ``RunResult.output``
    so the existing job runner sees a plain dict.
    """

    async def _dispatch(args: dict[str, Any], ctx: JobContext) -> Any:
        from attune_author.orchestration import (  # noqa: PLC0415
            JobContext as AuthorCtx,
        )
        from attune_author.orchestration import (
            run_command,
        )

        author_ctx = AuthorCtx(job_id=ctx.job_id, log=ctx.log)
        result = await run_command(orchestration_name, args, author_ctx)
        return result.output

    _dispatch.__name__ = f"_dispatch_{orchestration_name.replace('.', '_')}"
    return _dispatch


def _proxy_command(orchestration_name: str) -> CommandSpec:
    """Mirror an attune-author orchestration spec into a gui ``CommandSpec``.

    Importing :mod:`attune_author.orchestration.commands.<ns>` triggers
    registration on the orchestration registry; this helper then copies
    the metadata into a gui-shaped ``CommandSpec`` whose executor is a
    dispatcher closure. Phases D2 and D3 reuse this for the ``author.*``
    and ``help.*`` migrations.
    """

    from attune_author.orchestration import COMMANDS as _AUTHOR_COMMANDS  # noqa: PLC0415

    src = _AUTHOR_COMMANDS[orchestration_name]
    return CommandSpec(
        name=src.name,
        title=src.title,
        domain=src.domain,
        description=src.description,
        args_schema=src.args_schema,
        executor=_orchestration_dispatcher(orchestration_name),
        cancellable=src.cancellable,
        profiles=src.profiles,
    )


def _author_proxy(
    orchestration_name: str,
    *,
    pre_resolve_workspace: bool = False,
    invalidate_after: bool = False,
) -> CommandSpec:
    """Specialized :func:`_proxy_command` variant for ``author.*``.

    Two host-only behaviours that don't belong in the orchestration
    runtime:

    - ``pre_resolve_workspace=True`` — call :func:`_resolve_project_paths`
      on the incoming args so workspace-driven defaults still work even
      though the orchestration helper requires explicit paths. Passes
      the resolved ``project_root`` and ``help_dir`` strings through to
      ``run_command``.
    - ``invalidate_after=True`` — after dispatch, look for a
      ``project_root`` in the result dict and call
      ``attune_gui.routes.rag.invalidate`` so the route layer's pipeline
      cache stays in sync after a regeneration.

    Phase D4 will replace the private ``rag.invalidate`` call with the
    public ``pipeline_for(corpus_id)`` API.
    """

    from attune_author.orchestration import COMMANDS as _AUTHOR_COMMANDS  # noqa: PLC0415

    src = _AUTHOR_COMMANDS[orchestration_name]
    base_dispatch = _orchestration_dispatcher(orchestration_name)

    async def _dispatch(args: dict[str, Any], ctx: JobContext) -> Any:
        if pre_resolve_workspace:
            try:
                project_root, help_dir = _resolve_project_paths(args)
            except ValueError:
                # No path supplied and no workspace configured; let the
                # orchestration helper raise its ValidationError so the
                # job runner surfaces a consistent error.
                pass
            else:
                args = {
                    **args,
                    "project_root": str(project_root),
                    "help_dir": str(help_dir),
                }

        out = await base_dispatch(args, ctx)

        if invalidate_after and isinstance(out, dict):
            project_root_str = out.get("project_root")
            if project_root_str:
                from attune_gui.services.rag_pipeline import invalidate  # noqa: PLC0415

                invalidate(Path(project_root_str))

        return out

    return CommandSpec(
        name=src.name,
        title=src.title,
        domain=src.domain,
        description=src.description,
        args_schema=src.args_schema,
        executor=_dispatch,
        cancellable=src.cancellable,
        profiles=src.profiles,
    )


def _require_absolute(field: str, raw: str) -> None:
    """Reject relative paths up-front so users see a clear error.

    Without this, ``Path('foo').resolve()`` silently joins ``foo`` to the
    sidecar's cwd, producing confusing doubled paths in downstream errors
    (e.g. /Users/.../attune-gui/Users/.../attune-ai/.help).
    """
    if raw.startswith("/") or raw.startswith("~"):
        return
    raise ValueError(
        f"{field} must be an absolute path (e.g. /Users/you/project) "
        f"or start with ~ (e.g. ~/project), got: {raw!r}",
    )


def _autopromote_to_manifest_dir(help_dir: Path) -> Path:
    """If ``help_dir`` doesn't contain features.yaml but its parent does,
    promote to the parent.

    Common UX pitfall: the path picker lands on ``.help/templates`` (the
    children dir) instead of ``.help`` (the manifest dir). Without this,
    every downstream loader fails with a confusing FileNotFoundError.
    The walk only goes one level — deeper accidents stay errors so we
    don't silently rewrite paths that look nothing like a help dir.
    """
    if (help_dir / "features.yaml").exists():
        return help_dir
    parent = help_dir.parent
    if parent != help_dir and (parent / "features.yaml").exists():
        logger.info(
            "Auto-promoted help_dir from %s to %s (features.yaml lives in parent)",
            help_dir,
            parent,
        )
        return parent
    return help_dir


def _resolve_project_paths(args: dict[str, Any]) -> tuple[Path, Path]:
    """Return (project_root, help_dir) from args.

    Priority:
      1. ``project_path`` — convenience key, derives help_dir as <root>/.help
      2. ``project_root`` / ``help_dir`` legacy pair, when explicitly non-empty
      3. Configured workspace (from ~/.attune-gui/config.json)
    Raises ValueError when no path is provided and no workspace is configured.
    Relative paths are rejected with a clear error.

    The resolved help_dir is auto-promoted to its parent when features.yaml
    lives there instead — see :func:`_autopromote_to_manifest_dir`.
    """
    project_path_raw = str(args.get("project_path", "")).strip()
    if project_path_raw:
        _require_absolute("project_path", project_path_raw)
        project_root = Path(project_path_raw).expanduser().resolve()
        return project_root, _autopromote_to_manifest_dir(project_root / ".help")

    project_root_raw = str(args.get("project_root", "")).strip()
    help_dir_raw = str(args.get("help_dir", "")).strip()

    if not project_root_raw and not help_dir_raw:
        from attune_gui.workspace import get_workspace  # noqa: PLC0415

        ws = get_workspace()
        if ws is None:
            raise ValueError(
                "No project_path provided and no workspace configured. "
                "Set a workspace via PUT /api/living-docs/config."
            )
        return ws, _autopromote_to_manifest_dir(ws / ".help")

    project_root_raw = project_root_raw or "."
    help_dir_raw = help_dir_raw or ".help"
    if project_root_raw != ".":
        _require_absolute("project_root", project_root_raw)
    if help_dir_raw != ".help":
        _require_absolute("help_dir", help_dir_raw)
    return (
        Path(project_root_raw).expanduser().resolve(),
        _autopromote_to_manifest_dir(Path(help_dir_raw).expanduser().resolve()),
    )


ExecutorFn = Callable[[dict[str, Any], JobContext], Awaitable[Any]]


@dataclass(frozen=True)
class CommandSpec:
    name: str  # dotted id, e.g. "rag.query"
    title: str  # human label
    domain: str  # "rag" | "author" | "ai" | "help"
    description: str
    args_schema: dict[str, Any]  # JSON-Schema-ish; UI uses it to render a form
    executor: ExecutorFn
    cancellable: bool = True
    profiles: tuple[str, ...] = field(default=("developer",))


# ---------------------------------------------------------------------------
# RAG: query
# ---------------------------------------------------------------------------


async def _exec_rag_query(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    query = args["query"]
    k = int(args.get("k", 3))
    ctx.log(f"retrieving top-{k} for: {query!r}")

    from attune_gui.services.rag_pipeline import pipeline_for  # noqa: PLC0415
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    project_path_raw = str(args.get("project_path", "")).strip()
    workspace = (
        Path(project_path_raw).expanduser().resolve() if project_path_raw else get_workspace()
    )
    pipeline = pipeline_for(workspace)

    result = await asyncio.to_thread(pipeline.run, query, k=k)
    hits = [
        {
            "path": h.template_path,
            "category": h.category,
            "score": h.score,
            "excerpt": h.excerpt,
        }
        for h in result.citation.hits
    ]
    ctx.log(f"retrieved {len(hits)} hit(s)")

    return {
        "query": query,
        "k": k,
        "total_hits": len(hits),
        "hits": hits,
        "augmented_prompt": result.augmented_prompt,
    }


# ---------------------------------------------------------------------------
# Author: generate
# ---------------------------------------------------------------------------


async def _exec_author_generate(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415

    feature = args["feature"]
    project_root, help_dir = _resolve_project_paths(args)
    depths = args.get("depths") or None
    all_kinds = bool(args.get("all_kinds", False))
    overwrite = bool(args.get("overwrite", False))

    ctx.log(f"loading manifest from {help_dir}")
    manifest = await asyncio.to_thread(load_manifest, help_dir)
    if feature not in manifest.features:
        available = ", ".join(sorted(manifest.features.keys())) or "(none)"
        raise ValueError(f"Feature {feature!r} not in manifest. Available: {available}")
    feat = manifest.features[feature]

    if all_kinds:
        from attune_author.generator import _ALL_TEMPLATE_NAMES  # noqa: PLC0415

        depths = list(_ALL_TEMPLATE_NAMES)
    ctx.log(f"generating {len(depths) if depths else 'default'} kind(s) for feature={feature}")

    await asyncio.sleep(0)

    result = await asyncio.to_thread(
        generate_feature_templates,
        feature=feat,
        help_dir=help_dir,
        project_root=project_root,
        depths=depths,
        overwrite=overwrite,
    )

    templates = [
        {"depth": t.depth, "path": str(t.path), "source_hash": t.source_hash}
        for t in result.templates
    ]
    ctx.log(f"wrote {len(templates)} template(s)")
    for t in templates:
        ctx.log(f"  {t['depth']:<15} {t['path']}")

    return {
        "feature": result.feature,
        "source_hash": result.source_hash,
        "matched_files": list(result.matched_files),
        "templates": templates,
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


COMMANDS: dict[str, CommandSpec] = {
    "rag.query": CommandSpec(
        name="rag.query",
        title="Query corpus",
        domain="rag",
        description=(
            "Run retrieval against the default attune-rag corpus and "
            "show hits + augmented prompt."
        ),
        args_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "title": "Query",
                    "minLength": 1,
                    "description": "Natural-language query to retrieve matching documents.",
                },
                "k": {
                    "type": "integer",
                    "title": "k (top-k)",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 20,
                },
                "project_path": {
                    "type": "string",
                    "title": "Project path",
                    "default": "",
                    "description": (
                        "Root of the project to search. "
                        "Leave blank to use the configured workspace."
                    ),
                    "ui:widget": "path",
                    "ui:browseHint": "project",
                },
            },
            "required": ["query"],
        },
        executor=_exec_rag_query,
        profiles=("developer", "author"),
    ),
    "author.generate": CommandSpec(
        name="author.generate",
        title="Generate templates",
        domain="author",
        description="Render help / project-doc templates for a feature from its source files.",
        args_schema={
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "title": "Feature name",
                    "minLength": 1,
                    "description": "Must exist in the manifest at <help_dir>/features.yaml.",
                    # The Commands-page form fetches this URL when the
                    # modal opens (with `{help_dir}` replaced by the
                    # sibling field's current value) and renders a
                    # datalist of feature names.
                    "ui:choicesUrl": "/api/author/features?help_dir={help_dir}",
                },
                "help_dir": {
                    "type": "string",
                    "title": ".help/ path",
                    "default": ".help",
                    "ui:widget": "path",
                    # Picker shows a "✓ has manifest" badge next to
                    # dirs containing `features.yaml` so users don't
                    # accidentally pick a Jinja templates dir.
                    "ui:browseHint": "help",
                },
                "project_root": {
                    "type": "string",
                    "title": "Project root",
                    "default": ".",
                    "ui:widget": "path",
                    "ui:browseHint": "project",
                },
                "all_kinds": {
                    "type": "boolean",
                    "title": "All kinds (.help + docs/)",
                    "default": False,
                },
                "overwrite": {
                    "type": "boolean",
                    "title": "Overwrite existing / manual",
                    "default": False,
                },
            },
            "required": ["feature"],
        },
        executor=_exec_author_generate,
        profiles=("developer", "author"),
    ),
}


# ---------------------------------------------------------------------------
# RAG: corpus-info — owned by attune-author since Phase D1 of the
# architecture-realignment spec. Importing the orchestration command
# module triggers registration; we mirror it into this gui registry
# so /api/commands and the job runner stay unchanged.
# ---------------------------------------------------------------------------

import attune_author.orchestration.commands.rag  # noqa: F401, E402

COMMANDS["rag.corpus-info"] = _proxy_command("rag.corpus-info")


# ---------------------------------------------------------------------------
# author.* commands now live in attune_author.orchestration.commands.author
# (Phase D2 of the architecture-realignment spec). Importing the module
# triggers registration; the gui mirrors each spec via _proxy_command or
# _author_proxy depending on whether the command needs workspace
# pre-resolution and / or post-dispatch pipeline-cache invalidation.
# ---------------------------------------------------------------------------

import attune_author.orchestration.commands.author  # noqa: F401, E402

COMMANDS["author.init"] = _proxy_command("author.init")


COMMANDS["author.status"] = _author_proxy("author.status", pre_resolve_workspace=True)


COMMANDS["author.maintain"] = _author_proxy(
    "author.maintain", pre_resolve_workspace=True, invalidate_after=True
)


COMMANDS["author.lookup"] = _proxy_command("author.lookup")


# ---------------------------------------------------------------------------
# help.* commands now live in attune_author.orchestration.commands.help
# (Phase D3 of the architecture-realignment spec). None of the three
# need workspace pre-resolution or post-dispatch invalidation, so plain
# _proxy_command is sufficient.
# ---------------------------------------------------------------------------

import attune_author.orchestration.commands.help  # noqa: F401, E402

COMMANDS["help.lookup"] = _proxy_command("help.lookup")
COMMANDS["help.search"] = _proxy_command("help.search")
COMMANDS["help.list"] = _proxy_command("help.list")


COMMANDS["author.regen"] = _author_proxy(
    "author.regen", pre_resolve_workspace=True, invalidate_after=True
)


COMMANDS["author.setup"] = _author_proxy(
    "author.setup", pre_resolve_workspace=True, invalidate_after=True
)


def get_command(name: str) -> CommandSpec | None:
    """Return the CommandSpec for ``name``, or None if it isn't registered."""
    return COMMANDS.get(name)


def list_commands(profile: str | None = None) -> list[dict[str, Any]]:
    """Return registered commands as JSON-serializable dicts.

    If ``profile`` is given, only commands whose ``profiles`` tuple includes
    it are returned. ``None`` returns every command.
    """
    return [
        {
            "name": c.name,
            "title": c.title,
            "domain": c.domain,
            "description": c.description,
            "args_schema": c.args_schema,
            "cancellable": c.cancellable,
        }
        for c in COMMANDS.values()
        if profile is None or profile in c.profiles
    ]
