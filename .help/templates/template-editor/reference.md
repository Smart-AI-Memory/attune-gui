---
feature: template-editor
depth: reference
generated_at: 2026-05-05T16:26:26.406568+00:00
source_hash: 22192e4fdfda81908ce0c7de8fd3fa74a92769f56d86d8fd07a2f69d288eb171
status: generated
---

# Template Editor reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CorpusModel` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ListResponse` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ActiveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `RegisterRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ResolveRequest` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `ResolveResponse` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `TemplateResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `DiffRequest` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `HunkModel` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `DiffResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `SaveRequest` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `SaveResponse` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `LintRequest` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `DiagnosticModel` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `AliasInfoModel` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `RenameRequest` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `CorpusEntry` | — | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of ``~/.attune/corpora.json``. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single ``(corpus, path)`` editing tab. | `sidecar/attune_gui/editor_session.py` |
| `PortfileData` | — | `sidecar/attune_gui/editor_sidecar.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `editor_page()` | Render the editor HTML shell. | `sidecar/attune_gui/routes/editor_pages.py` |
| `list_corpora()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `set_active()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `register()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `resolve()` | — | `sidecar/attune_gui/routes/editor_corpus.py` |
| `get_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `diff_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `save_template()` | — | `sidecar/attune_gui/routes/editor_template.py` |
| `lint()` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `autocomplete()` | — | `sidecar/attune_gui/routes/editor_lint.py` |
| `template_schema()` | Return the JSON schema bundled with attune-rag. | `sidecar/attune_gui/routes/editor_schema.py` |
| `healthz()` | Return ``{"status": "ok"}`` if ``token`` matches this sidecar. | `sidecar/attune_gui/routes/editor_health.py` |
| `corpus_ws()` | File-watch + presence channel for one ``(corpus, path)`` editor tab. | `sidecar/attune_gui/routes/editor_ws.py` |
| `rename_preview()` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `rename_apply()` | — | `sidecar/attune_gui/routes/editor_ws.py` |
| `load_registry()` | Read the registry file. Returns an empty Registry if absent. | `sidecar/attune_gui/editor_corpora.py` |
| `save_registry()` | Write the registry to disk. Creates ``~/.attune/`` if needed. | `sidecar/attune_gui/editor_corpora.py` |
| `list_corpora()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `get_corpus()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `get_active()` | — | `sidecar/attune_gui/editor_corpora.py` |
| `set_active()` | Mark ``corpus_id`` as active. Raises ``KeyError`` if unknown. | `sidecar/attune_gui/editor_corpora.py` |
| `register()` | Register a corpus. Returns the new entry; raises ``ValueError`` if | `sidecar/attune_gui/editor_corpora.py` |
| `resolve_path()` | Find the registered corpus owning ``abs_path``. | `sidecar/attune_gui/editor_corpora.py` |
| `load_corpus()` | Instantiate a :class:`attune_rag.DirectoryCorpus` for ``corpus_id``. | `sidecar/attune_gui/editor_corpora.py` |
| `hash_text()` | Return the 16-char sha256 prefix used as the session's optimistic | `sidecar/attune_gui/editor_session.py` |
| `write_portfile()` | Write ``{pid, port, token}`` to the portfile (overwriting). | `sidecar/attune_gui/editor_sidecar.py` |
| `read_portfile()` | Return the parsed portfile or ``None`` if missing/corrupt. | `sidecar/attune_gui/editor_sidecar.py` |
| `delete_portfile()` | Remove the portfile if it exists. No-op when absent. | `sidecar/attune_gui/editor_sidecar.py` |
| `is_pid_alive()` | Return True if a process with ``pid`` is currently running. | `sidecar/attune_gui/editor_sidecar.py` |
| `is_portfile_stale()` | Return True if no fresh sidecar is reachable via the portfile. | `sidecar/attune_gui/editor_sidecar.py` |
| `portfile_context()` | Write the portfile on enter, remove on exit. Always cleans up. | `sidecar/attune_gui/editor_sidecar.py` |


## Source files

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

## Tags

`editor`, `templates`, `codemirror`, `websocket`, `frontend`
