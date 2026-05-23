---
type: reference
name: template-editor-reference
feature: template-editor
depth: reference
generated_at: 2026-05-23T11:23:11.950327+00:00
source_hash: ec1d4153a8e6969223933f4de93941bb8c47c96c480b5a3605f822a911923af1
status: generated
---

# Template Editor reference

The template editor is a CodeMirror 6 editor served at `/editor` by the `attune-gui` sidecar. Use this API to manage the corpus registry, open and save templates, run lint checks, stream file-watch events over WebSocket, and control sidecar lifecycle via portfile. The frontend is pre-bundled (Vite + TypeScript) into `sidecar/attune_gui/static/editor/`; PyPI consumers do not need Node.

---

## `attune_gui.editor_corpora`

Manage the corpus registry stored at `~/.attune/corpora.json`.

### Classes

#### `CorpusEntry` — dataclass

Represents a single registered corpus.

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `name` | `str` | — |
| `path` | `str` | — |
| `kind` | `CorpusKind` | `'source'` |
| `warn_on_edit` | `bool` | `False` |

**Methods**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize the entry to a plain dictionary. |

---

#### `Registry` — dataclass

In-memory snapshot of `~/.attune/corpora.json`.

| Field | Type | Default |
|-------|------|---------|
| `active` | `str | None` | `None` |
| `corpora` | `list[CorpusEntry]` | `field(default_factory=list)` |

**Methods**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize the registry to a plain dictionary. |

---

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_registry` | — | `Registry` | Read the registry file. Returns an empty `Registry` if absent. |
| `save_registry` | `reg: Registry` | `None` | Write the registry to disk. Creates `~/.attune/` if needed. |
| `list_corpora` | — | `list[CorpusEntry]` | Return all registered corpora. |
| `get_corpus` | `corpus_id: str` | `CorpusEntry | None` | Look up a corpus by ID; returns `None` if not found. |
| `get_active` | — | `CorpusEntry | None` | Return the currently active corpus entry, or `None`. |
| `set_active` | `corpus_id: str` | `CorpusEntry` | Mark `corpus_id` as active. |
| `register` | `name: str, path: str, *, kind: CorpusKind = 'source', warn_on_edit: bool | None = None` | `CorpusEntry` | Register a corpus and return the new entry. |
| `resolve_path` | `abs_path: str` | `tuple[CorpusEntry, str] | None` | Find the registered corpus that owns `abs_path`. |
| `load_corpus` | `corpus_id: str` | `Any` | Instantiate an `attune_rag.DirectoryCorpus` for `corpus_id`. |

**Raises**

| Function | Raises | Message |
|----------|--------|---------|
| `set_active` | `KeyError` | `'Unknown corpus id: {...}'` |
| `register` | `ValueError` | `'Not a directory: {...}'` |
| `load_corpus` | `KeyError` | `'Unknown corpus id: {...}'` |

---

## `attune_gui.editor_session`

Manage in-process state for a single `(corpus, path)` editing tab.

### Classes

#### `EditorSession` — dataclass

In-process state for a single `(corpus, path)` editing tab.

| Field | Type | Default |
|-------|------|---------|
| `abs_path` | `Path` | — |
| `base_text` | `str` | — |
| `base_hash` | `str` | — |
| `draft_text` | `str` | `field(init=False)` |
| `poll_interval` | `float` | `0.1` |

**Methods**

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `load` | `cls, abs_path: Path, *, poll_interval: float = 0.1` | `EditorSession` | Construct an `EditorSession` from a file on disk. |
| `update_draft` | `self, text: str` | `None` | Replace the in-memory draft with `text`. |
| `current_disk_hash` | `self` | `str | None` | Return the hash of the file's current on-disk content, or `None` if the file is missing. |
| `matches_base` | `self` | `bool` | Return `True` if the draft matches the base snapshot. |
| `start` | `self` | `None` | Begin background polling for file changes. |
| `stop` | `self` | `None` | Stop background polling. |
| `next_event` | `self` | `dict` | Block until the next file-watch event and return it. |

---

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `hash_text` | `text: str` | `str` | Return the 16-character SHA-256 prefix used as the session's optimistic-concurrency token. |

---

## `attune_gui.editor_sidecar`

Control sidecar lifecycle through the portfile at `~/.attune/`.

### Classes

#### `PortfileData` — dataclass

Contents of the sidecar portfile.

| Field | Type | Default |
|-------|------|---------|
| `pid` | `int` | — |
| `port` | `int` | — |
| `token` | `str` | — |

---

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `write_portfile` | `pid: int, port: int, token: str` | `None` | Write `{pid, port, token}` to the portfile, overwriting any existing file. |
| `read_portfile` | — | `PortfileData | None` | Return the parsed portfile, or `None` if the file is missing or corrupt. |
| `delete_portfile` | — | `None` | Remove the portfile if it exists. No-op when absent. |
| `is_pid_alive` | `pid: int` | `bool` | Return `True` if a process with `pid` is currently running. |
| `is_portfile_stale` | — | `bool` | Return `True` if no fresh sidecar is reachable via the portfile. |
| `portfile_context` | `port: int, token: str` | `Iterator[PortfileData]` | Write the portfile on enter and remove it on exit. Always cleans up. |

---

## `routes.editor_corpus`

HTTP routes for the corpus registry.

### Classes

| Class | Description |
|-------|-------------|
| `CorpusModel` | Response model representing a single corpus. |
| `ListResponse` | Response model for the list-corpora endpoint. |
| `ActiveRequest` | Request body for setting the active corpus. |
| `RegisterRequest` | Request body for registering a corpus. |
| `ResolveRequest` | Request body for resolving an absolute path to a corpus. |
| `ResolveResponse` | Response model for the path-resolution endpoint. |

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_corpora` | — | `ListResponse` | Return all registered corpora. |
| `set_active` | `req: ActiveRequest` | `CorpusModel` | Set the active corpus and return the updated entry. |
| `register` | `req: RegisterRequest` | `CorpusModel` | Register a new corpus and return the created entry. |
| `resolve` | `req: ResolveRequest` | `ResolveResponse` | Resolve an absolute path to its owning corpus and relative path. |

---

## `routes.editor_health`

Liveness check for the sidecar.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `healthz` | `token: str = Query(..., min_length=1)` | `dict` | Return `{"status": "ok"}` if `token` matches this sidecar. |

---

## `routes.editor_lint`

Server-side lint and autocomplete for template content.

### Classes

| Class | Description |
|-------|-------------|
| `LintRequest` | Request body carrying template text to lint. |
| `DiagnosticModel` | A single lint diagnostic returned by the server. |
| `AliasInfoModel` | Metadata about a resolved alias used in autocomplete. |

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `lint` | `corpus_id: str, req: LintRequest` | `list[DiagnosticModel]` | Run lint checks against the submitted template text and return diagnostics. |
| `autocomplete` | `corpus_id: str, kind: Literal['tag', 'alias'] = Query(...), prefix: str = Query('', description='Case-insensitive prefix; empty matches all'), limit: int = Query(50, ge=1, le=500)` | `list` | Return autocomplete suggestions for tags or aliases matching `prefix`. |

---

## `routes.editor_pages`

HTML shell for the editor UI.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `editor_page` | `request: Request, corpus: str | None = None, path: str | None = None` | `HTMLResponse` | Render the editor HTML shell. |

---

## `routes.editor_schema`

JSON schema for template frontmatter.

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `template_schema` | — | `dict[str, Any]` | Return the JSON schema bundled with `attune-rag`. |

---

## `routes.editor_template`

Read, diff, and save template files.

### Classes

| Class | Description |
|-------|-------------|
| `TemplateResponse` | Response model carrying a template's current content. |
| `DiffRequest` | Request body for computing a hunk diff. |
| `HunkModel` | A single diff hunk. |
| `DiffResponse` | Response model carrying the full diff. |
| `SaveRequest` | Request body for a per-hunk save. |
| `SaveResponse` | Response model confirming a save. |

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_template` | `corpus_id: str, path: str = Query(..., min_length=1, alias='path')` | `TemplateResponse` | Fetch the current content of a template file. |
| `diff_template` | `corpus_id: str, req: DiffRequest` | `DiffResponse` | Compute the diff between the draft and the on-disk file. |
| `save_template` | `corpus_id: str, req: SaveRequest` | `SaveResponse` | Write selected hunks to disk and return the updated state. |

---

## `routes.editor_ws`

WebSocket channel for file-watch events and rename refactoring.

### Classes

| Class | Description |
|-------|-------------|
| `RenameRequest` | Request body carrying the old and new names for a rename operation. |

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `corpus_ws` | `websocket: WebSocket, corpus_id: str, path: str` | `None` | File-watch and presence channel for one `(corpus, path)` editor tab. |
| `rename_preview` | `corpus_id: str, req: RenameRequest` | `dict[str, Any]` | Return a preview of all files affected by the rename. |
| `rename_apply` | `corpus_id: str, req: RenameRequest` | `dict[str, Any]` | Apply the rename refactor across the corpus and return results. |

---

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
