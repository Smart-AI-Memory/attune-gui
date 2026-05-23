"""MCP tool handlers — Phase 2.

Each tool is an async function that takes the argument dict the MCP
client sent and returns a JSON-serializable dict. Handlers go through
the same internal helpers the FastAPI routes use (``_specs_roots``,
``_scan_feature``, ``get_store()``…) — they don't reach across to the
HTTP layer.

Phase 2 ships five read-mostly tools per
``docs/specs/mcp-server-scope/decisions.md``:

- :func:`gui_list_specs` — federated spec listing
- :func:`gui_get_spec` — phase-file contents for one spec
- :func:`gui_get_spec_status` — the ``**Status**:`` line value
- :func:`gui_list_living_docs` — doc registry
- :func:`gui_get_living_doc` — one living-doc's file content
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from attune_gui.living_docs_store import get_store
from attune_gui.routes.cowork_specs import (
    _PHASE_FILES,
    _PHASE_LABELS,
    _PHASE_NAMES,
    _SLUG_RE,
    _project_for,
    _read_status,
    _scan_feature,
    _specs_roots,
)

_PHASE_FILE_BY_NAME = dict(zip(_PHASE_NAMES, _PHASE_FILES, strict=False))


# ---------------------------------------------------------------------------
# Schemas — what the MCP client sees
# ---------------------------------------------------------------------------


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "gui_list_specs": {
        "description": (
            "List all feature specs across configured roots (federated). Each "
            "spec is tagged with project, root, phase, and status. Mirrors the "
            "Specs page in the attune-gui dashboard."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    "gui_get_spec": {
        "description": (
            "Return the phase-file contents (requirements.md, design.md, "
            "tasks.md) for one spec. Use this to read what a spec actually "
            "says rather than just its metadata."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature": {
                    "type": "string",
                    "description": "Slug of the feature (the spec directory name).",
                },
                "root": {
                    "type": "string",
                    "description": (
                        "Optional absolute path of the specs root to "
                        "disambiguate when the same slug exists in multiple "
                        "roots. If omitted, the first match wins."
                    ),
                },
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
    },
    "gui_get_spec_status": {
        "description": (
            "Return the **Status** value from a spec's phase file (default: "
            "the most advanced phase). Cheap shortcut over gui_get_spec when "
            "you only need to check progress."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "phase": {
                    "type": "string",
                    "enum": list(_PHASE_NAMES),
                    "description": (
                        "Which phase to read. Defaults to the most advanced " "phase that exists."
                    ),
                },
                "root": {"type": "string"},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
    },
    "gui_list_living_docs": {
        "description": (
            "List entries in the living-docs registry — generated docs the "
            "workspace tracks, with status (current/stale/missing), persona, "
            "depth, and last-modified timestamp."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "persona": {
                    "type": "string",
                    "enum": ["end_user", "developer", "support", "author"],
                    "description": "Optional persona filter.",
                },
            },
            "additionalProperties": False,
        },
    },
    "gui_get_living_doc": {
        "description": (
            "Return the file content of one living-docs entry. Identified by "
            "`doc_id` in the form `<feature>/<depth>` (e.g. `sidecar/concept`)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "pattern": r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$",
                    "description": (
                        "`<feature>/<depth>` — the `id` field from " "gui_list_living_docs."
                    ),
                },
            },
            "required": ["doc_id"],
            "additionalProperties": False,
        },
    },
    "gui_set_spec_status": {
        "description": (
            "Rewrite the `**Status**:` line in a spec's phase file. The only "
            "write tool — use sparingly. Mirrors the validation of the existing "
            "PUT /api/cowork/specs/{feature}/{phase}/status route."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "phase": {
                    "type": "string",
                    "enum": list(_PHASE_NAMES),
                },
                "status": {
                    "type": "string",
                    "description": (
                        "One of: draft, in-review, approved, complete, " "completed, done."
                    ),
                },
                "root": {
                    "type": "string",
                    "description": (
                        "Optional absolute path of the specs root to "
                        "disambiguate when the same slug exists in multiple "
                        "roots. If omitted, the first match wins."
                    ),
                },
            },
            "required": ["feature", "phase", "status"],
            "additionalProperties": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _err(msg: str) -> dict[str, Any]:
    return {"success": False, "error": msg}


def _validate_slug(value: str, field: str = "feature") -> str | None:
    """Return an error message if ``value`` isn't a valid slug, else None."""
    if not isinstance(value, str) or not _SLUG_RE.match(value):
        return f"Invalid {field}: {value!r} (must match {_SLUG_RE.pattern})"
    return None


def _resolve_feature_dir(feature: str, root: str | None) -> tuple[Path, str] | dict[str, Any]:
    """Find the spec directory for ``feature``.

    If ``root`` is supplied, search only that root. Otherwise scan all
    configured roots and return the first match.

    Returns ``(feature_dir, project_label)`` on success, or an error envelope.
    """
    roots = _specs_roots()
    if not roots:
        return _err("No specs roots configured.")
    if root:
        target = Path(root).expanduser().resolve()
        roots = [r for r in roots if r.resolve() == target]
        if not roots:
            return _err(f"Specs root not configured: {root!r}")
    for r in roots:
        candidate = r / feature
        if candidate.is_dir():
            return candidate, _project_for(r)
    return _err(f"Spec {feature!r} not found in any configured root.")


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def gui_list_specs(_args: dict[str, Any]) -> dict[str, Any]:
    roots = _specs_roots()
    if not roots:
        return {"success": True, "specs": [], "specs_roots": []}

    specs: list[dict[str, Any]] = []
    seen: dict[str, str] = {}  # feature -> project of first occurrence
    for r in roots:
        project = _project_for(r)
        for child in sorted(r.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            spec = _scan_feature(child)
            spec["project"] = project
            spec["root"] = str(r)
            if child.name in seen and seen[child.name] != project:
                spec["collision"] = True
            else:
                seen.setdefault(child.name, project)
            specs.append(spec)
    return {
        "success": True,
        "specs": specs,
        "specs_roots": [{"path": str(r), "project": _project_for(r)} for r in roots],
    }


async def gui_get_spec(args: dict[str, Any]) -> dict[str, Any]:
    feature = args.get("feature", "")
    if (msg := _validate_slug(feature)) is not None:
        return _err(msg)
    root = args.get("root")

    found = _resolve_feature_dir(feature, root)
    if isinstance(found, dict):  # error envelope
        return found
    feat_dir, project = found

    phases: dict[str, dict[str, Any]] = {}
    for phase_name, file_name in zip(_PHASE_NAMES, _PHASE_FILES, strict=False):
        phase_path = feat_dir / file_name
        if not phase_path.is_file():
            continue
        try:
            content = phase_path.read_text(encoding="utf-8")
        except OSError as exc:
            return _err(f"Could not read {file_name}: {exc}")
        phases[phase_name] = {
            "label": _PHASE_LABELS[file_name],
            "file": file_name,
            "path": str(phase_path),
            "status": _read_status(phase_path),
            "content": content,
        }
    return {
        "success": True,
        "feature": feature,
        "project": project,
        "root": str(feat_dir.parent),
        "phases": phases,
    }


async def gui_get_spec_status(args: dict[str, Any]) -> dict[str, Any]:
    feature = args.get("feature", "")
    if (msg := _validate_slug(feature)) is not None:
        return _err(msg)
    phase = args.get("phase")
    root = args.get("root")

    found = _resolve_feature_dir(feature, root)
    if isinstance(found, dict):
        return found
    feat_dir, _project = found

    if phase is not None:
        if phase not in _PHASE_FILE_BY_NAME:
            return _err(f"Invalid phase: {phase!r} (valid: {', '.join(_PHASE_NAMES)})")
        target = feat_dir / _PHASE_FILE_BY_NAME[phase]
        if not target.is_file():
            return _err(f"Phase file does not exist: {target.name}")
        return {
            "success": True,
            "feature": feature,
            "phase": phase,
            "file": target.name,
            "status": _read_status(target),
        }

    # No phase requested — use most advanced
    present = [name for name in _PHASE_FILES if (feat_dir / name).is_file()]
    if not present:
        return _err(f"Spec {feature!r} has no phase files yet.")
    most_advanced = present[-1]
    return {
        "success": True,
        "feature": feature,
        "phase": _PHASE_NAMES[_PHASE_FILES.index(most_advanced)],
        "file": most_advanced,
        "status": _read_status(feat_dir / most_advanced),
    }


async def gui_list_living_docs(args: dict[str, Any]) -> dict[str, Any]:
    persona = args.get("persona")
    if persona is not None and not isinstance(persona, str):
        return _err(f"Invalid persona: {persona!r}")
    docs = await get_store().list_docs(persona=persona)
    return {"success": True, "docs": docs}


_DOC_ID_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def _doc_id_is_safe(doc_id: str) -> bool:
    """Reject anything that isn't ``<safe-token>/<safe-token>`` with no traversal."""
    if not _DOC_ID_RE.match(doc_id):
        return False
    return all(segment not in ("", ".", "..") for segment in doc_id.split("/"))


async def gui_get_living_doc(args: dict[str, Any]) -> dict[str, Any]:
    # Lazy workspace import so test monkeypatches on ``attune_gui.workspace.get_workspace``
    # land before we resolve the function reference. (Module-level import would bind once
    # at import time and ignore later patches.)
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    doc_id = args.get("doc_id", "")
    if not isinstance(doc_id, str) or not _doc_id_is_safe(doc_id):
        return _err(f"Invalid doc_id: {doc_id!r} (expected '<feature>/<depth>')")

    docs = await get_store().list_docs()
    match = next((d for d in docs if d["id"] == doc_id), None)
    if match is None:
        return _err(f"Living-doc not found: {doc_id!r}")
    if match.get("path") is None:
        return _err(f"Living-doc {doc_id!r} has no file on disk (status={match.get('status')!r}).")

    workspace = get_workspace() or Path.cwd()
    abs_path = (workspace / match["path"]).resolve()
    # Path-traversal guard: result must stay under the workspace
    try:
        abs_path.relative_to(workspace.resolve())
    except ValueError:
        return _err(f"Living-doc path escapes workspace: {match['path']!r}")
    if not abs_path.is_file():
        return _err(f"Living-doc file missing on disk: {abs_path}")

    try:
        content = abs_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _err(f"Could not read {abs_path}: {exc}")

    return {
        "success": True,
        "doc_id": doc_id,
        "feature": match["feature"],
        "depth": match["depth"],
        "persona": match["persona"],
        "status": match["status"],
        "path": match["path"],
        "last_modified": match.get("last_modified"),
        "content": content,
    }


async def gui_set_spec_status(args: dict[str, Any]) -> dict[str, Any]:
    # Lazy imports keep the writes-only deps (atomic_write, _VALID_STATUSES, the
    # status regexes) out of module-import time. Matches the gui_get_living_doc
    # workspace pattern above.
    from attune_gui._fs import atomic_write  # noqa: PLC0415
    from attune_gui.routes.cowork_specs import (  # noqa: PLC0415
        _STATUS_RE,
        _STATUS_VALUE_RE,
        _VALID_STATUSES,
    )

    feature = args.get("feature", "")
    if (msg := _validate_slug(feature)) is not None:
        return _err(msg)
    phase = args.get("phase", "")
    if phase not in _PHASE_FILE_BY_NAME:
        return _err(f"Invalid phase: {phase!r} (valid: {', '.join(_PHASE_NAMES)})")
    status = args.get("status", "")
    if not isinstance(status, str) or status not in _VALID_STATUSES:
        return _err(f"Invalid status: {status!r} (valid: {', '.join(_VALID_STATUSES)})")
    root = args.get("root")

    found = _resolve_feature_dir(feature, root)
    if isinstance(found, dict):
        return found
    feat_dir, project = found

    target = feat_dir / _PHASE_FILE_BY_NAME[phase]
    if not target.is_file():
        return _err(f"Phase file does not exist: {target.name}")

    try:
        original = target.read_text(encoding="utf-8")
    except OSError as exc:
        return _err(f"Read failed: {exc}")

    # Mirrors the PUT route's logic: substitute if a Status line exists,
    # insert near the top otherwise.
    if not _STATUS_VALUE_RE.search(original):
        lines = original.splitlines()
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        lines.insert(insert_at, f"\n**Status**: {status}\n")
        new_text = "\n".join(lines) + ("\n" if not original.endswith("\n") else "")
    else:
        new_text = _STATUS_RE.sub(f"**Status**: {status}", original, count=1)

    try:
        atomic_write(target, new_text)
    except OSError as exc:
        return _err(f"Write failed: {exc}")

    return {
        "success": True,
        "feature": feature,
        "project": project,
        "phase": phase,
        "file": target.name,
        "status": status,
        "path": str(target),
    }


# ---------------------------------------------------------------------------
# Public dispatch table
# ---------------------------------------------------------------------------


def get_dispatch() -> dict[str, Any]:
    """Tool-name → async handler. Imported by :mod:`.server`."""
    return {
        "gui_list_specs": gui_list_specs,
        "gui_get_spec": gui_get_spec,
        "gui_get_spec_status": gui_get_spec_status,
        "gui_list_living_docs": gui_list_living_docs,
        "gui_get_living_doc": gui_get_living_doc,
        "gui_set_spec_status": gui_set_spec_status,
    }
