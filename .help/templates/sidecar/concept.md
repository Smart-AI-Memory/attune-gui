---
feature: sidecar
depth: concept
generated_at: 2026-05-05T16:26:26.456433+00:00
source_hash: 46b45f3e1ca3cb6ad2d599cfd73bcd4889415b1e3f0a3ab0c887faaaa0503b10
status: generated
---

# Sidecar

## How it works

Sidecar.

The main building blocks are:

- **`CommandSpec`** — core component
- **`CorpusEntry`** — core component
- **`Registry`** — In-memory snapshot of ``~/.attune/corpora.json``.
- **`EditorSession`** — In-process state for a single ``(corpus, path)`` editing tab.
- **`PortfileData`** — core component

Under the hood, this feature spans 88 source
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
| `CorpusEntry` | — | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of ``~/.attune/corpora.json``. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single ``(corpus, path)`` editing tab. | `sidecar/attune_gui/editor_session.py` |
| `PortfileData` | — | `sidecar/attune_gui/editor_sidecar.py` |
