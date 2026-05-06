"""Corpora registry for the template editor (template-editor M2 task #7).

Persisted to ``~/.attune/corpora.json``. The registry is a simple list
of directories the editor can browse + an optional ``active`` pointer
mirroring the last-used corpus.

Schema (v1):

::

    {
      "version": 1,
      "active": "<id>" | null,
      "corpora": [
        {
          "id": "<slug>",
          "name": "<display>",
          "path": "<absolute path>",
          "kind": "source" | "generated",
          "warn_on_edit": <bool, optional>
        }
      ]
    }

IDs are slugs derived from ``name``; the registry preserves whatever
the caller supplies and only ensures uniqueness on register.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

CorpusKind = Literal["source", "generated", "ad-hoc"]
_VERSION = 1


def _registry_path() -> Path:
    """Return the on-disk corpora-registry path.

    Resolution order (highest priority first):
      1. ``ATTUNE_CORPORA_REGISTRY`` env var (CI / one-off)
      2. ``corpora_registry`` in ``~/.attune-gui/config.json``
      3. Default: ``~/.attune/corpora.json``
    """
    from attune_gui import config  # noqa: PLC0415 — local import keeps this hot path lean

    override = config.get("corpora_registry")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".attune" / "corpora.json"


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    name: str
    path: str
    kind: CorpusKind = "source"
    warn_on_edit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Registry:
    """In-memory snapshot of ``~/.attune/corpora.json``."""

    active: str | None = None
    corpora: list[CorpusEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": _VERSION,
            "active": self.active,
            "corpora": [c.to_dict() for c in self.corpora],
        }


# -- IO -------------------------------------------------------------


def load_registry() -> Registry:
    """Read the registry file. Returns an empty Registry if absent."""
    try:
        raw = _registry_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return Registry()
    except OSError:
        return Registry()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Registry()
    if not isinstance(data, dict):
        return Registry()
    return Registry(
        active=data.get("active") if isinstance(data.get("active"), str) else None,
        corpora=[_parse_entry(c) for c in data.get("corpora", []) if isinstance(c, dict)],
    )


def save_registry(reg: Registry) -> None:
    """Write the registry to disk. Creates ``~/.attune/`` if needed."""
    _registry_path().parent.mkdir(parents=True, exist_ok=True)
    _registry_path().write_text(json.dumps(reg.to_dict(), indent=2) + "\n", encoding="utf-8")


def _parse_entry(raw: dict[str, Any]) -> CorpusEntry:
    kind = raw.get("kind")
    if kind not in ("source", "generated", "ad-hoc"):
        kind = "source"
    return CorpusEntry(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        path=str(raw.get("path", "")),
        kind=kind,
        warn_on_edit=bool(raw.get("warn_on_edit", False)),
    )


# -- ops ------------------------------------------------------------


def list_corpora() -> list[CorpusEntry]:
    return load_registry().corpora


def get_corpus(corpus_id: str) -> CorpusEntry | None:
    for entry in list_corpora():
        if entry.id == corpus_id:
            return entry
    return None


def get_active() -> CorpusEntry | None:
    reg = load_registry()
    if reg.active is None:
        return None
    for entry in reg.corpora:
        if entry.id == reg.active:
            return entry
    return None


def set_active(corpus_id: str) -> CorpusEntry:
    """Mark ``corpus_id`` as active. Raises ``KeyError`` if unknown."""
    reg = load_registry()
    found = next((c for c in reg.corpora if c.id == corpus_id), None)
    if found is None:
        raise KeyError(f"Unknown corpus id: {corpus_id!r}")
    reg.active = corpus_id
    save_registry(reg)
    return found


def register(
    name: str,
    path: str,
    *,
    kind: CorpusKind = "source",
    warn_on_edit: bool | None = None,
) -> CorpusEntry:
    """Register a corpus. Returns the new entry; raises ``ValueError`` if
    the path is not a directory.

    If a corpus with the same ``path`` is already registered, returns
    the existing entry rather than creating a duplicate.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {resolved}")

    reg = load_registry()
    existing = next((c for c in reg.corpora if c.path == str(resolved)), None)
    if existing is not None:
        return existing

    base_id = _slug(name) or _slug(resolved.name) or "corpus"
    used = {c.id for c in reg.corpora}
    new_id = base_id
    counter = 2
    while new_id in used:
        new_id = f"{base_id}-{counter}"
        counter += 1

    entry = CorpusEntry(
        id=new_id,
        name=name,
        path=str(resolved),
        kind=kind,
        warn_on_edit=bool(warn_on_edit) if warn_on_edit is not None else (kind == "generated"),
    )
    reg.corpora.append(entry)
    if reg.active is None:
        reg.active = entry.id
    save_registry(reg)
    return entry


def resolve_path(abs_path: str) -> tuple[CorpusEntry, str] | None:
    """Find the registered corpus owning ``abs_path``.

    Walks parents of ``abs_path``; the deepest registered root wins
    (handles nested corpora). Returns ``(corpus, rel_path)`` or
    ``None`` if no corpus contains the path.
    """
    target = Path(abs_path).expanduser().resolve()
    candidates = list_corpora()
    best: tuple[CorpusEntry, Path] | None = None
    for entry in candidates:
        root = Path(entry.path).resolve()
        try:
            rel = target.relative_to(root)
        except ValueError:
            continue
        if best is None or len(root.parts) > len(Path(best[0].path).resolve().parts):
            best = (entry, rel)
    if best is None:
        return None
    entry, rel_path = best
    return entry, rel_path.as_posix()


def load_corpus(corpus_id: str):
    """Instantiate a :class:`attune_rag.DirectoryCorpus` for ``corpus_id``.

    Imports lazily so attune-gui can start without attune-rag's editor
    deps being importable. Raises :class:`KeyError` if the id is
    unknown.
    """
    from attune_rag import DirectoryCorpus  # noqa: PLC0415

    entry = get_corpus(corpus_id)
    if entry is None:
        raise KeyError(f"Unknown corpus id: {corpus_id!r}")
    return DirectoryCorpus(Path(entry.path))


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slug(value: str) -> str:
    cleaned = _SLUG_RE.sub("-", value.lower()).strip("-")
    return re.sub(r"-+", "-", cleaned)
