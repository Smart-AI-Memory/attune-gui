# Changelog

All notable changes to `attune-gui` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
