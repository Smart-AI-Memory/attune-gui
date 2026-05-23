---
feature: sidecar
depth: concept
generated_at: 2026-05-23T02:46:21.733757+00:00
source_hash: a2c72dd4b6cdbbe7e957643478bb58cc655c07347338265610ee6a93ae6d8a1d
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

Under the hood, this feature spans 104 source
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
