---
feature: template-editor
depth: task
generated_at: 2026-05-05T16:26:26.402216+00:00
source_hash: 22192e4fdfda81908ce0c7de8fd3fa74a92769f56d86d8fd07a2f69d288eb171
status: generated
---

# Work with template editor

Use template editor when you need to codemirror 6 editor for attune-help-style markdown templates, served at /editor by the attune-gui sidecar. schema-driven frontmatter form, debounced server-side lint, tag/alias autocomplete, per-hunk save modal, 3-way merge conflict mode via websocket file_changed pushes, cross-corpus rename refactor, corpus switcher with unsaved-edits guard, persistent advisory banners, and a directory picker. pre-bundled (vite + typescript) into sidecar/attune_gui/static/editor/ so pypi consumers don't need node..

## Prerequisites

- Access to the project source code
- Familiarity with the files under editor-frontend/src/main.ts

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what template editor
   does today before making changes.
   The primary functions are:
   - `editor_page()` in `sidecar/attune_gui/routes/editor_pages.py` — Render the editor HTML shell.
   - `list_corpora()` in `sidecar/attune_gui/routes/editor_corpus.py`
   - `set_active()` in `sidecar/attune_gui/routes/editor_corpus.py`
   - `register()` in `sidecar/attune_gui/routes/editor_corpus.py`
   - `resolve()` in `sidecar/attune_gui/routes/editor_corpus.py`
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "template-editor"`.

## Key files

- `editor-frontend/src/main.ts`
- `editor-frontend/src/editor.ts`
- `editor-frontend/src/api.ts`
- `editor-frontend/src/document-model.ts`
- `editor-frontend/src/frontmatter-form.ts`
- `editor-frontend/src/save-flow.ts`
- `editor-frontend/src/save-modal.ts`
- `editor-frontend/src/lint.ts`
- `editor-frontend/src/autocomplete.ts`
- `editor-frontend/src/diagnostics-strip.ts`
- `editor-frontend/src/diff-gutter.ts`
- `editor-frontend/src/ws.ts`
- `editor-frontend/src/three-way-merge.ts`
- `editor-frontend/src/conflict-mode.ts`
- `editor-frontend/src/rename-modal.ts`
- `editor-frontend/src/corpus-switcher.ts`
- `editor-frontend/src/advisory-banner.ts`
- `editor-frontend/src/grammar/markdown-extension.ts`
- `sidecar/attune_gui/routes/editor_pages.py`
- `sidecar/attune_gui/routes/editor_corpus.py`
- `sidecar/attune_gui/routes/editor_template.py`
- `sidecar/attune_gui/routes/editor_lint.py`
- `sidecar/attune_gui/routes/editor_schema.py`
- `sidecar/attune_gui/routes/editor_health.py`
- `sidecar/attune_gui/routes/editor_ws.py`
- `sidecar/attune_gui/editor_corpora.py`
- `sidecar/attune_gui/editor_session.py`
- `sidecar/attune_gui/editor_sidecar.py`
- `sidecar/attune_gui/templates/editor.html`

## Common modifications

Functions you are most likely to modify:

- `editor_page()` in `sidecar/attune_gui/routes/editor_pages.py`
- `list_corpora()` in `sidecar/attune_gui/routes/editor_corpus.py`
- `set_active()` in `sidecar/attune_gui/routes/editor_corpus.py`
- `register()` in `sidecar/attune_gui/routes/editor_corpus.py`
- `resolve()` in `sidecar/attune_gui/routes/editor_corpus.py`
- `get_template()` in `sidecar/attune_gui/routes/editor_template.py`
- `diff_template()` in `sidecar/attune_gui/routes/editor_template.py`
- `save_template()` in `sidecar/attune_gui/routes/editor_template.py`
