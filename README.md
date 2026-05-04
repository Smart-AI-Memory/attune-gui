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

> Prefer the React UI? It's still bundled and reachable at
> `/legacy/`. Both surfaces talk to the same FastAPI sidecar.

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

For HMR work on the React UI at `/legacy/`:

```bash
cd ui && npm install && cd ..
./scripts/dev.sh   # starts sidecar + Vite dev server
```

### Tests

```bash
uv run pytest                # 105 tests, ~2s
uv run ruff check .          # lint
```

## Architecture

```
┌──────────────────────────────────────┐
│  Cowork dashboard (Jinja2)  /        │
│  Legacy React UI            /legacy/ │
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
