---
type: reference
feature: attune-gui
depth: reference
generated_at: 2026-05-05T00:13:12.831905+00:00
source_hash: 373196211438f141eb9a7c64116a3e8312048764f33da724833860f48eb607bc
status: generated
---

# Attune GUI reference

Build local web interfaces for attune development workflows with FastAPI-based sidecar services.

## Classes

### Command and job management

| Class | Description |
|-------|-------------|
| `CommandSpec` | Dataclass defining a command that can be executed through the GUI |
| `Job` | Dataclass representing a single command execution with status tracking |
| `JobContext` | Context object passed to command executors for logging |
| `JobRegistry` | Process-wide job manager with history and cancellation support |

#### CommandSpec fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Command identifier |
| `title` | `str` | | Human-readable display name |
| `domain` | `str` | | Logical grouping (e.g., 'editor', 'living-docs') |
| `description` | `str` | | Brief explanation of what the command does |
| `args_schema` | `dict[str, Any]` | | JSON schema for command arguments |
| `executor` | `ExecutorFn` | | Function that executes the command |
| `cancellable` | `bool` | `True` | Whether the command can be interrupted |
| `profiles` | `tuple[str, ...]` | `('developer',)` | Which UI profiles can see this command |

#### Job fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique job identifier |
| `name` | `str` | | Command name that was executed |
| `args` | `dict[str, Any]` | | Arguments passed to the command |
| `status` | `JobStatus` | `'pending'` | Current execution state |
| `created_at` | `datetime` | current time | When the job was queued |
| `started_at` | `datetime | None` | `None` | When execution began |
| `finished_at` | `datetime | None` | `None` | When execution completed |
| `output_lines` | `list[str]` | `[]` | Log messages from the executor |
| `result` | `Any | None` | `None` | Return value from successful execution |
| `error` | `str | None` | `None` | Error message if execution failed |

### Corpus and editor management

| Class | Description |
|-------|-------------|
| `CorpusEntry` | Dataclass representing a registered document corpus |
| `Registry` | In-memory snapshot of `~/.attune/corpora.json` |
| `EditorSession` | In-process state for a single `(corpus, path)` editing tab |
| `PortfileData` | Dataclass storing sidecar process coordination data |

#### CorpusEntry fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique corpus identifier |
| `name` | `str` | | Human-readable corpus name |
| `path` | `str` | | Filesystem path to the corpus root |
| `kind` | `CorpusKind` | `'source'` | Type of corpus content |
| `warn_on_edit` | `bool` | `False` | Whether to show warnings when editing |

#### Registry fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `active` | `str | None` | `None` | ID of the currently active corpus |
| `corpora` | `list[CorpusEntry]` | `[]` | All registered corpora |

#### EditorSession fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `abs_path` | `Path` | | Absolute path to the file being edited |
| `base_text` | `str` | | Content from disk when session started |
| `base_hash` | `str` | | SHA-256 prefix of base_text |
| `draft_text` | `str` | | Current editor content (auto-initialized) |
| `poll_interval` | `float` | `0.1` | How often to check for disk changes |

#### PortfileData fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pid` | `int` | | Process ID of the running sidecar |
| `port` | `int` | | TCP port the sidecar is listening on |
| `token` | `str` | | Authentication token for API requests |

### Living docs tracking

| Class | Description |
|-------|-------------|
| `DocEntry` | Dataclass representing a tracked documentation file |
| `ReviewItem` | Dataclass representing an auto-applied change awaiting review |

#### DocEntry fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique document identifier |
| `feature` | `str` | | Feature name the document covers |
| `depth` | `str` | | Documentation depth (concept, reference, etc.) |
| `persona` | `str` | | Target audience (end-user, developer, support) |
| `status` | `str` | | Current state (draft, approved, etc.) |
| `path` | `str | None` | | Filesystem path, if the document exists |
| `last_modified` | `str | None` | | ISO timestamp of last change |
| `reason` | `str | None` | `None` | Why the document is in its current state |

#### ReviewItem fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique review item identifier |
| `doc_id` | `str` | | ID of the associated DocEntry |
| `feature` | `str` | | Feature name |
| `depth` | `str` | | Documentation depth |
| `persona` | `str` | | Target audience |
| `trigger` | `str` | | What caused the auto-update |
| `auto_applied_at` | `str` | | ISO timestamp when change was applied |
| `reviewed` | `bool` | `False` | Whether a human has reviewed this change |
| `diff_summary` | `str` | `''` | Brief description of what changed |

## Functions

### App lifecycle

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | | `FastAPI` | Build the FastAPI app with origin-guard, CORS, and all routers wired |

### Command management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_command` | `name: str` | `CommandSpec \| None` | Return the CommandSpec for `name`, or None if it isn't registered |
| `list_commands` | `profile: str \| None = None` | `list[dict[str, Any]]` | Return registered commands as JSON-serializable dicts |

### Corpus registry

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_registry` | | `Registry` | Read the registry file. Returns an empty Registry if absent |
| `save_registry` | `reg: Registry` | `None` | Write the registry to disk. Creates `~/.attune/` if needed |
| `list_corpora` | | `list[CorpusEntry]` | Return all registered corpora |
| `get_corpus` | `corpus_id: str` | `CorpusEntry \| None` | Find a corpus by ID |
| `get_active` | | `CorpusEntry \| None` | Return the currently active corpus |
| `set_active` | `corpus_id: str` | `CorpusEntry` | Mark `corpus_id` as active |
| `register` | `name: str, path: str, *, kind: CorpusKind = 'source', warn_on_edit: bool \| None = None` | `CorpusEntry` | Register a corpus. Returns the new entry |

#### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `set_active` | `KeyError` | 'Unknown corpus id: {...}' |
| `register` | `ValueError` | 'Not a directory: {...}' |

### Editor sessions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `EditorSession.load` | `cls, abs_path: Path, *, poll_interval: float = 0.1` | `EditorSession` | Create a session for editing the file at abs_path |
| `hash_text` | `text: str` | `str` | Return the 16-char sha256 prefix used as the session's optimistic lock token |

### Sidecar coordination

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `write_portfile` | `pid: int, port: int, token: str` | `None` | Write `{pid, port, token}` to the portfile (overwriting) |
| `read_portfile` | | `PortfileData \| None` | Return the parsed portfile or None if missing/corrupt |
| `delete_portfile` | | `None` | Remove the portfile if it exists. No-op when absent |
| `is_pid_alive` | `pid: int` | `bool` | Return True if a process with `pid` is currently running |
| `is_portfile_stale` | | `bool` | Return True if no fresh sidecar is reachable via the portfile |
| `portfile_context` | `pid: int, port: int, token: str` | context manager | Write the portfile on enter, remove on exit. Always cleans up |

### Job management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_registry` | | `JobRegistry` | Return the process-global JobRegistry, creating it on first call |

## Constants

### Version and exports

| Constant | Values |
|----------|--------|
| `__version__` | '0.5.0' |
| `__all__` | ['EditorSession', 'hash_text'] |

### Documentation structure

| Constant | Values |
|----------|--------|
| `_CORE_DEPTHS` | ('concept', 'reference', 'task') |
| `_PHASE_FILES` | ('requirements.md', 'design.md', 'tasks.md') |
| `_PHASE_NAMES` | ('requirements', 'design', 'tasks') |
| `_VALID_STATUSES` | ('draft', 'in-review', 'approved', 'complete', 'completed', 'done') |
| `_DEPTH_STEMS` | ('concept', 'task', 'reference', 'quickstart', 'how-to', 'guide') |

### UI profiles and security

| Constant | Values |
|----------|--------|
| `_VALID_PROFILES` | ('developer', 'author', 'support') |
| `_DEFAULT_PROFILE` | 'developer' |
| `_ALLOWED_ORIGIN_HOSTS` | ('localhost', '127.0.0.1', '[::1]') |

### File handling

| Constant | Values |
|----------|--------|
| `_SHOW_HIDDEN` | ('.help', '.attune') |
