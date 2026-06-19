"""Template provenance + staleness for the editor (hash-regenerate-button).

Pure-Python read path: given a corpus + template rel-path, resolve the
feature the template was generated from, recompute the source hash, and
report whether the template is fresh / stale / unbound / sources-missing.

No network, no LLM — backs ``GET /api/corpus/<id>/template/provenance``.
The regenerate write path (which *does* call the LLM) lives in
``routes/editor_provenance.py`` and reuses :func:`regen_inputs` here.

See ``specs/hash-regenerate-button/design.md``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from attune_author.manifest import load_manifest
from attune_author.staleness import compute_source_hash

from attune_gui import editor_corpora

logger = logging.getLogger(__name__)

# Status enum (mirrors design.md "API changes").
FRESH = "fresh"
STALE = "stale"
UNBOUND = "unbound"
SOURCES_MISSING = "sources_missing"


@dataclass
class ProvenanceResult:
    """Staleness + provenance snapshot for one template."""

    bound: bool
    status: str
    feature: str | None = None
    stored_hash: str | None = None
    current_hash: str | None = None
    depth: str | None = None
    generated_at: str | None = None
    source_files: list[str] = field(default_factory=list)
    source_globs: list[str] = field(default_factory=list)
    can_regenerate: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bound": self.bound,
            "status": self.status,
            "feature": self.feature,
            "stored_hash": self.stored_hash,
            "current_hash": self.current_hash,
            "depth": self.depth,
            "generated_at": self.generated_at,
            "source_files": list(self.source_files),
            "source_globs": list(self.source_globs),
            "can_regenerate": self.can_regenerate,
            "reason": self.reason,
        }


@dataclass
class RegenInputs:
    """Everything the regenerate job needs to re-render a template."""

    help_dir: Path
    project_root: Path
    feature: str
    depth: str | None


# ---------------------------------------------------------------------------
# Manifest cache (keyed by help_dir, invalidated on features.yaml mtime change)
# ---------------------------------------------------------------------------

_MANIFEST_CACHE: dict[str, tuple[float, Any]] = {}


def _load_manifest_cached(help_dir: Path) -> Any:
    yaml_path = help_dir / "features.yaml"
    mtime = yaml_path.stat().st_mtime
    key = str(help_dir)
    cached = _MANIFEST_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    manifest = load_manifest(help_dir)
    _MANIFEST_CACHE[key] = (mtime, manifest)
    return manifest


def invalidate(help_dir: Path | str) -> None:
    """Drop the cached manifest for ``help_dir`` (call after a regen)."""
    _MANIFEST_CACHE.pop(str(Path(help_dir)), None)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def _resolve(corpus_id: str, rel_path: str) -> tuple[Path, Path]:
    """Return ``(corpus_root, target_file)``.

    Raises:
        LookupError: unknown corpus id.
        ValueError: ``rel_path`` escapes the corpus root.
        FileNotFoundError: the template doesn't exist.
    """
    entry = editor_corpora.get_corpus(corpus_id)
    if entry is None:
        raise LookupError(f"Unknown corpus id: {corpus_id!r}")
    root = Path(entry.path).resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes corpus root: {rel_path!r}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Template not found: {rel_path!r}")
    return root, candidate


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the YAML frontmatter block into a dict (empty dict if none/malformed)."""
    if not text.startswith("---"):
        return {}
    after_open = text[3:]
    nl = after_open.find("\n")
    if nl == -1:
        return {}
    rest = after_open[nl + 1 :]
    end = rest.find("\n---")
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(rest[:end])
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _find_help_dir(target: Path) -> Path | None:
    """Walk up from ``target`` to the nearest dir holding ``features.yaml``.

    Returns the help_dir (the dir that *contains* ``features.yaml``), or
    None if no manifest is found above the template. Handles both layouts:
    a corpus rooted at ``.help`` (manifest is a direct ancestor) and a
    corpus rooted at the project (manifest lives in ``<root>/.help``).
    """
    for parent in target.parents:
        if (parent / "features.yaml").is_file():
            return parent
        nested = parent / ".help" / "features.yaml"
        if nested.is_file():
            return nested.parent
    return None


def _stringify(value: Any) -> str | None:
    """Render a frontmatter scalar as a string (datetime or str), preserving None."""
    return None if value is None else str(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_provenance(corpus_id: str, rel_path: str) -> ProvenanceResult:
    """Compute the staleness + provenance for one template. No network/LLM."""
    _root, target = _resolve(corpus_id, rel_path)
    fm = _parse_frontmatter(target.read_text(encoding="utf-8"))

    feature_name = fm.get("feature")
    stored = fm.get("source_hash") or fm.get("hash")
    depth = _stringify(fm.get("depth"))
    generated_at = _stringify(fm.get("generated_at"))

    base = ProvenanceResult(
        bound=False,
        status=UNBOUND,
        feature=feature_name,
        stored_hash=stored,
        depth=depth,
        generated_at=generated_at,
    )

    if not feature_name:
        base.reason = "Template has no feature binding (hand-authored)."
        return base

    help_dir = _find_help_dir(target)
    if help_dir is None:
        base.reason = "No features.yaml found above this template."
        return base

    manifest = _load_manifest_cached(help_dir)
    feat = manifest.features.get(feature_name)
    if feat is None:
        base.reason = f"Feature {feature_name!r} is not in features.yaml."
        return base

    project_root = help_dir.parent
    current_hash, matched = compute_source_hash(feat, project_root)
    globs = list(getattr(feat, "files", []))

    if not matched:
        return ProvenanceResult(
            bound=True,
            status=SOURCES_MISSING,
            feature=feature_name,
            stored_hash=stored,
            current_hash=current_hash,
            depth=depth,
            generated_at=generated_at,
            source_globs=globs,
            can_regenerate=False,
            reason="Source files missing — regenerate would fail.",
        )

    status = FRESH if (stored is not None and stored == current_hash) else STALE
    return ProvenanceResult(
        bound=True,
        status=status,
        feature=feature_name,
        stored_hash=stored,
        current_hash=current_hash,
        depth=depth,
        generated_at=generated_at,
        source_files=matched,
        source_globs=globs,
        can_regenerate=True,
    )


def regen_inputs(corpus_id: str, rel_path: str) -> RegenInputs:
    """Resolve the inputs needed to regenerate a template.

    Raises:
        LookupError / ValueError / FileNotFoundError: as :func:`_resolve`.
        PermissionError: the template isn't regenerable (unbound / sources
            missing); the message is a user-facing reason.
    """
    prov = resolve_provenance(corpus_id, rel_path)
    if not prov.can_regenerate:
        raise PermissionError(prov.reason or "Template is not regenerable.")

    _root, target = _resolve(corpus_id, rel_path)
    help_dir = _find_help_dir(target)
    assert help_dir is not None  # can_regenerate implies a manifest was found
    return RegenInputs(
        help_dir=help_dir,
        project_root=help_dir.parent,
        feature=str(prov.feature),
        depth=prov.depth,
    )
