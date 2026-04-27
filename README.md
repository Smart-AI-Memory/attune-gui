# attune-gui

Local **Living Docs** dashboard for the `attune-*` documentation family
(`attune-rag`, `attune-help`, `attune-author`). FastAPI sidecar +
React + Vite UI. Designed so you don't have to remember CLI flags or
sub-command paths to author, query, and maintain your project's docs.

## What it does

- **Commands mode** — run the 10 registered commands (RAG queries,
  template generation, staleness checks, doc maintenance, help lookup
  / search, …) from a 3-column form-driven UI. Async jobs with live
  status, structured results, and re-run with one click.
- **Living Docs mode** — proactively tracks documentation quality
  across three consumer personas (End User, Developer, Support).
  Scans your workspace, surfaces stale or low-quality docs, and gates
  releases on RAG faithfulness / accuracy thresholds.
- **Profiles** — Developer, Author, or Support. Each filters the
  command list to what's relevant for that role.

> Looking for AI dev workflows (code review, security audits, refactor
> planning, multi-agent orchestration)? Those live in
> [`attune-ai`](https://pypi.org/project/attune-ai/) — a separate
> product with its own CLI/plugin/MCP entry points. attune-gui is
> deliberately scoped to the documentation lifecycle.

## Quickstart

```bash
pip install attune-gui
attune-gui
# Or pick a specific port:
attune-gui --port 8765
```

The sidecar binds to `127.0.0.1`, opens your browser, and serves the React UI
from inside the package. No external services required.

For dev work against a local checkout (HMR + faster iteration):

```bash
git clone https://github.com/Smart-AI-Memory/attune-gui
cd attune-gui
uv venv && uv pip install -e '.[dev]'
cd ui && npm install && cd ..
./scripts/dev.sh   # starts sidecar on :8765 + Vite dev on :5173
```

## Architecture

```
┌──────────────────────────┐
│  React + Vite UI         │  ← served from package, or Vite dev (HMR)
│  (Commands | Living Docs)│
└──────────┬───────────────┘
           │  /api/*
┌──────────▼───────────────┐
│  FastAPI sidecar         │
│  127.0.0.1:8765          │
│  ├─ commands.py registry │
│  ├─ jobs.py              │
│  └─ routes/              │
│     rag, help, author,   │
│     profile, jobs,       │
│     living_docs          │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│  attune-rag,             │
│  attune-help,            │
│  attune-author           │
└──────────────────────────┘
```

## Security notes

This is a **single-user, local-only** app. Not designed for multi-user
deployment, not hardened against a motivated attacker on the same machine.

- Binds **only** to `127.0.0.1` — not reachable from other machines
- An `Origin` header guard rejects browser requests from non-localhost origins
- Mutating endpoints require the `X-Attune-Client` header to match a
  per-process token (served from `/api/session/token`)

## Related packages

- [`attune-rag`](https://pypi.org/project/attune-rag/) — RAG pipeline
- [`attune-help`](https://pypi.org/project/attune-help/) — help runtime
- [`attune-author`](https://pypi.org/project/attune-author/) — doc authoring
- [`attune-ai`](https://pypi.org/project/attune-ai/) — separate AI dev workflow product (not used by attune-gui)

## License

Apache-2.0
