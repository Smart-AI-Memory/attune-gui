---
feature: sidecar
depth: concept
generated_at: 2026-05-23T15:38:15.234638+00:00
source_hash: a1d71c4c13ab81ddb75e5a3c1d6096e69128d047613aaee8b3ccf4f65d356a74
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

Under the hood, this feature spans 110 source
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
