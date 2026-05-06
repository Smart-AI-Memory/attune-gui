# Changelog

All notable changes to `attune-gui` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Living Docs review queue + quality scores now persist across
  restarts.** Both pieces of state are written atomically to
  `~/.attune-gui/living_docs.json` (schema-versioned JSON, tempfile +
  `os.replace`). Missing or corrupt files start empty with a logged
  warning rather than crashing. The doc registry is still rescanned
  on demand and stays in-memory; jobs (`jobs.py`) remain in-memory
  by design.

### Documentation

- **Frontend boundary codified.** Added a "Frontend boundary" section
  to the README spelling out the rule contributors had to reverse-engineer:
  `/editor` is a Vite SPA, every other dashboard is server-rendered Jinja,
  new UI defaults to Jinja unless it needs editor-grade interactivity.

### Pending upstream

- **`attune_rag.editor` PyPI publication.** When upstream `attune-rag`
  ships the `editor` submodule in a public release, follow the
  step-by-step removal note in `sidecar/attune_gui/_editor_dep.py`:
  bump the pin, replace the 6 lazy `require_editor_submodule(...)`
  callsites in `routes/editor_*.py` with direct imports, delete
  `_editor_dep.py` and its tests.

## [0.5.2] — 2026-05-05

### Fixed

- **Templates page pin toggle now actually protects from regen.**
  The pin button was writing a top-level `manual: true` flag that
  attune-author does not read. Templates pinned through the dashboard
  were silently overwritten on the next `attune-author generate` /
  `regenerate`. Pin now writes `status: manual` (the canonical key
  attune-author honours). Reads still accept the legacy flag so
  existing files keep their badge; pin writes scrub the legacy key
  so files migrate forward on first save.

### Changed

- Refreshed `.help/templates/` for `sidecar`, `attune_gui-entry`,
  `scripts`, and `ui` after the 0.5.1 polish landed (12 templates,
  pure attune-author output, no hand edits).

---

## [0.5.1] — 2026-05-05

### Fixed

- **Editor backend dependency** — the template editor depends on
  `attune_rag.editor`, which was unpublished when 0.5.0 shipped. The
  pin now requires `attune-rag>=0.1.12`, and a runtime guard converts
  the legacy `ModuleNotFoundError` into a clean HTTP 503 with an
  actionable message if a user lands on a stale install.
- **Living-docs polling** — the page used `setInterval(1500ms)` and
  no-op'd on hidden tabs, so a backgrounded page still woke up every
  1.5s. Replaced with a `setTimeout` chain that pauses fully on
  hidden tabs and re-arms on `visibilitychange`. Transient API errors
  now keep polling instead of stopping silently.
- **Editor save → reload** — if the post-save reload failed, the
  editor was left with a saved file but stale base state and no
  surfaced error. Now the failed reload toasts and updates the status
  line so the user can retry.
- **Corpus switch errors** — `setActiveCorpus` rejections were
  silently swallowed. The switcher now surfaces them via an `onError`
  callback so the host can toast.

### Changed

- **Polish pass** across the editor + living-docs surfaces — ~340 net
  lines removed without changing behaviour. Notable: collapsed four
  near-identical "rebase the editor" blocks in `main.ts` into one
  helper; deleted the unused `summarize()` from `three-way-merge.ts`;
  removed the dead `EditorSession.rebase()` method (production never
  called it); dropped the legacy-bundle fallback in `editor_pages.py`;
  unified `attune_rag.editor._rename._hunks` lazy imports.
- **`atomic_write` helper** (`sidecar/attune_gui/_fs.py`) replaces three
  near-duplicate route-local impls; the `cowork_specs` / `cowork_files`
  variants leaked tmp files on exception and now inherit the robust
  cleanup path from the editor's version.
- **Test fixtures** — shared `client` and `session_token` fixtures
  moved to `sidecar/tests/conftest.py`; 17 test files were redefining
  them.

---

## [0.5.0] — 2026-05-04

### Removed — legacy React UI

The React/Vite UI has been retired. The Cowork dashboard at `/` is now
the only surface. This was always the plan from the `cowork-dashboard`
spec; 0.4.0 ran the two side-by-side to give you time to vet the new
one. With everything verified in production, the bundled React assets
are dead weight.

What goes away:
- `/legacy/` URL route — anyone with a bookmark gets a 404.
- `ui/` source tree (React + Vite + node_modules) — no more `npm install`
  to build the wheel.
- `sidecar/attune_gui/static/` — the built React assets that shipped in
  the wheel. Wheel size drops dramatically as a result.
- `build_hooks.py` — the hatchling hook that drove `npm run build`.
- `scripts/dev.sh` — the dual-runner script.
- The "Legacy UI ↗" link in the dashboard sidebar.

What stays the same:
- All JSON APIs (`/api/*`) — including the old ones that powered the
  React UI. Any external scripts hitting those continue to work.
- The Cowork dashboard at `/` — same routes, same look.
- Tests (124, all passing) — none of them hit the legacy mount.

If you need the old React UI for any reason, install `attune-gui==0.4.0`.

### Changed
- `pyproject.toml` description updated; sdist no longer includes `ui/*`
  or `build_hooks.py`.

---

## [0.4.0] — 2026-05-04

### Added — Spec authoring

The Specs page is no longer read-only. You can now create features, add
phases as you go, and transition status — all from the dashboard.

- **+ New spec** button on `/dashboard/specs` opens a slug input that
  bootstraps `specs/<slug>/requirements.md` from the workspace's
  `TEMPLATE.md` (falls back to a minimal stub if no template is found).
- **+ Design / + Tasks** inline buttons appear on each spec row at the
  appropriate moment, with prerequisite ordering enforced server-side
  (no design without requirements; no tasks without design).
- **Phase status dropdown** in the Preview/Edit panel for any spec file —
  rewrites the `**Status**:` line atomically (`draft → in-review →
  approved → complete`).
- New JSON APIs (all under `/api/cowork/`):
  - `GET  /specs/template` — fetch the canonical template
  - `POST /specs` — create a new feature directory
  - `POST /specs/{feature}/phase` — bootstrap design or tasks
  - `PUT  /specs/{feature}/{phase}/status` — transition status
- Slug validation: lowercase letters, digits, dashes; max 63 chars.
- 19 new tests covering the authoring flow, validation, and ordering rules.
  Suite total: **124 tests**, all passing.

### Fixed

- **Summaries page** no longer shows a red error banner when
  `summaries.json` doesn't exist yet. A missing file is the expected state
  on a fresh workspace (the polish pass hasn't run), so the page now
  renders a centered empty-state card with the exact
  `attune-author polish` command to generate it. Genuine errors (corrupt
  JSON, real I/O failures) still surface the danger banner.

---

## [0.3.0] — 2026-05-04

### Added — Cowork dashboard
A server-rendered Jinja2 dashboard mounted at `/`, with the React/Vite UI
preserved at `/legacy/` for fallback. Sidebar nav: **Health · Templates ·
Specs · Summaries · Living Docs · Commands · Jobs**.

- New JSON APIs under `/api/cowork/`:
  - `GET /layers` — `importlib.metadata` probe per attune layer
  - `GET /corpus` — workspace + template count + summaries presence
  - `GET /specs` — feature spec list with inferred phase + status
  - `GET /templates` — template list with mtime staleness + manual flag
  - `GET /files/raw/{root}/{path}` — read raw file (returns content + manual)
  - `PUT /files/raw/{root}/{path}` — atomic write
  - `GET /files/rendered/{root}/{path}` — markdown → HTML fragment
  - `POST /files/pin/{root}/{path}` — toggle the `manual: true` frontmatter flag
- New HTML page routes (Jinja2 templates):
  - `/dashboard` (Health), `/dashboard/templates`, `/dashboard/specs`,
    `/dashboard/summaries`, `/dashboard/preview`, `/dashboard/living-docs`,
    `/dashboard/commands`, `/dashboard/jobs`
- Per-page CSS in `static_cw/style.css` matching the design tokens from the
  approved `cowork-dashboard` spec.

### Added — Sidecar quality of life
- **`.env` auto-loading** at sidecar start. Searches `./`, `<repo-root>/`,
  `~/.attune-gui/`, `~/.attune/` and loads `KEY=value` lines without
  overwriting real existing env vars. Empty/whitespace existing values are
  treated as unset and replaced. Supports `export KEY=value`, quoted
  values, and `#` comments. No `python-dotenv` dependency added.
- **Anthropic SDK** pulled in via `attune-author[ai]` extra so
  `author.regen` and `author.maintain` jobs work out of the box.

### Added — Jobs page UX
- Per-feature progress in `author.maintain` (was previously silent during
  multi-minute runs, looking "stuck").
- "Last output" column on `/dashboard/jobs` shows the latest output line.
- **Cancel** button on running/pending rows (calls `DELETE /api/jobs/{id}`).
- Auto-refresh every 4s while a job is running, paused when the tab is hidden.

### Added — Tests
- 55 new tests covering: dotenv loader, cowork health, cowork specs (incl.
  resolver), cowork templates (incl. resolver + staleness thresholds),
  cowork files (read/write/render/pin/path-traversal), cowork pages.
- Suite total: **105 tests**, all passing.

### Changed
- `pyproject.toml` description rewritten to reflect the dual-UI reality.
- `attune-author` dependency now uses the `[ai]` extra so the Anthropic
  SDK is installed by default.
- `app.py` mounts the legacy React UI at `/legacy/` instead of `/`.

### Internals
- Token header for mutating routes corrected in the new dashboard from
  `X-Attune-Client-Token` to `X-Attune-Client` (matches `security.py`).
- File API URL prefixes restructured (`/raw/`, `/rendered/`, `/pin/`)
  so the greedy `:path` converter cannot swallow action suffixes.

---

## [0.2.1]
- Filesystem directory picker for path fields.

## [0.2.0]
- Setup help + Regenerate templates commands.

## [0.1.0]
- Initial release: React + Vite UI, sidecar with Commands and Living Docs
  modes, profile switching, RAG quality gates.
