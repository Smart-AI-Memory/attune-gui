---
type: reference
name: template-editor-reference
feature: template-editor
depth: reference
generated_at: 2026-06-23T04:13:38.193854+00:00
source_hash: 407c7dc6dcfaefcca257d93599116ce8bf9cd491c25de410e9dd8361366327ef
status: generated
---

# Template Editor reference

A CodeMirror 6 editor for attune-help-style markdown templates, served at `/editor` by the `attune-gui` sidecar. Use this reference to look up the Python classes, dataclass fields, and route functions that back the editor's corpus registry, session tracking, sidecar lifecycle, linting, diff/save flow, and WebSocket file-watch channel.

The frontend is pre-bundled (Vite + TypeScript) into `sidecar/attune_gui/static/editor/`, so PyPI consumers do not need Node.

---

## Dataclass fields

### `CorpusEntry`

Registered corpus entry stored in `~/.attune/corpora.json`.

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `name` | `str` | — |
| `path` | `str` | — |
| `kind` | `CorpusKind` | `'source'` |
| `warn_on_edit` | `bool` | `False` |

### `Registry`

In-memory snapshot of `~/.attune/corpora.json`.

| Field | Type | Default |
|-------|------|---------|
| `active` | `str | None` | `None` |
| `corpora` | `list[CorpusEntry]` | `field(default_factory=list)` |

### `EditorSession`

In-process state for a single `(corpus, path)` editing tab.

| Field | Type | Default |
|-------|------|---------|
| `abs_path` | `Path` | — |
| `base_text` | `str` | — |
| `base_hash` | `str` | — |
| `draft_text` | `str` | `field(init=False)` |
| `poll_interval` | `float` | `0.1` |

### `PortfileData`

Parsed contents of the sidecar portfile.

| Field | Type | Default |
|-------|------|---------|
| `pid` | `int` | — |
| `port` | `int` | — |
| `token` | `str` | — |

---

## `attune_gui.editor_corpora`

Functions for reading and writing the corpus registry at `~/.attune/corpora.json`.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_registry` | — | `Registry` | Read the registry file. Returns an empty `Registry` if absent. |
| `save_registry` | `reg: Registry` | `None` | Write the registry to disk. Creates `~/.attune/` if needed. |
| `list_corpora` | — | `list[CorpusEntry]` | Return all registered corpus entries. |
| `get_corpus` | `corpus_id: str` | `CorpusEntry | None` | Look up a corpus by ID; returns `None` if not found. |
| `get_active` | — | `CorpusEntry | None` | Return the currently active corpus entry, or `None`. |
| `set_active` | `corpus_id: str` | `CorpusEntry` | Mark `corpus_id` as active. |
| `register` | `name: str, path: str, *, kind: CorpusKind = 'source', warn_on_edit: bool | None = None` | `CorpusEntry` | Register a corpus and return the new entry. |
| `resolve_path` | `abs_path: str` | `tuple[CorpusEntry, str] | None` | Find the registered corpus that owns `abs_path`. |
| `load_corpus` | `corpus_id: str` | `Any` | Instantiate an `attune_rag.DirectoryCorpus` for `corpus_id`. |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `set_active` | `KeyError` | `'Unknown corpus id: {...}'` |
| `register` | `ValueError` | `'Not a directory: {...}'` |
| `load_corpus` | `KeyError` | `'Unknown corpus id: {...}'` |

### Methods

| Class | Method | Parameters | Returns | Description |
|-------|--------|------------|---------|-------------|
| `CorpusEntry` | `to_dict` | `self` | `dict[str, Any]` | Serialize the entry to a plain dict. |
| `Registry` | `to_dict` | `self` | `dict[str, Any]` | Serialize the registry to a plain dict. |

---

## `attune_gui.editor_session`

Per-tab session state and disk-hash utilities.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `hash_text` | `text: str` | `str` | Return the 16-character SHA-256 prefix used as the session's optimistic-concurrency token. |

### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `load` | `cls, abs_path: Path, *, poll_interval: float = 0.1` | `EditorSession` | Construct a session by reading `abs_path` from disk. |
| `update_draft` | `self, text: str` | `None` | Replace the in-memory draft with `text`. |
| `current_disk_hash` | `self` | `str | None` | Return the hash of the file currently on disk, or `None` if unreadable. |
| `matches_base` | `self` | `bool` | Return `True` if the draft matches the base text loaded at session open. |
| `start` | `self` | `None` | Begin background polling for file changes. |
| `stop` | `self` | `None` | Stop background polling. |
| `next_event` | `self` | `dict` | Block until the next file-change event and return it. |

---

## `attune_gui.editor_sidecar`

Portfile lifecycle management for the `attune-gui` sidecar process.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `write_portfile` | `pid: int, port: int, token: str` | `None` | Write `{pid, port, token}` to the portfile, overwriting any existing file. |
| `read_portfile` | — | `PortfileData | None` | Return the parsed portfile, or `None` if missing or corrupt. |
| `delete_portfile` | — | `None` | Remove the portfile if it exists; no-op when absent. |
| `is_pid_alive` | `pid: int` | `bool` | Return `True` if a process with `pid` is currently running. |
| `is_portfile_stale` | — | `bool` | Return `True` if no fresh sidecar is reachable via the portfile. |
| `portfile_context` | `port: int, token: str` | `Iterator[PortfileData]` | Write the portfile on enter and remove it on exit; always cleans up. |

---

## `routes.editor_corpus`

HTTP routes for the corpus registry.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_corpora` | — | `ListResponse` | Return all registered corpora. |
| `set_active` | `req: ActiveRequest` | `CorpusModel` | Set the active corpus. |
| `register` | `req: RegisterRequest` | `CorpusModel` | Register a new corpus. |
| `resolve` | `req: ResolveRequest` | `ResolveResponse` | Resolve an absolute path to its owning corpus and relative path. |

---

## `routes.editor_health`

Health-check route for portfile freshness validation.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `healthz` | `token: str = Query(..., min_length=1)` | `dict` | Return `{"status": "ok"}` if `token` matches this sidecar. |

---

## `routes.editor_lint`

Linting and autocomplete routes.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `lint` | `corpus_id: str, req: LintRequest` | `list[DiagnosticModel]` | Run server-side lint on a template and return diagnostics. |
| `autocomplete` | `corpus_id: str, kind: Literal['tag', 'alias'] = Query(...), prefix: str = Query('', description='Case-insensitive prefix; empty matches all'), limit: int = Query(50, ge=1, le=500)` | `list` | Return tag or alias completions matching `prefix`. |

---

## `routes.editor_pages`

HTML shell route.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `editor_page` | `request: Request, corpus: str | None = None, path: str | None = None` | `HTMLResponse` | Render the editor HTML shell. |

---

## `routes.editor_schema`

JSON schema route.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `template_schema` | — | `dict[str, Any]` | Return the JSON schema bundled with `attune-rag`. |

---

## `routes.editor_template`

Template read, diff, and save routes.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_template` | `corpus_id: str, path: str = Query(..., min_length=1, alias='path')` | `TemplateResponse` | Fetch a template's current content from disk. |
| `diff_template` | `corpus_id: str, req: DiffRequest` | `DiffResponse` | Compute a unified diff between the draft and the on-disk file. |
| `save_template` | `corpus_id: str, req: SaveRequest` | `SaveResponse` | Write selected hunks to disk. |

---

## `routes.editor_ws`

WebSocket file-watch and rename-refactor routes.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `corpus_ws` | `websocket: WebSocket, corpus_id: str, path: str` | `None` | File-watch and presence channel for one `(corpus, path)` editor tab. |
| `rename_preview` | `corpus_id: str, req: RenameRequest` | `dict[str, Any]` | Return a preview of all cross-reference changes a rename would produce. |
| `rename_apply` | `corpus_id: str, req: RenameRequest` | `dict[str, Any]` | Apply a rename and update all affected cross-references. |

---

## Classes summary

| Class | Module | Description |
|-------|--------|-------------|
| `CorpusEntry` | `attune_gui.editor_corpora` | Registered corpus entry (see [Fields](#corpusentry)). |
| `Registry` | `attune_gui.editor_corpora` | In-memory snapshot of `~/.attune/corpora.json` (see [Fields](#registry)). |
| `EditorSession` | `attune_gui.editor_session` | In-process state for a single `(corpus, path)` editing tab (see [Fields](#editorsession)). |
| `PortfileData` | `attune_gui.editor_sidecar` | Parsed sidecar portfile contents (see [Fields](#portfiledata)). |
| `CorpusModel` | `routes.editor_corpus` | HTTP response model for a single corpus. |
| `ListResponse` | `routes.editor_corpus` | HTTP response model for the corpus list. |
| `ActiveRequest` | `routes.editor_corpus` | Request body for setting the active corpus. |
| `RegisterRequest` | `routes.editor_corpus` | Request body for registering a corpus. |
| `ResolveRequest` | `routes.editor_corpus` | Request body for resolving an absolute path. |
| `ResolveResponse` | `routes.editor_corpus` | Response body carrying the owning corpus and relative path. |
| `LintRequest` | `routes.editor_lint` | Request body for the lint endpoint. |
| `DiagnosticModel` | `routes.editor_lint` | Single lint diagnostic returned by the lint endpoint. |
| `AliasInfoModel` | `routes.editor_lint` | Alias metadata returned by the autocomplete endpoint. |
| `TemplateResponse` | `routes.editor_template` | Response body for `get_template`. |
| `DiffRequest` | `routes.editor_template` | Request body for `diff_template`. |
| `HunkModel` | `routes.editor_template` | A single unified-diff hunk. |
| `DiffResponse` | `routes.editor_template` | Response body for `diff_template`. |
| `SaveRequest` | `routes.editor_template` | Request body for `save_template`. |
| `SaveResponse` | `routes.editor_template` | Response body for `save_template`. |
| `RenameRequest` | `routes.editor_ws` | Request body for `rename_preview` and `rename_apply`. |

---

## Source files

| File | Purpose |
|------|---------|
| `editor-frontend/src/main.ts` | Frontend entry point |
| `editor-frontend/src/editor.ts` | CodeMirror editor setup |
| `editor-frontend/src/api.ts` | HTTP client for sidecar routes |
| `editor-frontend/src/document-model.ts` | In-browser document model |
| `editor-frontend/src/frontmatter-form.ts` | Schema-driven frontmatter form |
| `editor-frontend/src/save-flow.ts` | Save flow orchestration |
| `editor-frontend/src/save-modal.ts` | Per-hunk save modal |
| `editor-frontend/src/lint.ts` | Debounced lint integration |
| `editor-frontend/src/autocomplete.ts` | Tag/alias autocomplete |
| `editor-frontend/src/diagnostics-strip.ts` | Diagnostics display strip |
| `editor-frontend/src/diff-gutter.ts` | Diff gutter decorations |
| `editor-frontend/src/ws.ts` | WebSocket client |
| `editor-frontend/src/three-way-merge.ts` | Three-way merge logic |
| `editor-frontend/src/conflict-mode.ts` | Conflict resolution mode |
| `editor-frontend/src/rename-modal.ts` | Cross-corpus rename modal |
| `editor-frontend/src/corpus-switcher.ts` | Corpus switcher with unsaved-edits guard |
| `editor-frontend/src/advisory-banner.ts` | Persistent advisory banners |
| `editor-frontend/src/grammar/markdown-extension.ts` | Markdown grammar extension |
| `sidecar/attune_gui/routes/editor_pages.py` | HTML shell route |
| `sidecar/attune_gui/routes/editor_corpus.py` | Corpus registry routes |
| `sidecar/attune_gui/routes/editor_template.py` | Template read/diff/save routes |
| `sidecar/attune_gui/routes/editor_lint.py` | Lint and autocomplete routes |
| `sidecar/attune_gui/routes/editor_schema.py` | JSON schema route |
| `sidecar/attune_gui/routes/editor_health.py` | Health-check route |
| `sidecar/attune_gui/routes/editor_ws.py` | WebSocket and rename routes |
| `sidecar/attune_gui/editor_corpora.py` | Corpus registry logic |
| `sidecar/attune_gui/editor_session.py` | Editor session logic |
| `sidecar/attune_gui/editor_sidecar.py` | Portfile lifecycle |
| `sidecar/attune_gui/templates/editor.html
