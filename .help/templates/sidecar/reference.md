---
type: reference
name: sidecar-reference
feature: sidecar
depth: reference
generated_at: 2026-05-08T06:44:34.324398+00:00
source_hash: e3ed1fa3b4aba4c7d35bf2c87e344546d5ffef087a34188fb094d356b89502f8
status: generated
---

# Sidecar reference

Create and manage the local FastAPI server that drives the attune GUI, provides editor functionality, and serves as a friendly interface to unpublished attune-rag components.

## Classes

### CommandSpec (dataclass)

Specification for commands exposed in the GUI command registry.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Command identifier |
| `title` | `str` | | Human-readable display name |
| `domain` | `str` | | Command category (rag, author, help) |
| `description` | `str` | | Brief explanation of what the command does |
| `args_schema` | `dict[str, Any]` | | JSON schema for command arguments |
| `executor` | `ExecutorFn` | | Function that runs the command |
| `cancellable` | `bool` | `True` | Whether the command can be cancelled mid-execution |
| `profiles` | `tuple[str, ...]` | `('developer',)` | UI profiles that can access this command |

### Config (dataclass)

Resolved configuration snapshot with values applied from environment, file, and defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `workspace` | `str \| None` | | Current workspace directory path |
| `corpora_registry` | `str \| None` | | Path to corpora.json registry file |
| `specs_root` | `str \| None` | | Directory containing feature specification files |

| Method | Returns | Description |
|--------|---------|-------------|
| `as_dict()` | `dict[str, str \| None]` | Serialize all config values as a dictionary |

### CorpusEntry (dataclass)

Registered corpus in the editor's corpora registry.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Unique identifier for this corpus |
| `name` | `str` | | Display name shown in editor UI |
| `path` | `str` | | Absolute path to the corpus directory |
| `kind` | `CorpusKind` | `'source'` | Type of corpus (source, reference, etc.) |
| `warn_on_edit` | `bool` | `False` | Whether to show warnings when editing files |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Serialize corpus entry for JSON responses |

### Registry (dataclass)

In-memory snapshot of `~/.attune/corpora.json` storing all registered editor corpora.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `active` | `str \| None` | `None` | ID of the currently active corpus |
| `corpora` | `list[CorpusEntry]` | `[]` | List of all registered corpus entries |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Serialize registry for JSON responses |

### EditorSession (dataclass)

In-process state tracking for a single `(corpus, path)` editing session with file watching.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `abs_path` | `Path` | | Absolute path to the file being edited |
| `base_text` | `str` | | File content when session started |
| `base_hash` | `str` | | SHA-256 hash of base_text for drift detection |
| `draft_text` | `str` | | Current draft content (not written to disk) |
| `poll_interval` | `float` | `0.1` | How often to check for external file changes |

| Method | Returns | Description |
|--------|---------|-------------|
| `load(abs_path, *, poll_interval=0.1)` | `EditorSession` | Create session by reading file from disk |
| `update_draft(text)` | `None` | Update the in-memory draft without writing to disk |
| `current_disk_hash()` | `str \| None` | Hash of current file contents, or None if file deleted |
| `matches_base()` | `bool` | Whether file on disk still matches the base version |
| `start()` | `None` | Begin file watching for external changes |
| `stop()` | `None` | Stop file watching and clean up resources |
| `next_event()` | `dict` | Get next file change event (blocking) |

### TemplateKpi (dataclass)

Template statistics for home page KPI tiles showing counts and freshness ratios.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `total` | `int` | | Total number of templates |
| `manual` | `int` | | Number of manually authored templates |
| `generated` | `int` | | Number of auto-generated templates |
| `fresh` | `int` | | Number of fresh generated templates |
| `stale` | `int` | | Number of stale generated templates |
| `very_stale` | `int` | | Number of very stale generated templates |

| Property | Type | Description |
|----------|------|-------------|
| `fresh_ratio` | `float` | Fraction of generated templates that are fresh (0.0 to 1.0) |

### JobsKpi (dataclass)

Job activity statistics for home page dashboard.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `today_count` | `int` | | Number of jobs run today |
| `week_count` | `int` | | Number of jobs run this week |
| `last_status` | `str \| None` | | Status of most recent job |
| `last_finished_at` | `str \| None` | | ISO timestamp of most recent job completion |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `require_editor_submodule` | `name: str` | `Any` | Import `attune_rag.editor.<name>` or raise HTTP 503 |
| `atomic_write` | `target: Path, text: str` | `float` | Write text to target atomically; return new mtime |
| `create_app` | | `FastAPI` | Build FastAPI app with origin-guard, CORS, and all routers |
| `get_command` | `name: str` | `CommandSpec \| None` | Return CommandSpec for name, or None if not registered |
| `list_commands` | `profile: str \| None = None` | `list[dict[str, Any]]` | Return registered commands as JSON-serializable dicts |
| `get` | `key: ConfigKey` | `str \| None` | Return resolved value for key, applying env > file > default |
| `get_source` | `key: ConfigKey` | `KeySource` | Tell user where the resolved value came from |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `require_editor_submodule` | `HTTPException` | HTTP 503 when editor submodule unavailable |

### get_source return values

The `get_source` function returns configuration sources:

| Value | Description |
|-------|-------------|
| `'default'` | Value comes from hardcoded default |

## Module constants

### Core depth names
| Constant | Values |
|----------|--------|
| `_CORE_DEPTHS` | `{'concept', 'reference', 'task'}` |

### Phase definitions
| Constant | Values |
|----------|--------|
| `_PHASE_FILES` | `{'requirements.md', 'design.md', 'tasks.md'}` |
| `_PHASE_NAMES` | `{'requirements', 'design', 'tasks'}` |

### Valid statuses
| Constant | Values |
|----------|--------|
| `_VALID_STATUSES` | `{'draft', 'in-review', 'approved', 'complete', 'completed', 'done'}` |

### Live job statuses
| Constant | Values |
|----------|--------|
| `_LIVE_STATUSES` | `{'pending', 'running'}` |

### Valid UI profiles
| Constant | Values |
|----------|--------|
| `_VALID_PROFILES` | `{'developer', 'author', 'support'}` |

### Default profile
| Constant | Value |
|----------|-------|
| `_DEFAULT_PROFILE` | `'developer'` |

### Depth stems for templates
| Constant | Values |
|----------|--------|
| `_DEPTH_STEMS` | `{'concept', 'task', 'reference', 'quickstart', 'how-to', 'guide'}` |

### Allowed origin hosts
| Constant | Values |
|----------|--------|
| `_ALLOWED_ORIGIN_HOSTS` | `{'localhost', '127.0.0.1', '[::1]'}` |

### Special directories to show
| Constant | Values |
|----------|--------|
| `_SHOW_HIDDEN` | `{'.help', '.attune'}` |

### Configuration keys
| Constant | Values |
|----------|--------|
| `_KEYS` | `{'workspace', 'corpora_registry', 'specs_root'}` |

### Error messages
| Constant | Value |
|----------|-------|
| `_REQUIRED_HINT` | `'The attune-gui template editor needs attune_rag.editor, which is not in any published attune-rag release yet. Install a newer attune-rag (local dev or pre-release) to enable editor routes.'` |
