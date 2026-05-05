---
type: task
feature: template-editor
depth: task
generated_at: 2026-05-05T02:17:29.906501+00:00
source_hash: 58fe95b4d95e5e9d2b0dab5826fdd560c2f368a7e93f74ec1eeac297f09d7d78
status: generated
---

# Work with template editor

Use the template editor when you need to modify or create attune-help markdown templates in a schema-driven environment with real-time validation and cross-corpus refactoring capabilities.

## Prerequisites

- Access to the project source code
- The attune-gui sidecar running (serves the editor at `/editor`)
- A registered corpus in `~/.attune/corpora.json`

## Steps

1. **Start the editor interface.**
   Navigate to `http://localhost:<port>/editor` where the sidecar is running. The editor loads with a CodeMirror 6 interface for markdown editing.

2. **Select your working corpus.**
   Use the corpus switcher in the top bar to choose which documentation corpus you want to edit. The editor will warn you if you have unsaved changes before switching.

3. **Open or create a template file.**
   Click the directory picker to browse your corpus files, or create a new template using the schema-driven frontmatter form. The editor validates YAML frontmatter against the template type schema.

4. **Edit the template content.**
   Write your markdown content in the main editor. The system provides:
   - Real-time lint feedback via debounced server-side validation
   - Tag and alias autocomplete for frontmatter fields
   - Syntax highlighting for attune-help markdown extensions

5. **Save your changes.**
   Use the per-hunk save modal to review and commit specific changes. The editor shows a diff view of your modifications before saving.

6. **Handle file conflicts (if needed).**
   If another process modifies the file while you're editing, the editor enters 3-way merge conflict mode via WebSocket notifications. Resolve conflicts using the visual merge interface.

## Verify success

- Your template appears in the corpus file browser
- The frontmatter validates without lint errors
- The template renders correctly when accessed through the help system
- File changes are reflected on disk in your corpus directory

## Key components

The editor consists of:

**Frontend** (TypeScript/Vite bundle):
- `main.ts` — Application entry point
- `editor.ts` — CodeMirror configuration
- `frontmatter-form.ts` — Schema-driven YAML editing
- `save-flow.ts` — Change persistence workflow
- `three-way-merge.ts` — Conflict resolution interface

**Backend** (Python routes):
- `editor_corpora.py` — Corpus registry management
- `editor_session.py` — Per-tab editing state
- `editor_lint.py` — Server-side validation
- `editor_ws.py` — WebSocket file change notifications
