# attune-gui

Unified local GUI that drives the `attune-*` Python libraries (`attune-ai`,
`attune-rag`, `attune-author`, `attune-help`) through a FastAPI sidecar and a
React + Vite UI. Designed so you don't have to remember CLI flags, MCP tool
names, or sub-command paths to run common developer-workflow tasks.

## What it does

- **Commands mode** — run any of the 24 registered commands (RAG queries,
  doc generation, security audits, code reviews, memory recall/capture,
  release prep, …) from a 3-column form-driven UI. Async jobs with live
  status, structured results, and re-run with one click.
- **Living Docs mode** — proactively tracks documentation quality across
  three consumer personas (End User, Developer, Support). Scans your
  workspace, surfaces stale or low-quality docs, and gates releases on
  RAG faithfulness / accuracy thresholds.
- **Profiles** — Developer, Author, or Support. Each filters the command
  list to what's relevant for that role.

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
│     rag, ai, author,     │
│     help, profile,       │
│     living_docs          │
└──────────┬───────────────┘
           │
┌──────────▼───────────────┐
│  attune-rag, attune-ai,  │
│  attune-author,          │
│  attune-help             │
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
- `attune-ai` — workflow engine (install via `attune-gui[ai]`)

## License

Apache-2.0
