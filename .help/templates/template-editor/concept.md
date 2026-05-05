---
type: concept
feature: template-editor
depth: concept
generated_at: 2026-05-05T02:17:15.312701+00:00
source_hash: 58fe95b4d95e5e9d2b0dab5826fdd560c2f368a7e93f74ec1eeac297f09d7d78
status: generated
---

# Template Editor

The template editor is a web-based CodeMirror 6 interface that lets you author and edit attune-help markdown templates with real-time validation and corpus-aware file management.

## Core capabilities

The editor provides a complete authoring environment for template development:

- **Schema-driven editing** — YAML frontmatter forms that validate template metadata as you type
- **Real-time feedback** — Server-side linting with debounced validation to catch structural errors
- **Smart autocomplete** — Context-aware suggestions for template tags and cross-reference aliases
- **Multi-corpus workflow** — Switch between different documentation corpora with unsaved-change protection
- **Conflict resolution** — 3-way merge interface when files change on disk during editing sessions
- **Cross-template operations** — Rename templates across an entire corpus with automatic reference updates

## Session management

Each editing tab maintains its own `EditorSession` that tracks file state independently:

- **Base tracking** — The editor remembers the original file content when you open it
- **Change detection** — WebSocket notifications alert you when someone else modifies the file
- **Optimistic updates** — Your changes are hashed and compared to detect conflicts before saving
- **Per-hunk saves** — You can save specific sections of a template rather than the entire file

## Corpus registry

The editor works with a persistent registry of documentation corpora stored in `~/.attune/corpora.json`:

- **Multiple corpora** — Register and switch between different documentation collections
- **Path resolution** — The editor automatically detects which corpus owns a file you're editing
- **Active corpus** — One corpus is marked active for new template creation
- **Edit warnings** — Some corpora can be marked to warn before allowing modifications

## File management integration

The editor integrates with the broader attune ecosystem through several interfaces:

- **Sidecar server** — Runs as part of the attune-gui sidecar at `/editor`
- **Healthcheck endpoint** — `/healthz` validates that the editor's portfile is current
- **Directory corpus loading** — Instantiates full corpus objects for file operations
- **WebSocket updates** — Real-time notifications when files change outside the editor

The entire interface is pre-built with Vite and TypeScript, bundled into the sidecar's static assets so you don't need Node.js to use it.
