---
type: concept
name: template-editor-concept
feature: template-editor
depth: concept
generated_at: 2026-06-23T04:13:38.182237+00:00
source_hash: 407c7dc6dcfaefcca257d93599116ce8bf9cd491c25de410e9dd8361366327ef
status: generated
---

# Template Editor

The template editor is a browser-based CodeMirror 6 environment, served at `/editor` by the attune-gui sidecar, for authoring and refactoring attune-help-style markdown templates without requiring a Node.js installation on the user's machine.

## What the editor does

The editor bundles everything needed to work with a corpus of templates in one place:

- A schema-driven frontmatter form that validates fields as you type
- Debounced server-side lint with tag and alias autocomplete (up to 500 results, configurable via the `limit` query parameter)
- A per-hunk save modal backed by `diff_template` and `save_template`
- 3-way merge conflict mode triggered by `file_changed` pushes over the WebSocket at `corpus_ws`
- Cross-corpus rename refactoring via `rename_preview` and `rename_apply`
- A corpus switcher with an unsaved-edits guard
- A directory picker for registering new corpora

The frontend is pre-bundled with Vite and TypeScript into `sidecar/attune_gui/static/editor/`, so PyPI consumers don't need Node.

## Core data model

Three dataclasses form the backbone of the editor's runtime state.

**`Registry`** is the in-memory snapshot of `~/.attune/corpora.json`. It holds an optional `active` corpus ID and the full list of `CorpusEntry` objects. You load it with `load_registry()` and write it back with `save_registry(reg)`, which creates `~/.attune/` if it doesn't exist yet.

**`CorpusEntry`** represents a single registered corpus. Its fields tell the editor where to find the files (`path`), how to label it (`name`, `id`), what role it plays (`kind`, defaulting to `'source'`), and whether to warn the user before any edit (`warn_on_edit`). You register a new corpus with `register(name, path)`, which raises `ValueError` if the path is not a directory. You switch the active corpus with `set_active(corpus_id)`, which raises `KeyError` if the ID is unknown.

**`EditorSession`** tracks the state of a single open tab — one `(corpus, path)` pair. It stores the text that was on disk when the tab opened (`base_text`, `base_hash`) and the current unsaved content (`draft_text`). Call `update_draft(text)` whenever the user types. Call `matches_base()` to decide whether the unsaved-edits guard should fire before a corpus switch. The session also polls the file on disk at `poll_interval` (default 0.1 s) and emits events you read with `next_event()` — this is what feeds the 3-way merge conflict mode when another process writes the file.

## Sidecar lifecycle

The editor runs inside the attune-gui sidecar process. Startup and shutdown are coordinated through a portfile — a small file containing the sidecar's `pid`, `port`, and `token` (see `PortfileData`). The `portfile_context` context manager writes the portfile on entry and deletes it on exit, so a stale portfile from a crashed process is detectable via `is_portfile_stale()` and `is_pid_alive(pid)`. The `/healthz` route requires the same `token` stored in the portfile, which prevents stale clients from talking to a restarted sidecar.

## How the pieces connect

When you open a template in the browser, the following chain runs:

1. The frontend calls `editor_page` to render the shell, then fetches `get_template(corpus_id, path)` to populate the editor.
2. An `EditorSession` is created for the tab. The session's background poller watches the file on disk.
3. The WebSocket at `corpus_ws` forwards `file_changed` events from the session to the browser, triggering the merge UI when disk content diverges from `base_hash`.
4. As you edit, the browser sends text to `lint(corpus_id, req)` for diagnostics and to `autocomplete` for tag or alias suggestions.
5. When you save, `diff_template` computes the hunks shown in the save modal, and `save_template` writes the accepted changes to disk.
6. A rename operation calls `rename_preview` first (shows affected files), then `rename_apply` to commit.

The corpus switcher in the toolbar calls `set_active(corpus_id)` and re-runs this chain for the new corpus. `resolve_path(abs_path)` lets the editor identify which registered corpus owns any given file path, which is used when opening a template from an external file picker.
