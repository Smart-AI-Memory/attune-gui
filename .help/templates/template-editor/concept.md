---
type: concept
name: template-editor-concept
feature: template-editor
depth: concept
generated_at: 2026-05-23T11:23:11.938567+00:00
source_hash: ec1d4153a8e6969223933f4de93941bb8c47c96c480b5a3605f822a911923af1
status: generated
---

# Template Editor

The template editor is a browser-based editing environment, served at `/editor` by the attune-gui sidecar, that lets you read, edit, lint, and save attune-help markdown templates without leaving the tool.

## What the editor does

The editor combines a CodeMirror 6 text surface with server-side intelligence. As you type, the sidecar runs debounced lint checks (via `lint` in `routes.editor_lint`) and returns `DiagnosticModel` annotations inline. Tag and alias autocomplete fires against the active corpus so you can reference existing vocabulary without switching windows. A schema-driven frontmatter form — backed by the `template_schema` route — validates the YAML header before you save.

Saving is surgical: a diff of your draft against the on-disk file is computed by `diff_template`, and a per-hunk modal lets you choose which changes to write. If the file changes on disk while your tab is open, a WebSocket push from `corpus_ws` triggers a 3-way merge conflict view rather than silently overwriting your work.

Rename refactoring works across corpora: `rename_preview` shows you every affected reference before `rename_apply` commits the change.

## The four runtime layers

Understanding how the pieces fit together makes the editor's behavior predictable.

**1. Corpus registry** — A `Registry` object (an in-memory snapshot of `~/.attune/corpora.json`) holds the list of `CorpusEntry` records. Each `CorpusEntry` carries an `id`, a human-readable `name`, a filesystem `path`, a `kind` (`'source'` by default), and a `warn_on_edit` flag that triggers an advisory banner when you open files in that corpus. You register a new corpus with `register(name, path)` and switch the active one with `set_active(corpus_id)`. The corpus switcher in the UI guards against switching away with unsaved edits.

**2. Editor session** — Each open tab corresponds to one `EditorSession`, keyed to an `(abs_path, corpus)` pair. When a tab opens, `EditorSession.load(abs_path)` reads the file, stores `base_text` and a 16-character `base_hash` (SHA-256 prefix from `hash_text`), and starts a background poller at `poll_interval` (default `0.1` seconds). Calling `update_draft(text)` records your in-progress edits as `draft_text`. `matches_base()` tells the session — and the UI — whether your draft diverges from what was on disk when the tab loaded. `next_event()` surfaces file-change notifications to the WebSocket layer.

**3. Sidecar portfile** — The sidecar process advertises its `pid`, `port`, and `token` by writing a `PortfileData` record via `write_portfile`. Consumers call `read_portfile()` to discover the running instance and authenticate requests. `is_portfile_stale()` checks whether the recorded PID is still alive (`is_pid_alive`), so a crashed sidecar doesn't leave a phantom portfile. The `portfile_context` context manager handles the full write-then-delete lifecycle. The `/healthz` route requires the same `token`, giving clients a lightweight liveness check.

**4. HTTP and WebSocket routes** — The corpus routes (`routes.editor_corpus`) expose `list_corpora`, `set_active`, `register`, and `resolve` as JSON endpoints. The template routes (`routes.editor_template`) expose `get_template`, `diff_template`, and `save_template`. Lint and autocomplete live in `routes.editor_lint`. Real-time file-change events and rename operations flow over the WebSocket route in `routes.editor_ws`.

## When the `warn_on_edit` flag matters

When you call `register` with `warn_on_edit=True`, or when the registry file already records that flag for a corpus, the editor displays a persistent advisory banner on every file in that corpus. This is useful for corpora that are generated or otherwise managed outside the editor — the banner signals that manual edits may be overwritten by an upstream process.

## Static asset delivery

The frontend (TypeScript + Vite) is pre-bundled into `sidecar/attune_gui/static/editor/` and shipped inside the PyPI package. PyPI consumers do not need Node.js installed; the sidecar serves the compiled assets directly from `routes.editor_pages`.
