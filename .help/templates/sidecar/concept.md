---
feature: sidecar
depth: concept
generated_at: 2026-05-14T13:07:35.984805+00:00
source_hash: 43602ea53f0e5b79ddaad20853717644b6860bd3776d913da73a0ed8a8701c13
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

Under the hood, this feature spans 105 source
files covering:

- Friendly guard for the unpublished ``attune_rag.editor`` submodule.
- Filesystem helpers shared across routes.
- FastAPI app factory — wires routes, CORS, and the origin guard.

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
