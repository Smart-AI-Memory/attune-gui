---
type: task
name: template-editor-task
feature: template-editor
depth: task
generated_at: 2026-05-23T11:23:11.945592+00:00
source_hash: ec1d4153a8e6969223933f4de93941bb8c47c96c480b5a3605f822a911923af1
status: generated
---

# Work with the template editor

Use the template editor when you need to create or modify attune-help-style markdown templates through the sidecar's `/editor` interface, with schema-validated frontmatter, live lint feedback, and per-hunk saves.

## Prerequisites

- The attune-gui sidecar is running and a portfile is readable via `read_portfile()` in `attune_gui.editor_sidecar`
- At least one corpus directory is registered and accessible via `list_corpora()` in `attune_gui.editor_corpora`
- You have a valid bearer token (stored in `PortfileData.token`) to authenticate requests to `/healthz`

## Register a corpus

Before editing templates, the editor needs to know which directory contains them.

1. Call `register(name, path)` from `attune_gui.editor_corpora`, passing the corpus display name and its absolute directory path.

   ```python
   from attune_gui.editor_corpora import register
   entry = register("My Templates", "/path/to/templates")
   ```

   `register` raises `ValueError` if the path is not an existing directory. On success it returns a `CorpusEntry` with fields `id`, `name`, `path`, `kind`, and `warn_on_edit`.

2. Call `set_active(entry.id)` to make this corpus the default in the UI.

   ```python
   from attune_gui.editor_corpora import set_active
   set_active(entry.id)
   ```

   `set_active` raises `KeyError` if the corpus ID is not in the registry.

3. Call `save_registry(load_registry())` to persist the change to `~/.attune/corpora.json`.

   ```python
   from attune_gui.editor_corpora import load_registry, save_registry
   save_registry(load_registry())
   ```

**Verify:** Call `get_active()` — it should return the `CorpusEntry` you just registered.

## Open and edit a template

1. Navigate to `/editor?corpus=<corpus_id>&path=<relative_path>` in your browser. The `editor_page` route renders the editor UI for that corpus and path.

2. Edit the frontmatter fields in the schema-driven form. The form validates against the schema served by `template_schema()` (`routes.editor_schema`).

3. Edit the markdown body in the CodeMirror 6 editor. Lint diagnostics appear automatically; they are powered by `lint(corpus_id, req)` in `routes.editor_lint`. Tag and alias suggestions come from `autocomplete(corpus_id, kind, prefix)`.

4. When you are ready to save, open the save modal. It shows a per-hunk diff produced by `diff_template(corpus_id, req)` (`routes.editor_template`). Review each hunk, then confirm.

5. Click **Save** to call `save_template(corpus_id, req)`. The route returns a `SaveResponse` confirming the write.

**Verify:** After saving, call `get_template` (`routes.editor_template`) with the same `corpus_id` and `path`. The returned `TemplateResponse` should reflect your changes. Alternatively, confirm that `EditorSession.matches_base()` returns `True` after reloading the session with `EditorSession.load(abs_path)`.

## Handle a file-changed conflict

If the file on disk changes while you are editing, the WebSocket endpoint `corpus_ws` (`routes.editor_ws`) pushes a `file_changed` event to the browser.

1. Call `EditorSession.next_event()` to read the incoming event from the session.
2. The editor enters three-way merge conflict mode automatically. Resolve each conflict in the diff gutter.
3. Save the resolved content using `save_template`.

**Verify:** After saving, `EditorSession.current_disk_hash()` should match `hash_text` applied to the saved file content (`attune_gui.editor_session`).

## Rename a template across corpora

1. In the editor UI, open the rename modal. It calls `rename_preview(corpus_id, req)` (`routes.editor_ws`) to show all files that reference the current template.
2. Review the preview. If the changes are correct, confirm to call `rename_apply(corpus_id, req)`.

**Verify:** `rename_apply` returns a dict summarising the files updated. Check that every path listed now contains the new name.

## Switch corpora with unsaved edits

The corpus switcher checks for unsaved edits before switching. If `EditorSession.matches_base()` returns `False`, the UI displays an unsaved-edits guard dialog.

1. Save or discard your current edits.
2. Select the target corpus in the switcher. The switcher calls `set_active` with the new corpus ID.

**Verify:** `get_active()` returns the newly selected `CorpusEntry`.
