# Cowork Dashboard Revival — Review

**Branch:** `feat/cowork-dashboard-revival`
**What:** Server-rendered Jinja2 dashboard merging the Cowork design (clean
sidebar, soft badges, generous whitespace) with the React UI's feature set
(Living Docs, Commands, Jobs).

---

## What you can do right now

```bash
cd ~/attune/attune-gui
git checkout feat/cowork-dashboard-revival
ATTUNE_SPECS_ROOT=~/attune/specs uv run attune-gui --port 8765 --open
```

Then visit `http://127.0.0.1:8765/` — you'll be redirected to `/dashboard`
(Health). The legacy React UI is preserved at `http://127.0.0.1:8765/legacy/`.

Also reachable inside the Cowork preview pane via the existing
`/attune-gui` plugin command.

---

## Page map

| Path | What it shows |
|------|---------------|
| `/dashboard` | Cross-layer health (rag/help/author/gui versions) + corpus card |
| `/dashboard/templates` | Markdown templates table with **manual pin toggle** + filter chips |
| `/dashboard/specs` | Feature specs with phase + status badges, links to each phase file |
| `/dashboard/summaries` | Inline-editable `summaries.json` with overwrite warning |
| `/dashboard/preview?root=…&path=…` | Two-tab Preview/Edit panel (server-rendered MD → HTML) |
| `/dashboard/living-docs` | Health/Documents/Review Queue + workspace editor + scan button + RAG quality bars |
| `/dashboard/commands` | Available commands as cards, "Run" button starts a job |
| `/dashboard/jobs` | Job history with status badges |
| `/legacy/` | The React/Vite UI (unchanged) |

---

## API surface (new)

All under `/api/cowork/`:

- `GET  /api/cowork/layers` — `importlib.metadata` probe per layer
- `GET  /api/cowork/corpus` — workspace + template count + summaries presence
- `GET  /api/cowork/specs` — list of feature specs with inferred phase + status
- `GET  /api/cowork/templates` — template list with staleness + manual flag
- `GET  /api/cowork/files/raw/{root}/{path}` — read file (returns raw + manual flag)
- `PUT  /api/cowork/files/raw/{root}/{path}` — atomic write
- `GET  /api/cowork/files/rendered/{root}/{path}` — markdown → HTML fragment
- `POST /api/cowork/files/pin/{root}/{path}` — toggle the `manual: true` flag

All existing JSON routes (`/api/health`, `/api/jobs`, `/api/living-docs/...`
etc.) are untouched and still work — both the new dashboard and the legacy
React UI consume them.

---

## How the design choice played out

The cowork-dashboard spec was already approved with the goal of dropping
React entirely. That's the right call long-term — but right now the React UI
holds active functionality (Living Docs Documents/Queue, Commands, Jobs)
that wasn't in the original spec scope. Rather than re-implement everything
in vanilla JS in one shot, this branch:

1. **Builds the Jinja2 dashboard fresh** following the spec's design.
2. **Adds three more sections** the original spec didn't anticipate but are
   now real product surface:
   - Living Docs (Health stats, Documents table with regenerate, Review Queue
     with approve/revert)
   - Commands (run any registered command from a card grid)
   - Jobs (history with status badges)
3. **Keeps the React UI alive at `/legacy/`** so nothing is lost during the
   transition. Once you're confident the Jinja dashboard covers everything
   you need, deleting `ui/` is a separate, safe commit.

The sidebar nav reflects this expanded scope:
**Health · Templates · Specs · Summaries · Living Docs · Commands · Jobs**

---

## Aesthetic decisions (to match the screenshot you liked)

- **Dark sidebar, light canvas** (`#14161c` / `#fafafa`) — same contrast as
  the screenshot.
- **Soft pill badges** — pastel backgrounds with bold ink colours (e.g.
  green `#dcfce7` on `#15803d` for "ok").
- **Monospace for paths** — file paths and feature names render in
  ui-monospace at `0.85em`.
- **Tight tables** — 12px row padding, single-pixel borders, hover
  highlight in `#fafafb`.
- **Subtle cards** — 1px border, 1px shadow, 10px radius. No rounded-2xl
  inflation.
- **Inline accent** for primary actions (`#4f46e5`), used sparingly.
- **Toast feedback** at bottom-right for save/pin/scan results — same colour
  language as the badges.

---

## Files changed

```
attune-gui/
  pyproject.toml                                    # +3 deps
  sidecar/attune_gui/
    app.py                                          # mount cowork routes + /legacy
    routes/
      cowork_health.py     [NEW] cross-layer health probe
      cowork_specs.py      [NEW] spec listing with phase inference
      cowork_templates.py  [NEW] template listing with staleness + manual
      cowork_files.py      [NEW] read/write/render/pin file API
      cowork_pages.py      [NEW] Jinja2 HTML page routes (8 pages)
    templates/
      base.html            [NEW] sidebar + main + toast layout
      health.html          [NEW]
      templates.html       [NEW]
      specs.html           [NEW]
      summaries.html       [NEW]
      preview.html         [NEW] tabbed preview/edit
      living_docs.html     [NEW]
      commands.html        [NEW]
      jobs.html            [NEW]
    static_cw/
      style.css            [NEW] design tokens + components

  REVIEW.md                                         # this file
```

No existing files were deleted. The React UI's `ui/` directory and the
sidecar's `static/` mount remain intact.

---

## Smoke test results

All 14 endpoints return **200**. Lint passes (`ruff check`). Full test:

| Endpoint | Status |
|----------|--------|
| `/dashboard` | 200 |
| `/dashboard/templates` | 200 |
| `/dashboard/specs` | 200 |
| `/dashboard/summaries` | 200 |
| `/dashboard/living-docs` | 200 |
| `/dashboard/commands` | 200 |
| `/dashboard/jobs` | 200 |
| `/dashboard/preview?root=specs&path=...` | 200 |
| `/api/cowork/layers` | 200 |
| `/api/cowork/corpus` | 200 |
| `/api/cowork/specs` | 200 (returns 6 features from `~/attune/specs/`) |
| `/api/cowork/templates` | 200 |
| `/api/cowork/files/raw/specs/...` | 200 |
| `/api/cowork/files/rendered/specs/...` | 200 (4501 chars HTML) |

---

## Known gaps (deliberate — not blockers)

- **No automated tests yet** for the new routes/templates. The spec called
  out "manual golden-path walkthrough" as the v1 acceptance gate; matching
  that posture for now. Easy to add later — the route handlers are pure
  functions with no side effects beyond file IO.
- **No CodeMirror / syntax highlighting** in the editor — plain `<textarea>`
  per the spec's v1 scope.
- **No live-reload for the doc list** — pages are server-rendered; you
  reload to see changes. Could add SSE/htmx later if you want.
- **`ATTUNE_SPECS_ROOT` env var** is the new way to point at a specs dir
  outside the workspace. Without it, the route walks up from `cwd` looking
  for `specs/`. If you launch from `~/attune/`, it Just Works.
- **Pin toggle works** but the regen-pipeline guard (Task 1 of the original
  spec, in `attune-author/regen.py`) is in attune-author and out of scope
  for this branch. Pin state is persisted to frontmatter regardless; the
  guard ensures attune-author respects it during regen.

---

## Recommended next steps after your review

1. **Try it** — visit each page, click around, edit a spec file via Preview/Edit, toggle a pin.
2. **If you like it** — merge `feat/cowork-dashboard-revival` to `main`. The React UI stays at `/legacy/` as a safety net.
3. **Once the Jinja dashboard is the daily driver** — drop `ui/` and the
   React static mount in a separate commit (Task 13 of the original spec),
   and the package gets dramatically smaller without npm in the build chain.
4. **Add tests** for the new route handlers before publishing to PyPI.
