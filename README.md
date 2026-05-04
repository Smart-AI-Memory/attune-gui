# attune-gui

Local dashboard for the `attune-*` documentation family
(`attune-rag`, `attune-help`, `attune-author`). Server-rendered Jinja2
UI ("Cowork dashboard") backed by a FastAPI sidecar — ships clean via
PyPI with no `npm` step required to run.

## What it does

Sidebar nav with seven pages, each consuming the existing JSON API:

| Page | What it shows |
|------|---------------|
| **Health** | Cross-layer health (rag/help/author/gui versions) + corpus snapshot |
| **Templates** | Markdown templates with mtime staleness, tags, and a manual-pin toggle |
| **Specs** | Feature specs in `specs/` with phase + status badges. **+ New spec** bootstraps from `TEMPLATE.md`; **+ Design / + Tasks** inline; status dropdown in Preview |
| **Summaries** | Inline-editable `summaries.json` with overwrite warning |
| **Living Docs** | Workspace editor, scan trigger, document health, review queue, RAG quality bars |
| **Commands** | Run any registered command from a card grid (RAG queries, regen, maintain, …) |
| **Jobs** | Job history with per-feature progress, last-output column, Cancel button, auto-refresh |

Click any spec or template to open the **Preview / Edit** panel — server-side
Markdown rendering plus a raw `<textarea>` for editing.

## Template editor (`/editor`)

A first-class CodeMirror 6 editor for attune-help-style markdown templates.
Triggered by `attune-author edit <path>` or by navigating to
`/editor?corpus=<id>&path=<rel>`. Reads from / writes back to any registered
corpus on disk, with all retrieval/lint/refactor smarts coming from
[`attune-rag`](https://pypi.org/project/attune-rag/)'s `editor` toolkit.

Developer features:

| Feature | What it does |
|---------|---------------|
| **Schema-driven frontmatter form** | Reads `attune_rag.editor.load_schema()` at request time and renders typed inputs (select / chip-input / textarea / text). Unknown frontmatter keys are preserved verbatim. Raw-YAML toggle round-trips byte-for-byte. |
| **CodeMirror 6 + Lezer extension** | Composes the standard `@codemirror/lang-markdown` with a custom Lezer extension for YAML frontmatter delimiters, `## Depth N` markers, and `[[alias]]` refs (excluding fenced code, supporting `\[[` escape). |
| **Server-side lint** | 300 ms debounced POST to `/api/corpus/<id>/lint`. Diagnostics paint as squiggles in the editor + a clickable strip at the bottom. Local fast-path skips the round-trip for YAML parse errors. |
| **Tag + alias autocomplete** | Context-aware completions inside `tags:` / `aliases:` frontmatter fields and `[[…]]` body refs. Per-prefix LRU cache invalidates on WS file-change events. |
| **Per-hunk save modal** | `/api/corpus/<id>/template/diff` returns stable hunk ids; the modal shows each hunk with a checkbox and runs a *projected-state* lint so a partial save can't write known-broken frontmatter. Atomic save via `/template/save` (409 on `base_hash` mismatch → conflict mode). |
| **3-way merge conflict mode** | A WebSocket at `/ws/corpus/<id>?path=<rel>` pushes `file_changed` events from `watchfiles`. On conflict (or 409), a banner offers Reload / Keep / Resolve. Resolve uses [`node-diff3`](https://github.com/bhousel/node-diff3) for per-region accept-disk / accept-editor / keep-both. |
| **Cross-corpus rename refactor** | Right-click any tag/alias chip → "Rename …". `/api/corpus/<id>/refactor/rename/preview` returns a multi-file diff; apply is atomic across files (per-file tempfile + sequential rename + drift-detection rollback). 409 with `owning_path` on alias collisions. |
| **Corpus switcher** | Top-bar dropdown lists registered corpora (`~/.attune/corpora.json`). Search input materializes above 10 corpora. "+ Add corpus…" registers a new root via `/api/corpus/register`. Switching with unsaved edits prompts Save / Discard / Cancel. |
| **Generated-corpus advisory** | Persistent, non-dismissible banner when the active corpus has `kind: "generated"` — flags that edits will be overwritten on the next `attune-author maintain`. |
| **Read-only on duplicate session** | A second tab opening the same `(corpus, path)` receives a `duplicate_session` WS message and goes read-only with a banner — first tab keeps full control. |
| **Keyboard shortcuts** | `⌘/Ctrl-S` opens the save modal; `⌘/Ctrl-K` is reserved for the v2 command palette (currently surfaces a "coming in v2" toast). `beforeunload` warns on unsaved edits. |
| **Pre-bundled, no Node at install** | `editor-frontend/` is Vite + TypeScript; `make build-editor` produces a hashed-filename bundle into `sidecar/attune_gui/static/editor/` that's checked into the repo. PyPI consumers don't need `npm`. |

### Editor frontend dev loop

```bash
# In one shell — sidecar with auto-reload:
uv run attune-gui --port 8765 --reload

# In another — vitest watch (94 unit tests, ~2s):
cd editor-frontend && npm run test --watch

# Rebuild the bundle (deterministic; output committed):
make build-editor
```

The editor bundle is ~210 KB gzipped (budget: 600 KB). Schema and Lezer
grammar parse fixtures live in `editor-frontend/src/grammar/`; merge
correctness in `three-way-merge.test.ts`.

### Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/editor?corpus=<id>&path=<rel>` | Editor shell (Jinja) |
| GET    | `/api/editor/template-schema` | Frontmatter JSON Schema |
| GET    | `/api/corpus` | List registered corpora + active id |
| POST   | `/api/corpus/active` | Switch active corpus |
| POST   | `/api/corpus/register` | Add a new corpus root |
| POST   | `/api/corpus/resolve` | Map an absolute path → `(corpus_id, rel_path)` |
| GET    | `/api/corpus/<id>/template?path=<rel>` | Read template + base hash + mtime |
| POST   | `/api/corpus/<id>/template/diff` | Compute unified-diff hunks vs disk |
| POST   | `/api/corpus/<id>/template/save` | Atomic save (`base_hash` 409-guarded) |
| POST   | `/api/corpus/<id>/lint` | Lint a template body |
| GET    | `/api/corpus/<id>/autocomplete?kind=tag\|alias&prefix=…` | Autocomplete |
| POST   | `/api/corpus/<id>/refactor/rename/preview` | Multi-file rename plan |
| POST   | `/api/corpus/<id>/refactor/rename/apply` | Atomic rename across files |
| WS     | `/ws/corpus/<id>?path=<rel>` | `file_changed` + `duplicate_session` push |

> Looking for AI dev workflows (code review, security audits, refactor
> planning, multi-agent orchestration)? Those live in
> [`attune-ai`](https://pypi.org/project/attune-ai/) — a separate
> product. attune-gui is deliberately scoped to the documentation lifecycle.

## Quickstart

```bash
pip install attune-gui
attune-gui
# Or pick a specific port:
attune-gui --port 8765
```

The sidecar binds to `127.0.0.1`, prints `SIDECAR_URL=…`, and serves the
new dashboard at `/`. Use `--open` to auto-open your browser.

## Configuration

### `.env` auto-loading

The sidecar loads `KEY=value` lines from the first `.env` it finds, in this order:

1. `./.env` (current working directory)
2. `<repo-root>/.env` (the attune-gui checkout root)
3. `~/.attune-gui/.env`
4. `~/.attune/.env`

Existing real env values are preserved; empty/whitespace-only values are
treated as unset and overwritten. Common keys:

```
ANTHROPIC_API_KEY=sk-ant-…   # required for author.regen / author.maintain
ATTUNE_SPECS_ROOT=/path/to/your/repo/specs
ATTUNE_WORKSPACE=/path/to/your/project
```

### Workspace + specs root

| Variable | Default | Purpose |
|----------|---------|---------|
| `ATTUNE_WORKSPACE` | persisted to `~/.attune-gui/config.json` | The project the sidecar watches (Living Docs, templates) |
| `ATTUNE_SPECS_ROOT` | `<workspace>/specs/`, then walks up from cwd | Where the **Specs** page reads from |

Workspace can also be set via **Living Docs → Workspace** in the UI; it
persists to `~/.attune-gui/config.json` and survives restarts.

## Development

```bash
git clone https://github.com/Smart-AI-Memory/attune-gui
cd attune-gui
uv sync
uv run attune-gui --port 8765 --reload
```

Templates auto-reload — edit anything under `sidecar/attune_gui/templates/`
and refresh the browser. Python code changes reload automatically with
`--reload`.

### Tests

```bash
uv run pytest                # 124 tests, ~2s
uv run ruff check .          # lint
```

## Architecture

```
┌──────────────────────────────────────┐
│  Cowork dashboard (Jinja2)  /        │
└──────────────────┬───────────────────┘
                   │  /api/*
┌──────────────────▼───────────────────┐
│  FastAPI sidecar — 127.0.0.1         │
│  ├─ routes/system, rag, help, …      │
│  ├─ routes/cowork_health             │
│  ├─ routes/cowork_specs              │
│  ├─ routes/cowork_templates          │
│  ├─ routes/cowork_files              │
│  └─ routes/cowork_pages  (HTML)      │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│  attune-rag · attune-help            │
│  attune-author[ai]                   │
└──────────────────────────────────────┘
```

## Security notes

This is a **single-user, local-only** app. Not designed for multi-user
deployment, not hardened against a motivated attacker on the same machine.

- Binds **only** to `127.0.0.1` — not reachable from other machines
- An `Origin` header guard rejects browser requests from non-localhost origins
- Mutating endpoints require the `X-Attune-Client` header to match a
  per-process token (served from `/api/session/token`)
- File API enforces a path-traversal guard against three named roots
  (`templates`, `specs`, `summaries`); writes outside those roots return 400

## Related packages

- [`attune-rag`](https://pypi.org/project/attune-rag/) — RAG pipeline
- [`attune-help`](https://pypi.org/project/attune-help/) — help runtime
- [`attune-author`](https://pypi.org/project/attune-author/) — doc authoring
- [`attune-gui-plugin`](https://github.com/Smart-AI-Memory/attune-gui-plugin) — Claude Code plugin that launches the dashboard inside Cowork's preview pane
- [`attune-ai`](https://pypi.org/project/attune-ai/) — separate AI dev workflow product (not used by attune-gui)

## License

Apache-2.0
