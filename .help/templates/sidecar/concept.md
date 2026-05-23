---
feature: sidecar
depth: concept
generated_at: 2026-05-23T12:15:13.893753+00:00
source_hash: d509f940912ab837e49bab6ed81c03a030572fdec5475967ceae86389dc3dc11
status: generated
---

# Sidecar

## How it works

Sidecar.

The main building blocks are:

- **`CommandSpec`** — core component
- **`Config`** — Resolved config snapshot. Values are post-precedence.
- **`CorpusEntry`** — core component
- **`Registry`** — In-memory snapshot of ``~/.attune/corpora.json``.
- **`EditorSession`** — In-process state for a single ``(corpus, path)`` editing tab.

Under the hood, this feature spans 107 source
files covering:

- Filesystem helpers shared across routes.
- FastAPI app factory — wires routes, CORS, and the origin guard.
- Command registry — the canonical list of what the GUI can run.

## What connects to it


Other parts of the codebase interact with
sidecar through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CommandSpec` | — | `sidecar/attune_gui/commands.py` |
| `Config` | Resolved config snapshot. Values are post-precedence. | `sidecar/attune_gui/config.py` |
| `CorpusEntry` | — | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of ``~/.attune/corpora.json``. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single ``(corpus, path)`` editing tab. | `sidecar/attune_gui/editor_session.py` |
