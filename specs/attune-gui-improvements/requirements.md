# attune-gui Improvements — Refined Plan

**Status:** Draft (pending review)
**Branch:** `claude/youthful-poincare-a23b2e`
**Predecessor:** v0.5.2 baseline

---

## 1. Problem

A critical review of attune-gui v0.5.2 surfaced four areas worth tightening:

1. The template editor depends on an unpublished submodule (`attune_rag.editor`), guarded at runtime — clean once upstream ships.
2. Living-docs state (review queue, quality scores) is in-memory only, so it disappears on sidecar restart and the user has to re-trigger work.
3. Configuration is split across `~/.attune-gui/config.json` and ad-hoc env vars (`ATTUNE_CORPORA_REGISTRY`, `ATTUNE_SPECS_ROOT`) with no unified surface.
4. The split between server-rendered Jinja and the Vite SPA in `editor-frontend/` is implicit — new contributors have to read code to figure out where things go.

The original review proposed broader changes (ABC interfaces, persisted job registry, full SPA migration). Those were rejected as speculative or counter to the existing "in-memory is honest" design. This spec captures only the four cuts that pay for themselves.

---

## 2. Solution — Four Independent Initiatives

Each initiative ships as its own PR. They have no dependencies on each other and can be picked up in any order.

### Initiative A — Drop the editor-backend guard once upstream ships

`sidecar/attune_gui/_editor_dep.py` exists solely to turn a `ModuleNotFoundError` for `attune_rag.editor` into a friendly 503. Five route files import `require_editor_submodule` lazily:

- `routes/editor_ws.py` (2 callsites)
- `routes/editor_schema.py`
- `routes/editor_template.py`
- `routes/editor_lint.py` (2 callsites)

This is **a tracking task, not new code**. Plan:

- **A1:** Add a `# TODO(attune_rag.editor):` marker in `_editor_dep.py` that names what to do when the upstream release lands. Pin the watch in CHANGELOG so it doesn't get lost.
- **A2:** *(Deferred until upstream)* Bump the `attune-rag` version pin in `pyproject.toml` to require the release that ships `editor`, replace each `require_editor_submodule(...)` callsite with a top-level `from attune_rag import editor as editor_mod` (or the appropriate submodule), delete `_editor_dep.py`, drop the lazy-import noqa comments.

A1 ships now. A2 is a *checklist note*, not a task to execute in this spec — flagged so we don't pretend otherwise.

### Initiative B — Persist living-docs state only

`living_docs_store.py` keeps three pieces of state in memory: the doc registry, the review queue, and quality scores from smoke evals. The review queue and quality scores have user-visible persistence value — losing them on restart forces the user to redo work. The doc registry is rescanned from disk on demand and does not need to persist.

**Storage choice:** a single JSON file at `~/.attune-gui/living_docs.json`. Under expected volumes (tens of queue items, low-cardinality scores) JSON beats SQLite on every axis: zero schema migration burden, human-readable, trivially testable, no new dependency. If the data grows to thousands of items or needs queries beyond `list_queue(reviewed=False)`, that's the trigger to revisit.

**Explicitly out of scope:** persisting `jobs.py`. The file's docstring says *"for a single-user localhost sidecar, an in-memory dict is honest"* and that remains correct — no user-facing problem motivates persisting jobs.

Plan:

- **B1:** Add `_load()` / `_save()` helpers in `living_docs_store.py`. Schema versioned with a top-level `"version": 1` field. Atomic writes via `tempfile + os.replace`.
- **B2:** Wire load on first access (lazy), save after every mutation that touches the queue or scores. Doc registry stays in-memory only.
- **B3:** Handle missing file (fresh install) and corrupt JSON (log a warning, start empty, do not crash). Add unit tests for both paths.

### Initiative C — Config consolidation + CLI

Today's config is a JSON file at `~/.attune-gui/config.json` with a single key (`workspace`), plus two env vars (`ATTUNE_CORPORA_REGISTRY`, `ATTUNE_SPECS_ROOT`) read in different modules. Path is **`~/.attune-gui/`, not `~/.attune/`** — the prior plan got that wrong.

Plan:

- **C1:** Document the schema in code (a typed loader that returns a frozen dataclass) and in README. Initial fields: `workspace` (existing), `corpora_registry` (replaces `ATTUNE_CORPORA_REGISTRY`), `specs_root` (replaces `ATTUNE_SPECS_ROOT`). Keep the file as JSON — adding TOML support means a new dep (`tomli-w` for writes) for no real win.
- **C2:** Add an `attune-gui config` subcommand: `--list`, `--get <key>`, `--set <key> <value>`. Implementation lives in `main.py` next to the existing `main()` entry point.
- **C3:** Precedence: env var > config file > built-in default. Env vars stay supported as overrides (CI / one-off runs) but the config file is the source of truth. Update the two existing env-var consumers (`editor_corpora.py:49`, `cowork_specs.py:99`) to read through the new loader.

### Initiative D — Frontend boundary decision

`editor-frontend/`'s `package.json` already documents the boundary informally: *"Output is pre-bundled into `../sidecar/attune_gui/static/editor/` and committed to the repo so attune-gui consumers do not need Node at install time."*

The decision is essentially already made — the template editor is a Vite SPA, everything else is Jinja. This initiative *codifies* that, so future contributors don't have to reverse-engineer it.

Plan:

- **D1:** Audit which UI surfaces live where. Confirm: `templates/editor.html` is the SPA mount point; the other 9 templates (`commands`, `health`, `jobs`, `living_docs`, `preview`, `specs`, `summaries`, `templates`, `base`) are pure server-rendered Jinja.
- **D2:** Add a `## Frontend architecture` section to README and a one-liner to CHANGELOG: *"Template editor is a Vite SPA mounted at `/editor`; all other dashboards are server-rendered Jinja. New UI defaults to Jinja unless it needs editor-grade interactivity (CodeMirror, conflict resolution, etc.)."*

No code changes. This is a documentation initiative.

---

## 3. Sequencing

A1, B, C, D are independent. Suggested order — D first (cheapest, lowest risk), then A1 (tiny), then B and C in parallel or either order.

A2 is parked until upstream attune-rag ships the editor submodule.

---

## 4. Out of Scope

- Persisting `jobs.py` state — the in-memory design is intentional.
- Abstract base classes for attune-* libraries — speculative; one consumer, no second implementation in sight.
- Migrating Jinja dashboards to SPA — `editor-frontend/` already absorbs the parts that need rich interactivity.
- Switching config from JSON to TOML — pure churn for a one-key file.

---

## 5. Tasks

<task id="D">
  <name>Document frontend boundary (Initiative D)</name>
  <objective>Codify the existing implicit rule: editor = Vite SPA, everything else = Jinja. Add a "Frontend architecture" section to README and a CHANGELOG entry. No code changes.</objective>
  <files>README.md, CHANGELOG.md</files>
  <risks>None — pure documentation.</risks>
</task>

<task id="A1">
  <name>Mark editor-backend guard for removal (Initiative A1)</name>
  <objective>Add a clear TODO marker in _editor_dep.py and a CHANGELOG note flagging the cleanup waiting on upstream attune_rag.editor publication. Do NOT remove the guard yet — A2 is parked.</objective>
  <files>sidecar/attune_gui/_editor_dep.py, CHANGELOG.md</files>
  <risks>None — documentation only.</risks>
</task>

<task id="B">
  <name>Persist living-docs review queue and quality scores (Initiative B)</name>
  <objective>Add JSON-file persistence to living_docs_store.py for the review queue and quality scores. Doc registry stays in-memory. Atomic writes, schema-versioned, graceful handling of missing/corrupt file. Unit tests for load/save and corruption recovery.</objective>
  <files>sidecar/attune_gui/living_docs_store.py, sidecar/tests/test_living_docs_store.py (new or extended)</files>
  <risks>State migration — first run after upgrade will see no persisted file (empty start, expected). Concurrent writes from a single asyncio loop are not a concern; a stray second process would race, but that's not a supported topology. Atomic replace mitigates partial writes.</risks>
</task>

<task id="C">
  <name>Config consolidation + CLI (Initiative C)</name>
  <objective>Introduce a typed config loader at ~/.attune-gui/config.json, fold in corpora_registry and specs_root (currently env-only), add `attune-gui config --list / --get / --set` subcommand, document precedence (env > file > default).</objective>
  <files>sidecar/attune_gui/workspace.py (or new config.py), sidecar/attune_gui/main.py, sidecar/attune_gui/editor_corpora.py, sidecar/attune_gui/routes/cowork_specs.py, README.md, sidecar/tests/test_config.py (new)</files>
  <risks>Backwards compatibility — existing users have a workspace key in the JSON and may have the env vars set. Loader must accept both old shape and new, env vars must keep working as overrides. Test the migration path explicitly.</risks>
</task>
