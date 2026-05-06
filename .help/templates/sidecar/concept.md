---
feature: sidecar
depth: concept
generated_at: 2026-05-06T03:22:24.071907+00:00
source_hash: 9a45296c182496f7a010644896af3e7b8be6dca9a5412ea5145a2d2e9d9944ab
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

Under the hood, this feature spans 90 source
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
