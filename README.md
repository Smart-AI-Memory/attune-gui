# attune-gui

Local FastAPI sidecar + HTML/JS UI that drives the **attune-rag**,
**attune-author**, and (later) **attune-ai** Python libraries from
a browser tab.

- **v1 architecture ("Option C"):** uvicorn serves the sidecar on
  127.0.0.1, the UI runs in your default browser and talks to it
  via `fetch()`. One process, no external services, no Cowork.
- **Forward path ("Option E"):** the same sidecar + UI can later be
  wrapped in Tauri for a native installable app without a rewrite
  — the Rust core just spawns this sidecar and points a webview at
  the URL it prints on stdout.

See the full plan at
[attune-ai/.claude/plans/attune-gui-2026-04-24.md](../attune-ai/.claude/plans/attune-gui-2026-04-24.md).

## Status: **M1** — sidecar skeleton + one tool wired end-to-end

Currently exposes:

- `POST /api/rag/query` — run retrieval against the attune-help corpus.
- `GET /api/rag/corpus-info` — stats about the loaded corpus.
- `GET /api/health` — sidecar health + version.
- `GET /api/session/token` — per-process token the UI echoes on
  mutating calls as a CSRF guard.

The UI is one HTML file at `ui/src/index.html`: query input, k knob,
retrieval results, collapsible augmented-prompt panel.

## Install

```bash
uv venv
uv pip install -e '.[dev]'
# or, with attune-ai included (pulls a large dep tree):
uv pip install -e '.[dev,ai]'
```

## Run

```bash
./scripts/dev.sh
```

Or manually:

```bash
.venv/bin/python -m attune_gui.main --reload --open
```

The sidecar picks a free port and prints `SIDECAR_URL=http://127.0.0.1:<port>`
on the first stdout line. `scripts/dev.sh` reads that and opens your
default browser. `--open` does the same when you run the module directly.

## Security notes (v1)

- Binds **only** to `127.0.0.1` — not reachable from other machines.
- CORS allows any `localhost`/`127.0.0.1` origin on any port.
- An `Origin` header guard rejects browser requests from non-localhost
  origins.
- Mutating endpoints require the `X-Attune-Client` header to match
  a per-process token (served from `/api/session/token`).

This is a **single-user, local-only** app. Not designed for
multi-user deployment, not hardened against a motivated attacker
on the same machine.

## Project layout

```
attune-gui/
├── pyproject.toml
├── sidecar/
│   ├── attune_gui/
│   │   ├── __init__.py
│   │   ├── main.py         # uvicorn entry, CLI flags, port picking
│   │   ├── app.py          # FastAPI app factory + UI mount
│   │   ├── models.py       # pydantic schemas
│   │   ├── security.py     # origin guard + session token
│   │   └── routes/
│   │       ├── rag.py      # attune_rag endpoints
│   │       └── system.py   # health + session token
│   └── tests/
├── ui/
│   └── src/
│       └── index.html      # single-file UI (no build step)
└── scripts/
    └── dev.sh              # start sidecar + open browser
```

## License

Apache 2.0.
