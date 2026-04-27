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

    Accepts either a single ``project_path`` convenience key or the legacy
    ``project_root`` / ``help_dir`` pair.  ``project_path`` wins when set.
    Relative paths are rejected with a clear error.
    """
    project_path_raw = str(args.get("project_path", "")).strip()
    if project_path_raw:
        _require_absolute("project_path", project_path_raw)
        project_root = Path(project_path_raw).expanduser().resolve()
        help_dir = project_root / ".help"
    else:
        help_dir_raw = str(args.get("help_dir", "")).strip() or ".help"
        project_root_raw = str(args.get("project_root", "")).strip() or "."
        if project_root_raw != ".":
            _require_absolute("project_root", project_root_raw)
        if help_dir_raw != ".help":
            _require_absolute("help_dir", help_dir_raw)
        help_dir = Path(help_dir_raw).expanduser().resolve()
        project_root = Path(project_root_raw).expanduser().resolve()
    return project_root, help_dir


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

    from attune_gui.routes.rag import _get_pipeline  # noqa: PLC0415 — reuse the cached pipeline

    pipeline = _get_pipeline()

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
                },
                "project_root": {
                    "type": "string",
                    "title": "Project root",
                    "default": ".",
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

    pipeline = _get_pipeline()
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
    args_schema={"type": "object", "properties": {}},
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
            "project_path": {"type": "string", "title": "Project path", "default": ""},
            "help_dir": {
                "type": "string",
                "title": ".help/ path (overrides project_path)",
                "default": "",
            },
            "project_root": {
                "type": "string",
                "title": "Project root (overrides project_path)",
                "default": "",
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
    from attune_author.maintenance import run_maintenance  # noqa: PLC0415

    project_root, help_dir = _resolve_project_paths(args)
    dry_run = bool(args.get("dry_run", False))
    features_raw = str(args.get("features", "")).strip()
    features = [f.strip() for f in features_raw.split(",") if f.strip()] or None

    label = "Dry-run check" if dry_run else "Regenerating stale templates"
    ctx.log(f"{label} in {help_dir}…")
    result = await asyncio.to_thread(run_maintenance, help_dir, project_root, features, dry_run)

    total = result.staleness.stale_count + result.staleness.current_count
    ctx.log(f"Stale: {result.staleness.stale_count} / {total}")
    if not dry_run:
        ctx.log(f"Regenerated: {len(result.regenerated)}, failed: {len(result.failed)}")

    return {
        "stale_count": result.staleness.stale_count,
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
            "project_path": {"type": "string", "title": "Project path", "default": ""},
            "help_dir": {
                "type": "string",
                "title": ".help/ path (overrides project_path)",
                "default": "",
            },
            "project_root": {
                "type": "string",
                "title": "Project root (overrides project_path)",
                "default": "",
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
            "help_dir": {"type": "string", "title": ".help/ path", "default": ".help"},
        },
        "required": ["query"],
    },
    executor=_exec_author_lookup,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# AI: health-check
# ---------------------------------------------------------------------------


async def _exec_ai_health_check(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.orchestrated_health_check import (
        OrchestratedHealthCheckWorkflow,
    )  # noqa: PLC0415

    project_root = str(Path(args.get("project_root", ".")).resolve())
    ctx.log(f"Running health check on {project_root}…")

    workflow = OrchestratedHealthCheckWorkflow()
    result = await workflow.execute(project_root=project_root)
    ctx.log(
        f"Grade: {getattr(result, 'grade', '?')}  Score: {getattr(result, 'overall_health_score', '?')}"
    )

    return {
        "success": getattr(result, "success", False),
        "health_score": getattr(result, "overall_health_score", 0),
        "grade": getattr(result, "grade", "unknown"),
        "issues": getattr(result, "issues", []),
        "recommendations": getattr(result, "recommendations", []),
    }


COMMANDS["ai.health-check"] = CommandSpec(
    name="ai.health-check",
    title="Health check",
    domain="ai",
    description="Run an orchestrated project health check — scores code quality, test coverage, security, and docs.",
    args_schema={
        "type": "object",
        "properties": {
            "project_root": {
                "type": "string",
                "title": "Project root",
                "default": ".",
                "description": "Root of the project to analyse.",
            },
        },
    },
    executor=_exec_ai_health_check,
)


# ---------------------------------------------------------------------------
# AI: code-review
# ---------------------------------------------------------------------------


async def _exec_ai_code_review(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.code_review import CodeReviewWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    ctx.log(f"Running code review on {path}…")

    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path=path)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    feedback = output.get("feedback") or (raw if isinstance(raw, str) else None)
    ctx.log(f"Review complete. Score: {output.get('quality_score', '?')}")
    return {
        "success": result.success,
        "feedback": feedback,
        "score": output.get("quality_score"),
        "cost": cost,
    }


COMMANDS["ai.code-review"] = CommandSpec(
    name="ai.code-review",
    title="Code review",
    domain="ai",
    description="Comprehensive code quality analysis via AI subagents. Provide a file or directory path.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to review.",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_code_review,
)


# ---------------------------------------------------------------------------
# AI: security-audit
# ---------------------------------------------------------------------------


async def _exec_ai_security_audit(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.security_audit import SecurityAuditWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    depth = args.get("depth", "standard")
    ctx.log(f"Running security audit on {path} (depth={depth})…")

    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(path=path, depth=depth)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    findings = getattr(result, "findings", None) or output.get("findings", [])
    summary = output.get("summary") or (raw if isinstance(raw, str) else None)
    ctx.log(f"Audit complete. {len(findings)} finding(s)")
    return {
        "success": result.success,
        "findings": findings,
        "summary": summary,
        "cost": cost,
    }


COMMANDS["ai.security-audit"] = CommandSpec(
    name="ai.security-audit",
    title="Security audit",
    domain="ai",
    description="AI-powered security audit: injection, secrets, auth issues, path traversal. Provide a path.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to audit.",
            },
            "depth": {
                "type": "string",
                "title": "Depth",
                "default": "standard",
                "description": "quick | standard | deep",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_security_audit,
)


# ---------------------------------------------------------------------------
# AI: memory-recall
# ---------------------------------------------------------------------------


async def _exec_ai_memory_recall(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune.memory.personal import PersonalMemory  # noqa: PLC0415

    query = args["query"]
    k = int(args.get("k", 3))
    ctx.log(f"Searching personal memory for {query!r} (k={k})…")

    pm = PersonalMemory()
    hits = await asyncio.to_thread(pm.query, query, k=k)
    ctx.log(f"Found {len(hits)} hit(s)")

    return {"query": query, "k": k, "count": len(hits), "results": hits}


COMMANDS["ai.memory-recall"] = CommandSpec(
    name="ai.memory-recall",
    title="Memory recall",
    domain="ai",
    description="Search personal cross-session memory with a natural-language query.",
    args_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "title": "Query",
                "minLength": 1,
                "description": "What to search for in personal memory.",
            },
            "k": {
                "type": "integer",
                "title": "k (top results)",
                "default": 3,
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query"],
    },
    executor=_exec_ai_memory_recall,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# AI: memory-capture
# ---------------------------------------------------------------------------


async def _exec_ai_memory_capture(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from attune.memory.personal import PersonalMemory  # noqa: PLC0415

    topic = args["topic"]
    content = args["content"]
    kind = args.get("kind", "decision")
    ctx.log(f"Capturing memory: topic={topic!r} kind={kind}…")

    pm = PersonalMemory()
    dest = await asyncio.to_thread(pm.capture, topic, content, kind=kind)
    ctx.log(f"Saved to {dest}")

    return {"success": True, "topic": topic, "kind": kind, "path": str(dest)}


COMMANDS["ai.memory-capture"] = CommandSpec(
    name="ai.memory-capture",
    title="Memory capture",
    domain="ai",
    description="Save a decision, pattern, or note to personal cross-session memory.",
    args_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "title": "Topic",
                "minLength": 1,
                "description": "Short slug identifying the memory (e.g. 'db-migration-approach').",
            },
            "content": {
                "type": "string",
                "title": "Content",
                "minLength": 1,
                "ui:widget": "textarea",
                "description": "The memory content to store.",
            },
            "kind": {
                "type": "string",
                "title": "Kind",
                "default": "decision",
                "description": "decision | pattern | troubleshooting | reference",
            },
        },
        "required": ["topic", "content"],
    },
    executor=_exec_ai_memory_capture,
    cancellable=False,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# AI: deep-review
# ---------------------------------------------------------------------------


async def _exec_ai_deep_review(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    focus = args.get("focus") or None
    ctx.log(f"Running deep review on {path}…")

    workflow = DeepReviewAgentSDKWorkflow()
    kwargs: dict[str, Any] = {"path": path}
    if focus:
        kwargs["focus"] = focus
    result = await workflow.execute(**kwargs)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    ctx.log("Deep review complete.")
    return {
        "success": result.success,
        "feedback": output.get("feedback") or (raw if isinstance(raw, str) else None),
        "issues": output.get("issues", []),
        "cost": cost,
    }


COMMANDS["ai.deep-review"] = CommandSpec(
    name="ai.deep-review",
    title="Deep review",
    domain="ai",
    description="Multi-pass deep code review via AI subagents — more thorough than a standard review.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to review.",
            },
            "focus": {
                "type": "string",
                "title": "Focus area",
                "default": "",
                "description": "Optional: narrow the review to a specific concern (e.g. 'error handling').",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_deep_review,
)


# ---------------------------------------------------------------------------
# AI: code-quality
# ---------------------------------------------------------------------------


async def _exec_ai_code_quality(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.bug_predict import BugPredictionWorkflow  # noqa: PLC0415
    from attune.workflows.code_review import CodeReviewWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    ctx.log(f"Running code quality analysis on {path} (review + bug prediction in parallel)…")

    review_result, bugs_result = await asyncio.gather(
        CodeReviewWorkflow().execute(path=path),
        BugPredictionWorkflow().execute(path=path),
        return_exceptions=True,
    )

    review_out: dict[str, Any] = {}
    bugs_out: dict[str, Any] = {}

    if isinstance(review_result, Exception):
        ctx.log(f"Code review error: {review_result}")
    else:
        raw = review_result.final_output
        review_out = (
            raw if isinstance(raw, dict) else {"feedback": raw if isinstance(raw, str) else None}
        )

    if isinstance(bugs_result, Exception):
        ctx.log(f"Bug prediction error: {bugs_result}")
    else:
        raw = bugs_result.final_output
        bugs_out = raw if isinstance(raw, dict) else {}

    total_cost = None
    costs = [
        r.cost_report.total_cost
        for r in [review_result, bugs_result]
        if not isinstance(r, Exception) and hasattr(r, "cost_report") and r.cost_report
    ]
    if costs:
        total_cost = sum(costs)

    ctx.log("Code quality analysis complete.")
    return {
        "success": not (
            isinstance(review_result, Exception) and isinstance(bugs_result, Exception)
        ),
        "review": review_out,
        "bug_prediction": bugs_out,
        "total_cost": total_cost,
    }


COMMANDS["ai.code-quality"] = CommandSpec(
    name="ai.code-quality",
    title="Code quality",
    domain="ai",
    description="Code review + bug prediction in parallel — a combined quality signal for a file or directory.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to analyse.",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_code_quality,
)


# ---------------------------------------------------------------------------
# AI: bug-predict
# ---------------------------------------------------------------------------


async def _exec_ai_bug_predict(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.bug_predict import BugPredictionWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    ctx.log(f"Running bug prediction on {path}…")

    workflow = BugPredictionWorkflow()
    result = await workflow.execute(path=path)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    predictions = output.get("predictions") or output.get("bugs", [])
    ctx.log(f"Bug prediction complete. {len(predictions)} prediction(s).")
    return {
        "success": result.success,
        "predictions": predictions,
        "risk_score": output.get("risk_score"),
        "recommendations": output.get("recommendations", []),
        "cost": cost,
    }


COMMANDS["ai.bug-predict"] = CommandSpec(
    name="ai.bug-predict",
    title="Bug prediction",
    domain="ai",
    description="Predict likely bug locations using pattern analysis and AI reasoning.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to analyse.",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_bug_predict,
)


# ---------------------------------------------------------------------------
# AI: smart-test
# ---------------------------------------------------------------------------


async def _exec_ai_smart_test(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.test_gen.workflow import TestGenerationWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    depth = args.get("depth", "standard")
    ctx.log(f"Generating tests for {path} (depth={depth})…")

    workflow = TestGenerationWorkflow()
    result = await workflow.execute(path=path, depth=depth)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    ctx.log("Test generation complete.")
    return {
        "success": result.success,
        "tests_generated": output.get("tests_generated", []),
        "coverage": output.get("coverage"),
        "summary": output.get("summary") or (raw if isinstance(raw, str) else None),
        "cost": cost,
    }


COMMANDS["ai.smart-test"] = CommandSpec(
    name="ai.smart-test",
    title="Smart test",
    domain="ai",
    description="Find test gaps and generate tests for uncovered code paths.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to generate tests for.",
            },
            "depth": {
                "type": "string",
                "title": "Depth",
                "default": "standard",
                "description": "quick | standard | deep",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_smart_test,
)


# ---------------------------------------------------------------------------
# AI: fix-test
# ---------------------------------------------------------------------------


async def _exec_ai_fix_test(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.test_maintenance import TestMaintenanceWorkflow  # noqa: PLC0415

    project_root = str(Path(args.get("project_root", ".")).resolve())
    mode = args.get("mode", "analyze")
    max_items = int(args.get("max_items", 20))
    dry_run = bool(args.get("dry_run", False))
    ctx.log(f"Running test maintenance (mode={mode}, max_items={max_items}, dry_run={dry_run})…")

    workflow = TestMaintenanceWorkflow(project_root)
    result = await workflow.run(
        {
            "mode": mode,
            "max_items": max_items,
            "dry_run": dry_run,
        }
    )

    ctx.log("Test maintenance complete.")
    return result if isinstance(result, dict) else {"output": str(result)}


COMMANDS["ai.fix-test"] = CommandSpec(
    name="ai.fix-test",
    title="Fix tests",
    domain="ai",
    description="Auto-diagnose and fix failing tests. Use 'analyze' mode first to preview changes.",
    args_schema={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "title": "Mode",
                "default": "analyze",
                "description": "analyze | execute | auto | report",
            },
            "max_items": {
                "type": "integer",
                "title": "Max items",
                "default": 20,
                "minimum": 1,
                "maximum": 100,
            },
            "dry_run": {
                "type": "boolean",
                "title": "Dry run",
                "default": False,
            },
            "project_root": {
                "type": "string",
                "title": "Project root",
                "default": ".",
                "description": "Root of the project containing the tests.",
            },
        },
    },
    executor=_exec_ai_fix_test,
)


# ---------------------------------------------------------------------------
# AI: refactor
# ---------------------------------------------------------------------------


async def _exec_ai_refactor(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.refactor_plan import RefactorPlanWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    goal = args.get("goal") or None
    ctx.log(f"Running refactor planning on {path}…")

    workflow = RefactorPlanWorkflow()
    kwargs: dict[str, Any] = {"path": path}
    if goal:
        kwargs["goal"] = goal
    result = await workflow.execute(**kwargs)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    ctx.log("Refactor planning complete.")
    return {
        "success": result.success,
        "plan": output.get("plan") or (raw if isinstance(raw, str) else None),
        "debt_items": output.get("debt_items", []),
        "priority_order": output.get("priority_order", []),
        "cost": cost,
    }


COMMANDS["ai.refactor"] = CommandSpec(
    name="ai.refactor",
    title="Refactor plan",
    domain="ai",
    description="Analyse technical debt and produce a prioritised refactoring roadmap.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to analyse.",
            },
            "goal": {
                "type": "string",
                "title": "Goal",
                "default": "",
                "description": "Optional: describe what you're trying to achieve (e.g. 'reduce complexity').",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_refactor,
)


# ---------------------------------------------------------------------------
# AI: doc-gen
# ---------------------------------------------------------------------------


async def _exec_ai_doc_gen(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.document_gen.workflow import DocumentGenerationWorkflow  # noqa: PLC0415

    path = str(Path(args["path"]).resolve())
    ctx.log(f"Generating documentation for {path}…")

    workflow = DocumentGenerationWorkflow()
    result = await workflow.execute(path=path)

    cost = None
    if hasattr(result, "cost_report") and result.cost_report:
        cost = result.cost_report.total_cost

    raw = result.final_output
    output = raw if isinstance(raw, dict) else {}
    ctx.log("Documentation generation complete.")
    return {
        "success": result.success,
        "docs": output.get("docs") or (raw if isinstance(raw, str) else None),
        "files_documented": output.get("files_documented", []),
        "cost": cost,
    }


COMMANDS["ai.doc-gen"] = CommandSpec(
    name="ai.doc-gen",
    title="Doc gen",
    domain="ai",
    description="Generate documentation from source code using AI subagents.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "minLength": 1,
                "description": "File or directory to document.",
            },
        },
        "required": ["path"],
    },
    executor=_exec_ai_doc_gen,
    profiles=("developer", "author"),
)


# ---------------------------------------------------------------------------
# AI: release
# ---------------------------------------------------------------------------


async def _exec_ai_release(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    from pathlib import Path  # noqa: PLC0415

    from attune.workflows.orchestrated_release_prep import (
        OrchestratedReleasePrepWorkflow,
    )  # noqa: PLC0415

    path = str(Path(args.get("path", ".")).resolve())
    ctx.log(f"Running release prep check on {path}…")

    workflow = OrchestratedReleasePrepWorkflow()
    result = await workflow.execute(path=path)

    ctx.log(f"Release prep complete. Approved: {result.approved}, Blockers: {len(result.blockers)}")
    return result.to_dict()


COMMANDS["ai.release"] = CommandSpec(
    name="ai.release",
    title="Release prep",
    domain="ai",
    description="Run pre-release checks: security, test coverage, code quality, docs readiness.",
    args_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "title": "Path",
                "default": ".",
                "description": "Root of the project to check.",
            },
        },
    },
    executor=_exec_ai_release,
)


# ---------------------------------------------------------------------------
# AI: bulk
# ---------------------------------------------------------------------------


async def _exec_ai_bulk(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    import uuid  # noqa: PLC0415

    from attune.workflows.batch_processing import (
        BatchProcessingWorkflow,
        BatchRequest,
    )  # noqa: PLC0415

    task_type = args["task_type"]
    paths_raw = str(args["paths"])
    model_tier = args.get("model_tier", "capable")

    paths = [p.strip() for p in paths_raw.splitlines() if p.strip()]
    if not paths:
        raise ValueError("At least one path is required.")

    requests = [
        BatchRequest(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            input_data={"path": p},
            model_tier=model_tier,
        )
        for p in paths
    ]
    ctx.log(f"Submitting {len(requests)} '{task_type}' batch request(s) via Anthropic Batch API…")

    workflow = BatchProcessingWorkflow()
    results = await workflow.execute_batch(requests)

    successful = sum(1 for r in results if r.success)
    ctx.log(f"Batch complete: {successful}/{len(results)} successful")
    return {
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": [
            {"task_id": r.task_id, "success": r.success, "output": r.output, "error": r.error}
            for r in results
        ],
    }


COMMANDS["ai.bulk"] = CommandSpec(
    name="ai.bulk",
    title="Bulk process",
    domain="ai",
    description="Run a workflow on many paths via Anthropic Batch API (50% cost saving, async, up to 24h).",
    args_schema={
        "type": "object",
        "properties": {
            "task_type": {
                "type": "string",
                "title": "Task type",
                "minLength": 1,
                "description": "Workflow to run on each path (e.g. code_review, security_audit).",
            },
            "paths": {
                "type": "string",
                "title": "Paths (one per line)",
                "minLength": 1,
                "ui:widget": "textarea",
                "description": "One file or directory path per line.",
            },
            "model_tier": {
                "type": "string",
                "title": "Model tier",
                "default": "capable",
                "description": "cheap | capable | premium",
            },
        },
        "required": ["task_type", "paths"],
    },
    executor=_exec_ai_bulk,
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
            },
        },
    },
    executor=_exec_help_list,
    cancellable=False,
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
