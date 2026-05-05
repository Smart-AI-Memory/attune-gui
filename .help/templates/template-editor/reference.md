---
type: reference
feature: template-editor
depth: reference
generated_at: 2026-05-05T02:17:50.665062+00:00
source_hash: 58fe95b4d95e5e9d2b0dab5826fdd560c2f368a7e93f74ec1eeac297f09d7d78
status: generated
---

# Template Editor reference

Manage corpus registrations, track editing sessions, and handle file operations for the web-based template editor.

## Dataclass Fields

### CorpusEntry

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique identifier for the corpus |
| `name` | `str` | | Human-readable corpus name |
| `path` | `str` | | Filesystem path to corpus directory |
| `kind` | `CorpusKind` | `'source'` | Type of corpus content |
| `warn_on_edit` | `bool` | `False` | Whether to warn before allowing edits |

### Registry

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `active` | `str \| None` | `None` | ID of the currently active corpus |
| `corpora` | `list[CorpusEntry]` | `field(default_factory=list)` | List of registered corpora |

### EditorSession

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `abs_path` | `Path` | | Absolute path to the file being edited |
| `base_text` | `str` | | Original content when session started |
| `base_hash` | `str` | | SHA256 hash of base content |
| `draft_text` | `str` | `field(init=False)` | Current draft content |
| `poll_interval` | `float` | `0.1` | Filesystem polling interval in seconds |

### PortfileData

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pid` | `int` | | Process ID of the running sidecar |
| `port` | `int` | | Port number the sidecar is listening on |
| `token` | `str` | | Authentication token for sidecar access |

## Methods

### CorpusEntry

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize corpus entry to dictionary |

### Registry

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize registry to dictionary |

### EditorSession

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `load(cls, abs_path, *, poll_interval=0.1)` | `abs_path: Path, poll_interval: float = 0.1` | `EditorSession` | Create session for file at given path |
| `update_draft(self, text)` | `text: str` | `None` | Update the draft content |
| `current_disk_hash(self)` | | `str \| None` | Get hash of file's current disk content |
| `matches_base(self)` | | `bool` | Check if draft matches original base content |
| `rebase(self)` | | `None` | Update base content to current disk state |
| `start(self)` | | `None` | Begin filesystem polling |
| `stop(self)` | | `None` | Stop filesystem polling |
| `next_event(self)` | | `dict` | Get next filesystem change event |

## Functions

### Registry Management

| Function | Parameters | Returns | Raises | Description |
|----------|------------|---------|---------|-------------|
| `load_registry()` | | `Registry` | | Read the registry file or return empty Registry if absent |
| `save_registry(reg)` | `reg: Registry` | `None` | | Write the registry to disk, creating `~/.attune/` if needed |
| `list_corpora()` | | `list[CorpusEntry]` | | Get all registered corpora |
| `get_corpus(corpus_id)` | `corpus_id: str` | `CorpusEntry \| None` | | Find corpus by ID |
| `get_active()` | | `CorpusEntry \| None` | | Get the currently active corpus |
| `set_active(corpus_id)` | `corpus_id: str` | `CorpusEntry` | `KeyError` — 'Unknown corpus id: {...}' | Mark corpus as active |
| `register(name, path, *, kind='source', warn_on_edit=None)` | `name: str, path: str, kind: CorpusKind = 'source', warn_on_edit: bool \| None = None` | `CorpusEntry` | `ValueError` — 'Not a directory: {...}' | Register a new corpus |
| `resolve_path(abs_path)` | `abs_path: str` | `tuple[CorpusEntry, str] \| None` | | Find the registered corpus owning the absolute path |
| `load_corpus(corpus_id)` | `corpus_id: str` | | `KeyError` — 'Unknown corpus id: {...}' | Instantiate a DirectoryCorpus for corpus ID |

### Session Management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `hash_text(text)` | `text: str` | `str` | Return the 16-char SHA256 prefix for session tracking |

### Portfile Operations

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `write_portfile()` | | | Write process info to portfile, overwriting existing |
| `read_portfile()` | | `PortfileData \| None` | Return parsed portfile data or None if missing/corrupt |
| `delete_portfile()` | | | Remove portfile if it exists |
| `is_pid_alive()` | | `bool` | Check if process is currently running |
| `is_portfile_stale()` | | `bool` | Check if no fresh sidecar is reachable via portfile |
| `portfile_context()` | | | Context manager to write portfile on enter, remove on exit |

### HTTP Route Handlers

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `healthz()` | | `dict` | Return status check for sidecar freshness |
| `editor_page()` | | | Render the editor HTML shell |
| `template_schema()` | | | Return the JSON schema bundled with attune-rag |
| `corpus_ws()` | | | File-watch and presence channel for editor tabs |

## Tags

`editor`, `templates`, `codemirror`, `websocket`, `frontend`
