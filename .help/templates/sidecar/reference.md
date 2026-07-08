---
type: reference
name: sidecar-reference
feature: sidecar
depth: reference
generated_at: 2026-06-23T04:14:34.358058+00:00
source_hash: 6d1a3b2a6686655be45c94fbd62b43d5887dec3496603be6ca7a12500650779e
status: generated
---

# Sidecar reference

`attune-gui` is a local FastAPI sidecar that drives `attune-rag`, `attune-author`, and `attune-help`. This page covers the public classes, dataclass fields, functions, and constants you interact with when extending or integrating the sidecar.

## Classes

The following classes are available in `attune_gui`. Dataclass fields are listed in the subsections below.

| Class | Description | File |
|-------|-------------|------|
| `CommandSpec` | Descriptor for a registered GUI command, including its executor and JSON schema. | `sidecar/attune_gui/commands.py` |
| `Config` | Resolved config snapshot. Values are post-precedence. | `sidecar/attune_gui/config.py` |
| `CorpusEntry` | One registered corpus entry in the corpora registry. | `sidecar/attune_gui/editor_corpora.py` |
| `Registry` | In-memory snapshot of `~/.attune/corpora.json`. | `sidecar/attune_gui/editor_corpora.py` |
| `EditorSession` | In-process state for a single `(corpus, path)` editing tab. | `sidecar/attune_gui/editor_session.py` |
| `PortfileData` | Parsed contents of the sidecar portfile. | `sidecar/attune_gui/editor_sidecar.py` |
| `TemplateKpi` | Templates count + stale-vs-fresh ratio for the home tiles. | `sidecar/attune_gui/home_summary.py` |
| `JobsKpi` | Job-activity snapshot. | `sidecar/attune_gui/home_summary.py` |
| `DailyJobs` | One day's job count for the sparkline. | `sidecar/attune_gui/home_summary.py` |
| `FamilyVersion` | Installed version of one attune-* package. | `sidecar/attune_gui/home_summary.py` |

### `CommandSpec` fields

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `title` | `str` | — |
| `domain` | `str` | — |
| `description` | `str` | — |
| `args_schema` | `dict[str, Any]` | — |
| `executor` | `ExecutorFn` | — |
| `cancellable` | `bool` | `True` |
| `profiles` | `tuple[str, ...]` | `('developer',)` |

### `Config` fields

| Field | Type | Default |
|-------|------|---------|
| `workspace` | `str | None` | — |
| `corpora_registry` | `str | None` | — |
| `specs_root` | `str | None` | — |

### `CorpusEntry` fields

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `name` | `str` | — |
| `path` | `str` | — |
| `kind` | `CorpusKind` | `'source'` |
| `warn_on_edit` | `bool` | `False` |

### `Registry` fields

| Field | Type | Default |
|-------|------|---------|
| `active` | `str | None` | `None` |
| `corpora` | `list[CorpusEntry]` | `field(default_factory=list)` |

### `EditorSession` fields

| Field | Type | Default |
|-------|------|---------|
| `abs_path` | `Path` | — |
| `base_text` | `str` | — |
| `base_hash` | `str` | — |
| `draft_text` | `str` | `field(init=False)` |
| `poll_interval` | `float` | `0.1` |

### `PortfileData` fields

| Field | Type | Default |
|-------|------|---------|
| `pid` | `int` | — |
| `port` | `int` | — |
| `token` | `str` | — |

### `TemplateKpi` fields

| Field | Type | Default |
|-------|------|---------|
| `total` | `int` | — |
| `manual` | `int` | — |
| `generated` | `int` | — |
| `fresh` | `int` | — |
| `stale` | `int` | — |

#### `TemplateKpi` properties

| Property | Type | Description |
|----------|------|-------------|
| `fresh_ratio` | `float` | Fraction of generated templates that are fresh (0.0 to 1.0). |

### `JobsKpi` fields

| Field | Type | Default |
|-------|------|---------|
| `today_count` | `int` | — |
| `week_count` | `int` | — |
| `last_status` | `str | None` | — |
| `last_finished_at` | `str | None` | — |

### `DailyJobs` fields

| Field | Type | Default |
|-------|------|---------|
| `day` | `str` | — |
| `count` | `int` | — |

### `FamilyVersion` fields

| Field | Type | Default |
|-------|------|---------|
| `package` | `str` | — |
| `version` | `str | None` | — |
| `importable` | `bool` | — |

## Functions

### Filesystem helpers (`attune_gui/_fs.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `atomic_write` | `target: Path, text: str` | `float` | Write `text` to `target` atomically; return the new mtime. |

### App factory (`attune_gui/app.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | — | `FastAPI` | Build the FastAPI app with origin-guard, CORS, and all routers wired. |

### Command registry (`attune_gui/commands.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_command` | `name: str` | `CommandSpec | None` | Return the `CommandSpec` for `name`, or `None` if it isn't registered. |
| `list_commands` | `profile: str | None = None` | `list[dict[str, Any]]` | Return registered commands as JSON-serializable dicts. |

### Config (`attune_gui/config.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_valid_key` | `key: str` | `bool` | Return whether `key` is a recognized config key. |
| `known_keys` | — | `tuple[ConfigKey, ...]` | Return all recognized config key names. |
| `env_var_for` | `key: ConfigKey` | `str` | Return the environment variable name for `key`. |
| `get` | `key: ConfigKey` | `str | None` | Return the resolved value for `key`, applying env > file > default. |
| `get_source` | `key: ConfigKey` | `KeySource` | Tell the caller where the resolved value came from. Used by `config --list`. |
| `load` | — | `Config` | Resolve all keys at once. |
| `set_value` | `key: ConfigKey, value: str` | `None` | Persist `value` to the config file. Does not validate semantics. |
| `unset_value` | `key: ConfigKey` | `bool` | Remove `key` from the config file. Returns `True` if it was present. |

#### `get_source` return values

| Value |
|-------|
| `'default'` |

### Corpus management (`attune_gui/editor_corpora.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_registry` | — | `Registry` | Read the registry file. Returns an empty `Registry` if absent. |
| `save_registry` | `reg: Registry` | `None` | Write the registry to disk. Creates `~/.attune/` if needed. |
| `list_corpora` | — | `list[CorpusEntry]` | Return all registered corpus entries. |
| `get_corpus` | `corpus_id: str` | `CorpusEntry | None` | Return the corpus entry for `corpus_id`, or `None` if unknown. |
| `get_active` | — | `CorpusEntry | None` | Return the currently active corpus entry, or `None` if unset. |
| `set_active` | `corpus_id: str` | `CorpusEntry` | Mark `corpus_id` as active. Raises `KeyError` if unknown. |
| `register` | `name: str, path: str, *, kind: CorpusKind = 'source', warn_on_edit: bool | None = None` | `CorpusEntry` | Register a corpus. Returns the new entry; raises `ValueError` if the path is invalid. |
| `resolve_path` | `abs_path: str` | `tuple[CorpusEntry, str] | None` | Find the registered corpus that owns `abs_path`. |
| `load_corpus` | `corpus_id: str` | `Any` | Instantiate an `attune_rag.DirectoryCorpus` for `corpus_id`. |

### Editor session (`attune_gui/editor_session.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `hash_text` | `text: str` | `str` | Return the 16-char SHA-256 prefix used as the session's optimistic lock token. |

### Portfile helpers (`attune_gui/editor_sidecar.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `write_portfile` | `pid: int, port: int, token: str` | `None` | Write `{pid, port, token}` to the portfile, overwriting any existing file. |
| `read_portfile` | — | `PortfileData | None` | Return the parsed portfile, or `None` if missing or corrupt. |
| `delete_portfile` | — | `None` | Remove the portfile if it exists. No-op when absent. |
| `is_pid_alive` | `pid: int` | `bool` | Return `True` if a process with `pid` is currently running. |
| `is_portfile_stale` | — | `bool` | Return `True` if no fresh sidecar is reachable via the portfile. |
| `portfile_context` | `port: int, token: str` | `Iterator[PortfileData]` | Write the portfile on enter, remove on exit. Always cleans up. |

### Error handling (`attune_gui/errors.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `error_envelope` | `*, message: str, code: str | None = None` | `dict[str, dict[str, Any]]` | Build the canonical `{"detail": {"message": ..., "code": ...}}` response body. |
| `http_exception_handler` | `request: Request, exc: HTTPException` | `JSONResponse` | Render every `HTTPException` through `error_envelope`. |
| `request_validation_exception_handler` | `request: Request, exc: RequestValidationError` | `JSONResponse` | Render FastAPI's 422 request-validation errors through `error_envelope`. |
| `unhandled_exception_handler` | `request: Request, exc: Exception` | `JSONResponse` | Last-resort handler for exceptions that escape the route layer. |
| `install_handlers` | `app: FastAPI` | `None` | Register the three error handlers on `app` at construction time. |

### Home summary (`attune_gui/home_summary.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `sparkline_points` | `values: list[int], *, width: int = 240, height: int = 40` | `str` | Render a list of values as an SVG `polyline` `points` string. |
| `build_home_summary` | — | `HomeSummary` | Build the home-page summary by composing existing accessors. |

### Job registry (`attune_gui/jobs.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_registry` | — | `JobRegistry` | Return the process-global `JobRegistry`, creating it on first call. |

### Living docs store (`attune_gui/living_docs_store.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_store` | — | `LivingDocsStore` | Return the process-global `LivingDocsStore` singleton, creating it on first call. |

### CLI entry point (`attune_gui/main.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | `argv: list[str] | None = None` | `int` | CLI entry point: parse args, pick a port, print `SIDECAR_URL`, run uvicorn. |

### MCP server (`attune_gui/mcp/server.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_server` | — | `AttuneGuiMCPServer` | Instantiate and return the `AttuneGuiMCPServer`. |
| `main` | — | `None` | MCP server entry point. |

### MCP tools (`attune_gui/mcp/tools.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `gui_list_specs` | `_args: dict[str, Any]` | `dict[str, Any]` | List all feature specs via the MCP tool interface. |
| `gui_get_spec` | `args: dict[str, Any]` | `dict[str, Any]` | Retrieve a single feature spec via the MCP tool interface. |
| `gui_get_spec_status` | `args: dict[str, Any]` | `dict[str, Any]` | Return the status of a feature spec via the MCP tool interface. |
| `gui_list_living_docs` | `args: dict[str, Any]` | `dict[str, Any]` | List living docs via the MCP tool interface. |
| `gui_get_living_doc` | `args: dict[str, Any]` | `dict[str, Any]` | Retrieve a single living doc via the MCP tool interface. |
| `gui_set_spec_status` | `args: dict[str, Any]` | `dict[str, Any]` | Set the status of a feature spec via the MCP tool interface. |
| `get_dispatch` | — | `dict[str, Any]` | Return the tool-name → async handler dispatch map. Imported by `server`. |

### Provenance (`attune_gui/provenance.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `invalidate` | `help_dir: Path | str` | `None` | Drop the cached manifest for `help_dir` (call after a regen). |
| `resolve_provenance` | `corpus_id: str, rel_path: str` | `ProvenanceResult` | Compute the staleness and provenance for one template. No network or LLM calls. |
| `regen_inputs` | `corpus_id: str, rel_path: str` | `RegenInputs` | Resolve the inputs needed to regenerate a template. |

### Routes

#### Batch (`attune_gui/routes/batch.py`)

| Function | Parameters | Returns | Description |
|----------|------------|------
