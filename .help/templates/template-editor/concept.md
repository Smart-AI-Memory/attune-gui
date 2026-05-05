---
feature: template-editor
depth: concept
generated_at: 2026-05-05T16:26:26.395773+00:00
source_hash: 22192e4fdfda81908ce0c7de8fd3fa74a92769f56d86d8fd07a2f69d288eb171
status: generated
---

# Template Editor

## How it works

CodeMirror 6 editor for attune-help-style markdown templates, served at /editor by the attune-gui sidecar. Schema-driven frontmatter form, debounced server-side lint, tag/alias autocomplete, per-hunk save modal, 3-way merge conflict mode via WebSocket file_changed pushes, cross-corpus rename refactor, corpus switcher with unsaved-edits guard, persistent advisory banners, and a directory picker. Pre-bundled (Vite + TypeScript) into sidecar/attune_gui/static/editor/ so PyPI consumers don't need Node..

The main building blocks are:

- **`CorpusModel`** — core component
- **`ListResponse`** — core component
- **`ActiveRequest`** — core component
- **`RegisterRequest`** — core component
- **`ResolveRequest`** — core component

Under the hood, this feature spans 29 source
files covering:

- Corpora-registry routes for the template editor (M2 task #7).
- Template GET / diff / save routes for the editor (M2 task #10).
- Lint + autocomplete proxy routes for the template editor (M2 task #11).

## What connects to it

This feature relates to: editor, templates, codemirror, websocket, frontend.

Other parts of the codebase interact with
template editor through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CorpusModel` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ListResponse` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ActiveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `RegisterRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ResolveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
