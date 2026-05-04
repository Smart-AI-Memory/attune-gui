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


def _resolve_project_paths(args: dict[str, Any]) -> tuple[Path, Path]:
    """Return (project_root, help_dir) from args.

    Priority:
      1. ``project_path`` — convenience key, derives help_dir as <root>/.help
      2. ``project_root`` / ``help_dir`` legacy pair, when explicitly non-empty
      3. Configured workspace (from ~/.attune-gui/config.json)
    Raises ValueError when no path is provided and no workspace is configured.
    Relative paths are rejected with a clear error.
    """
    project_path_raw = str(args.get("project_path", "")).strip()
    if project_path_raw:
        _require_absolute("project_path", project_path_raw)
        project_root = Path(project_path_raw).expanduser().resolve()
        return project_root, project_root / ".help"

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
        return ws, ws / ".help"

    project_root_raw = project_root_raw or "."
    help_dir_raw = help_dir_raw or ".help"
    if project_root_raw != ".":
        _require_absolute("project_root", project_root_raw)
    if help_dir_raw != ".help":
        _require_absolute("help_dir", help_dir_raw)
    return (
        Path(project_root_raw).expanduser().resolve(),
        Path(help_dir_raw).expanduser().resolve(),
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

    from attune_gui.routes.rag import _get_pipeline  # noqa: PLC0415
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    project_path_raw = str(args.get("project_path", "")).strip()
    workspace = (
        Path(project_path_raw).expanduser().resolve() if project_path_raw else get_workspace()
    )
    pipeline = _get_pipeline(workspace)

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
    from pathlib import Path

    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415

    feature = args["feature"]
    help_dir = Path(args.get("help_dir", ".help")).resolve()
    project_root = Path(args.get("project_root", ".")).resolve()
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
        description="Run retrieval against the default attune-rag corpus and show hits + augmented prompt.",
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
                    "description": "Root of the project to search. Leave blank to use the configured workspace.",
                    "ui:widget": "path",
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
                },
                "help_dir": {
                    "type": "string",
                    "title": ".help/ path",
                    "default": ".help",
                    "ui:widget": "path",
                },
                "project_root": {
                    "type": "string",
                    "title": "Project root",
                    "default": ".",
                    "ui:widget": "path",
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
# RAG: corpus-info
# ---------------------------------------------------------------------------


async def _exec_rag_corpus_info(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune_gui.routes.rag import _get_pipeline  # noqa: PLC0415
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    project_path_raw = str(args.get("project_path", "")).strip()
    workspace = (
        Path(project_path_raw).expanduser().resolve() if project_path_raw else get_workspace()
    )
    pipeline = _get_pipeline(workspace)
    entries = await asyncio.to_thread(list, pipeline.corpus.entries())
    kinds = sorted({e.path.split("/")[0] for e in entries if "/" in e.path})
    ctx.log(f"{len(entries)} entries across {len(kinds)} kind(s)")
    return {
        "corpus_class": type(pipeline.corpus).__name__,
        "entry_count": len(entries),
        "kinds": kinds,
    }


COMMANDS["rag.corpus-info"] = CommandSpec(
    name="rag.corpus-info",
    title="Corpus info",
    domain="rag",
    description="Show entry count and category breakdown for the loaded attune-rag corpus.",
    args_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "title": "Project path",
                "default": "",
                "description": "Root of the project whose corpus to inspect. Leave blank to use the configured workspace.",
                "ui:widget": "path",
            },
        },
    },
    executor=_exec_rag_corpus_info,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: init
# ---------------------------------------------------------------------------


async def _exec_author_init(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune_author.bootstrap import proposals_to_manifest, scan_project  # noqa: PLC0415
    from attune_author.manifest import save_manifest  # noqa: PLC0415

    project_root = Path(args.get("project_root", ".")).resolve()
    help_dir = project_root / ".help"

    if (help_dir / "features.yaml").exists():
        ctx.log("Already initialised — skipping scan")
        return {
            "already_initialized": True,
            "manifest_path": str(help_dir / "features.yaml"),
        }

    ctx.log(f"Scanning {project_root} for features…")
    proposals = await asyncio.to_thread(scan_project, project_root)
    ctx.log(f"Discovered {len(proposals)} feature(s)")

    if not proposals:
        return {"discovered": 0, "message": "No features discovered in project."}

    manifest = proposals_to_manifest(proposals)
    manifest_path = await asyncio.to_thread(save_manifest, manifest, help_dir)
    ctx.log(f"Wrote manifest to {manifest_path}")

    return {
        "discovered": len(proposals),
        "manifest_path": str(manifest_path),
        "features": [{"name": p.name, "description": p.description} for p in proposals],
    }


COMMANDS["author.init"] = CommandSpec(
    name="author.init",
    title="Init .help/",
    domain="author",
    description="Scan the project and bootstrap a .help/features.yaml manifest.",
    args_schema={
        "type": "object",
        "properties": {
            "project_root": {
                "type": "string",
                "title": "Project root",
                "default": ".",
                "description": "Root of the project to scan.",
                "ui:widget": "path",
            },
        },
    },
    executor=_exec_author_init,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: status
# ---------------------------------------------------------------------------


async def _exec_author_status(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:

    from attune_author.maintenance import format_status_report  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415
    from attune_author.staleness import check_staleness  # noqa: PLC0415

    project_root, help_dir = _resolve_project_paths(args)

    ctx.log(f"Loading manifest from {help_dir}…")
    manifest = await asyncio.to_thread(load_manifest, help_dir)
    ctx.log(f"Checking staleness for {len(manifest.features)} feature(s)…")
    report = await asyncio.to_thread(check_staleness, manifest, help_dir, project_root, None)
    total = report.stale_count + report.current_count
    ctx.log(f"Stale: {report.stale_count} / {total}")

    return {
        "total": total,
        "stale": report.stale_count,
        "fresh": report.current_count,
        "report": format_status_report(report),
    }


COMMANDS["author.status"] = CommandSpec(
    name="author.status",
    title="Template status",
    domain="author",
    description="Report which help templates are stale vs. fresh.",
    args_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "title": "Project path",
                "default": "",
                "ui:widget": "path",
            },
            "help_dir": {
                "type": "string",
                "title": ".help/ path (overrides project_path)",
                "default": "",
                "ui:widget": "path",
            },
            "project_root": {
                "type": "string",
                "title": "Project root (overrides project_path)",
                "default": "",
                "ui:widget": "path",
            },
        },
    },
    executor=_exec_author_status,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: maintain
# ---------------------------------------------------------------------------


async def _exec_author_maintain(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    """Regenerate stale templates with per-feature progress.

    Mirrors ``attune_author.maintenance.run_maintenance`` but calls
    ``generate_feature_templates`` one feature at a time so we can emit a
    log line per feature and the UI doesn't appear stuck.
    """
    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.maintenance import MaintenanceResult  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415
    from attune_author.staleness import check_staleness  # noqa: PLC0415

    project_root, help_dir = _resolve_project_paths(args)
    dry_run = bool(args.get("dry_run", False))
    features_raw = str(args.get("features", "")).strip()
    features = [f.strip() for f in features_raw.split(",") if f.strip()] or None

    label = "Dry-run check" if dry_run else "Regenerating stale templates"
    ctx.log(f"{label} in {help_dir}…")

    manifest = await asyncio.to_thread(load_manifest, help_dir)
    report = await asyncio.to_thread(check_staleness, manifest, help_dir, project_root, features)
    result = MaintenanceResult(staleness=report)

    total = report.stale_count + report.current_count
    ctx.log(f"Stale: {report.stale_count} / {total}")

    if dry_run or report.stale_count == 0:
        return {
            "stale_count": report.stale_count,
            "total_count": total,
            "regenerated": [],
            "failed": [],
            "dry_run": dry_run,
        }

    stale_entries = [e for e in report.help_entries if e.is_stale]
    n_stale = len(stale_entries)
    for idx, entry in enumerate(stale_entries, start=1):
        feat = manifest.features.get(entry.feature)
        if feat is None:
            ctx.log(f"  [{idx}/{n_stale}] {entry.feature}: not in manifest — skip")
            continue

        try:
            gen = await asyncio.to_thread(
                generate_feature_templates,
                feature=feat,
                help_dir=help_dir,
                project_root=project_root,
            )
            result.regenerated.append(gen)
            ctx.log(f"  [{idx}/{n_stale}] {entry.feature}: {len(gen.templates)} template(s)")
        except (OSError, Exception) as exc:  # noqa: BLE001
            ctx.log(f"  [{idx}/{n_stale}] {entry.feature}: FAILED — {exc}")
            result.failed.append(entry.feature)

    ctx.log(f"Regenerated: {len(result.regenerated)}, failed: {len(result.failed)}")

    return {
        "stale_count": report.stale_count,
        "total_count": total,
        "regenerated": [r.feature for r in result.regenerated],
        "failed": result.failed,
        "dry_run": dry_run,
    }


COMMANDS["author.maintain"] = CommandSpec(
    name="author.maintain",
    title="Maintain templates",
    domain="author",
    description="Regenerate all stale help templates (or dry-run to preview what would change).",
    args_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "title": "Project path",
                "default": "",
                "ui:widget": "path",
            },
            "help_dir": {
                "type": "string",
                "title": ".help/ path (overrides project_path)",
                "default": "",
                "ui:widget": "path",
            },
            "project_root": {
                "type": "string",
                "title": "Project root (overrides project_path)",
                "default": "",
                "ui:widget": "path",
            },
            "features": {
                "type": "string",
                "title": "Features (comma-separated)",
                "default": "",
                "description": "Leave blank to check all features.",
            },
            "dry_run": {"type": "boolean", "title": "Dry run", "default": False},
        },
    },
    executor=_exec_author_maintain,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: lookup
# ---------------------------------------------------------------------------


async def _exec_author_lookup(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune_author.manifest import (
        is_safe_feature_name,
        load_manifest,
        resolve_topic,
    )  # noqa: PLC0415

    query = args["query"]
    depth = args.get("depth", "concept")
    help_dir = Path(args.get("help_dir", ".help")).resolve()

    ctx.log(f"Looking up {query!r} (depth={depth})…")
    manifest = await asyncio.to_thread(load_manifest, help_dir)
    feature_name = resolve_topic(query, manifest)

    if not feature_name:
        available = sorted(manifest.features)
        raise ValueError(f"No feature matches {query!r}. Available: {', '.join(available)}")

    if not is_safe_feature_name(feature_name):
        raise ValueError(f"Invalid feature name: {feature_name!r}")

    template_path = help_dir / "templates" / feature_name / f"{depth}.md"
    if not template_path.exists():
        raise ValueError(f"No {depth} template for '{feature_name}'. Run author.generate first.")

    content = template_path.read_text(encoding="utf-8")
    ctx.log(f"Loaded template for '{feature_name}' ({len(content)} chars)")

    return {"feature": feature_name, "depth": depth, "path": str(template_path), "content": content}


COMMANDS["author.lookup"] = CommandSpec(
    name="author.lookup",
    title="Lookup template",
    domain="author",
    description="Read a rendered help template for a feature by name or tag.",
    args_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "title": "Feature / tag",
                "minLength": 1,
                "description": "Feature name or tag to look up.",
            },
            "depth": {
                "type": "string",
                "title": "Depth",
                "default": "concept",
                "description": "concept | task | reference",
            },
            "help_dir": {
                "type": "string",
                "title": ".help/ path",
                "default": ".help",
                "ui:widget": "path",
            },
        },
        "required": ["query"],
    },
    executor=_exec_author_lookup,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Help: lookup
# ---------------------------------------------------------------------------


def _help_engine(template_dir: str | None, job_id: str):
    from pathlib import Path as _Path  # noqa: PLC0415

    from attune_help import HelpEngine  # noqa: PLC0415

    return HelpEngine(
        template_dir=_Path(template_dir).resolve() if template_dir else None,
        renderer="plain",
        user_id=job_id,
    )


async def _exec_help_lookup(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    topic = args["topic"]
    depth = args.get("depth", "concept")
    template_dir = args.get("template_dir") or None

    depth_steps = {"concept": 1, "task": 2, "reference": 3}
    steps = depth_steps.get(depth, 1)

    engine = _help_engine(template_dir, ctx.job_id)
    ctx.log(f"Looking up {topic!r} at depth={depth} ({steps} step(s))…")

    content = None
    for _ in range(steps):
        content = await asyncio.to_thread(engine.lookup, topic, suggest_on_miss=True)

    if content is None:
        raise ValueError(f"No help found for topic {topic!r}.")

    topics = await asyncio.to_thread(engine.list_topics)
    ctx.log(f"Retrieved from {engine.generated_dir}")
    return {
        "topic": topic,
        "depth": depth,
        "content": content,
        "template_dir": str(engine.generated_dir),
        "total_topics": len(topics),
    }


COMMANDS["help.lookup"] = CommandSpec(
    name="help.lookup",
    title="Help lookup",
    domain="help",
    description="Look up a help topic with progressive depth (concept → task → reference).",
    args_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "title": "Topic",
                "minLength": 1,
                "description": "Topic slug or feature name to look up.",
            },
            "depth": {
                "type": "string",
                "title": "Depth",
                "default": "concept",
                "description": "concept | task | reference",
            },
            "template_dir": {
                "type": "string",
                "title": "Template dir",
                "default": "",
                "description": "Path to .help/templates/ directory. Leave blank to use bundled templates.",
                "ui:widget": "path",
            },
        },
        "required": ["topic"],
    },
    executor=_exec_help_lookup,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Help: search
# ---------------------------------------------------------------------------


async def _exec_help_search(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    query = args["query"]
    limit = int(args.get("limit", 10))
    template_dir = args.get("template_dir") or None

    engine = _help_engine(template_dir, "search")
    ctx.log(f"Searching {query!r} (limit={limit})…")

    results = await asyncio.to_thread(engine.search, query, limit=limit)
    ctx.log(f"Found {len(results)} result(s)")
    return {
        "query": query,
        "results": results,
        "count": len(results),
        "template_dir": str(engine.generated_dir),
    }


COMMANDS["help.search"] = CommandSpec(
    name="help.search",
    title="Help search",
    domain="help",
    description="Fuzzy-search help topics by keyword across the template library.",
    args_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "title": "Query",
                "minLength": 1,
                "description": "Keyword or phrase to search for.",
            },
            "limit": {
                "type": "integer",
                "title": "Limit",
                "default": 10,
                "minimum": 1,
                "maximum": 50,
            },
            "template_dir": {
                "type": "string",
                "title": "Template dir",
                "default": "",
                "description": "Path to .help/templates/ directory. Leave blank to use bundled templates.",
                "ui:widget": "path",
            },
        },
        "required": ["query"],
    },
    executor=_exec_help_search,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Help: list
# ---------------------------------------------------------------------------


async def _exec_help_list(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    type_filter = args.get("type_filter") or None
    template_dir = args.get("template_dir") or None

    engine = _help_engine(template_dir, "list")
    ctx.log(f"Listing topics{f' (type={type_filter})' if type_filter else ''}…")

    topics = await asyncio.to_thread(engine.list_topics, type_filter=type_filter)
    ctx.log(f"{len(topics)} topic(s) found in {engine.generated_dir}")
    return {
        "topics": topics,
        "count": len(topics),
        "type_filter": type_filter,
        "template_dir": str(engine.generated_dir),
    }


COMMANDS["help.list"] = CommandSpec(
    name="help.list",
    title="List topics",
    domain="help",
    description="List all available help topics, optionally filtered by type (concepts, tasks, references).",
    args_schema={
        "type": "object",
        "properties": {
            "type_filter": {
                "type": "string",
                "title": "Type filter",
                "default": "",
                "description": "concepts | tasks | references | (blank for all)",
            },
            "template_dir": {
                "type": "string",
                "title": "Template dir",
                "default": "",
                "description": "Path to .help/templates/ directory. Leave blank to use bundled templates.",
                "ui:widget": "path",
            },
        },
    },
    executor=_exec_help_list,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: regen
# ---------------------------------------------------------------------------


async def _exec_author_regen(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415

    project_root, help_dir = _resolve_project_paths(args)
    feature_name = str(args.get("feature", "")).strip()
    overwrite = bool(args.get("overwrite", True))

    ctx.log(f"Loading manifest from {help_dir}…")
    manifest = await asyncio.to_thread(load_manifest, help_dir)

    if feature_name:
        if feature_name not in manifest.features:
            available = ", ".join(sorted(manifest.features)) or "(none)"
            raise ValueError(f"Feature {feature_name!r} not in manifest. Available: {available}")
        targets = [manifest.features[feature_name]]
    else:
        targets = list(manifest.features.values())

    ctx.log(f"Regenerating {len(targets)} feature(s)…")
    generated: list[dict[str, Any]] = []
    failed: list[str] = []
    for feat in targets:
        try:
            result = await asyncio.to_thread(
                generate_feature_templates,
                feature=feat,
                help_dir=help_dir,
                project_root=project_root,
                depths=None,
                overwrite=overwrite,
            )
            ctx.log(f"  {feat.name}: {len(result.templates)} template(s)")
            generated.append({"feature": feat.name, "templates": len(result.templates)})
        except Exception as exc:
            ctx.log(f"  {feat.name}: FAILED — {exc}")
            failed.append(feat.name)

    from attune_gui.routes import rag  # noqa: PLC0415

    rag.invalidate(project_root)
    ctx.log(f"Done — {len(generated)} generated, {len(failed)} failed")
    return {"generated": generated, "failed": failed}


COMMANDS["author.regen"] = CommandSpec(
    name="author.regen",
    title="Regenerate templates",
    domain="author",
    description="Regenerate help templates for one feature or all features in a project.",
    args_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "title": "Project path",
                "default": "",
                "description": "Root of the project. Leave blank to use the configured workspace.",
                "ui:widget": "path",
            },
            "feature": {
                "type": "string",
                "title": "Feature (leave blank for all)",
                "default": "",
                "description": "Feature name from the manifest. Leave blank to regenerate all.",
            },
            "overwrite": {
                "type": "boolean",
                "title": "Overwrite existing templates",
                "default": True,
            },
        },
    },
    executor=_exec_author_regen,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# Author: setup (init + generate all templates in one step)
# ---------------------------------------------------------------------------


async def _exec_author_setup(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune_author.bootstrap import proposals_to_manifest, scan_project  # noqa: PLC0415
    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest, save_manifest  # noqa: PLC0415

    project_root, help_dir = _resolve_project_paths(args)
    overwrite = bool(args.get("overwrite", False))

    manifest_path = help_dir / "features.yaml"
    if manifest_path.exists():
        ctx.log("Manifest exists — skipping init")
    else:
        ctx.log(f"Scanning {project_root} for features…")
        proposals = await asyncio.to_thread(scan_project, project_root)
        ctx.log(f"Discovered {len(proposals)} feature(s)")
        if not proposals:
            return {"discovered": 0, "message": "No features discovered in project."}
        manifest = proposals_to_manifest(proposals)
        await asyncio.to_thread(save_manifest, manifest, help_dir)
        ctx.log(f"Wrote manifest to {manifest_path}")

    manifest = await asyncio.to_thread(load_manifest, help_dir)
    features = list(manifest.features.values())
    ctx.log(f"Generating templates for {len(features)} feature(s)…")

    generated: list[dict[str, Any]] = []
    failed: list[str] = []
    for feat in features:
        try:
            result = await asyncio.to_thread(
                generate_feature_templates,
                feature=feat,
                help_dir=help_dir,
                project_root=project_root,
                depths=None,
                overwrite=overwrite,
            )
            ctx.log(f"  {feat.name}: {len(result.templates)} template(s)")
            generated.append({"feature": feat.name, "templates": len(result.templates)})
        except Exception as exc:
            ctx.log(f"  {feat.name}: FAILED — {exc}")
            failed.append(feat.name)

    from attune_gui.routes import rag  # noqa: PLC0415

    rag.invalidate(project_root)
    ctx.log(f"Done — {len(generated)} generated, {len(failed)} failed")
    return {
        "manifest_path": str(manifest_path),
        "features_total": len(features),
        "generated": generated,
        "failed": failed,
    }


COMMANDS["author.setup"] = CommandSpec(
    name="author.setup",
    title="Setup help",
    domain="author",
    description="Init .help/ (if needed) and generate all help templates for a project in one step.",
    args_schema={
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "title": "Project path",
                "default": "",
                "description": "Root of the project to set up help for. Leave blank to use the configured workspace.",
                "ui:widget": "path",
            },
            "overwrite": {
                "type": "boolean",
                "title": "Overwrite existing templates",
                "default": False,
            },
        },
    },
    executor=_exec_author_setup,
    profiles=("developer", "author"),
)


def get_command(name: str) -> CommandSpec | None:
    return COMMANDS.get(name)


def list_commands(profile: str | None = None) -> list[dict[str, Any]]:
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
