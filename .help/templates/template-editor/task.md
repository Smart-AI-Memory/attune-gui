---
type: task
name: template-editor-task
feature: template-editor
depth: task
generated_at: 2026-06-23T04:13:38.188486+00:00
source_hash: 407c7dc6dcfaefcca257d93599116ce8bf9cd491c25de410e9dd8361366327ef
status: generated
---

# Work with the template editor

Use the template editor when you need to open, edit, and save attune-help markdown templates through the sidecar UI at `/editor`, with schema-validated frontmatter, live lint feedback, per-hunk saving, and cross-corpus rename support.

## Prerequisites

- The `attune-gui` sidecar is installed and running.
- At least one corpus directory is registered in `~/.attune/corpora.json`.
- You have read access to the corpus path you want to edit.

## Register a corpus

Before you can open a template, the editor must know which directory to load it from.

1. Call `register()` from `attune_gui.editor_corpora`, passing a display name and an absolute path to a corpus directory:

   ```python
   from attune_gui.editor_corpora import register

   entry = register("My Corpus", "/abs/path/to/corpus", kind="source")
   print(entry.id)   # use this id in subsequent calls
   ```

   `register()` raises `ValueError` if the path is not an existing directory.

2. Confirm the entry was saved by calling `load_registry()` and checking that your corpus appears in `Registry.corpora`:

   ```python
   from attune_gui.editor_corpora import load_registry

   reg = load_registry()
   print([c.name for c in reg.corpora])
   ```

## Set the active corpus

1. Call `set_active()` with the corpus `id` returned by `register()`:

   ```python
   from attune_gui.editor_corpora import set_active

   active = set_active(entry.id)
   print(active.name)
   ```

   `set_active()` raises `KeyError` if the corpus id is not recognised. Call `list_corpora()` to inspect all registered ids.

2. Verify the change by calling `get_active()` and confirming it returns the expected `CorpusEntry`:

   ```python
   from attune_gui.editor_corpora import get_active

   assert get_active().id == entry.id
   ```

## Open and edit a template

1. Navigate to `/editor?corpus=<corpus_id>&path=<relative_path>` in your browser. The editor page is served by `editor_page()` in `routes.editor_pages`.

2. Edit the frontmatter fields in the schema-driven form. The form schema is served by `template_schema()` in `routes.editor_schema`.

3. Edit the markdown body in the CodeMirror panel. Lint diagnostics appear automatically; they are provided by `lint()` in `routes.editor_lint`.

4. Use tag and alias autocomplete as you type. Completions are provided by `autocomplete()` in `routes.editor_lint` and respect the `prefix` you have typed.

## Save a template

1. Click **Save** to open the per-hunk save modal. The diff is computed by `diff_template()` in `routes.editor_template`, which returns a `DiffResponse` containing `HunkModel` objects.

2. Select the hunks you want to keep, then confirm. The editor calls `save_template()` in `routes.editor_template` with a `SaveRequest` and receives a `SaveResponse`.

3. If another process edited the file while you were working, the WebSocket connection (`corpus_ws` in `routes.editor_ws`) pushes a `file_changed` event. The editor enters three-way merge conflict mode. Resolve each conflict and save again.

## Rename a template across corpora

1. Use the rename modal to preview the impact of a rename before applying it. The preview is provided by `rename_preview()` in `routes.editor_ws`.

2. After reviewing the affected files, apply the rename with `rename_apply()` in `routes.editor_ws`.

## Start and stop an editor session programmatically

If you are driving the editor from Python rather than a browser, use `EditorSession` from `attune_gui.editor_session`:

1. Load a session for a file:

   ```python
   from pathlib import Path
   from attune_gui.editor_session import EditorSession

   session = EditorSession.load(Path("/abs/path/to/template.md"))
   session.start()
   ```

2. Push draft text as the user types:

   ```python
   session.update_draft(new_text)
   ```

3. Check whether the in-memory draft still matches the on-disk file:

   ```python
   in_sync = session.matches_base()
   ```

4. Poll for file-system events:

   ```python
   event = session.next_event()
   ```

5. Stop the session when done:

   ```python
   session.stop()
   ```

## Verify the editor is working

- `GET /healthz?token=<token>` returns `{"status": "ok"}`. This endpoint is served by `healthz()` in `routes.editor_health`.
- `list_corpora()` returns a non-empty list containing your registered corpus.
- `get_active()` returns the `CorpusEntry` you set with `set_active()`.
- `resolve_path()` returns a `(CorpusEntry, relative_path)` tuple for any absolute path inside a registered corpus directory, confirming the registry is consistent.
