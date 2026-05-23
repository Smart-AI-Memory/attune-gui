# Tasks — Templates page staleness alignment

**Status:** superseded — spec goal met by [#40](https://github.com/Smart-AI-Memory/attune-gui/pull/40) (and follow-ups [#42](https://github.com/Smart-AI-Memory/attune-gui/pull/42), [#43](https://github.com/Smart-AI-Memory/attune-gui/pull/43)) via a simpler per-request `check_workspace_staleness` call rather than the cache-layer design below. The Templates page now agrees with `author.maintain`; `very-stale` is gone; `manual` is exposed as a separate frontmatter-driven flag instead of being folded into the staleness domain. PR [#41](https://github.com/Smart-AI-Memory/attune-gui/pull/41) closed unmerged 2026-05-22. The cache + invalidation layer described in tasks 1–6 is parked: if a measured perf problem appears on real workspaces (>500ms cold list_templates), revisit; until then it's premature optimization.
**Spec:** [requirements.md](./requirements.md) · [design.md](./design.md)
**Date:** 2026-05-22

---

## Implementation order

Tasks are ordered so each one is independently testable. Backend/cache before wiring; wiring before UI; UI before cleanup. Mark status as you work: `pending` → `in-progress` → `done`.

| # | Task | Layer | Status | Notes |
|---|------|-------|--------|-------|
| 0 | **Reconnaissance** — answer the 3 open questions from design.md §"Open questions" | attune-gui | pending | Test fixtures (does attune-author publish one?), grep for `very-stale` assertions, locate badge CSS. Outputs feed tasks 6–7. ~30 min. |
| 1 | **Add `staleness_cache` service module** — `sidecar/attune_gui/services/staleness_cache.py` with `get_template_staleness`, `invalidate_workspace`, `invalidate_path`. In-memory dict, lazy population, graceful-degrade when `attune_author` not importable. | attune-gui | pending | Pure unit tests with a fake/mock `check_staleness`. No HTTP, no I/O beyond `check_staleness` itself. |
| 2 | **Map template path → owning feature** — helper used by task 1 to project a `FeatureStaleness.is_stale` onto every `*.md` template under `templates/<feature>/`. Files outside any feature dir → `"manual"`. | attune-gui | pending | Pure function, table-driven tests. Likely lives next to `staleness_cache.py`. |
| 3 | **Wire cache into `list_templates()`** — replace `_staleness(mtime)` call in `routes/cowork_templates.py:95` with `staleness_cache.get_template_staleness(workspace, rel_path)`. Update the `_staleness()` helper or delete it. Keep `last_modified` field untouched. | attune-gui | pending | Existing route tests need updating to new status domain (drop `very-stale`). |
| 4 | **Hook invalidation in `_author_proxy(invalidate_after=True)`** — extend `commands.py:99-106` to also call `staleness_cache.invalidate_workspace(Path(project_root_str))` alongside the existing RAG invalidate. | attune-gui | pending | Add test asserting cache entry for the workspace is gone after a maintain job completes. |
| 5 | **Hook invalidation in editor save endpoint** — `routes/editor_template.py` `/template/save`: on 200, call `staleness_cache.invalidate_path(workspace, saved_rel_path)`. Look up workspace from corpus root. | attune-gui | pending | Test: save → cache entry for that path is gone. Needs corpus→workspace lookup helper if not already factored out. |
| 6 | **Hook invalidation in watchfiles WS** — `routes/editor_ws.py`: on `file_changed` event for a template path, call `invalidate_path`. | attune-gui | pending | Test: simulate file_changed event → cache entry dropped. Watch out for noisy events (debounce already present? confirm). |
| 7 | **Update Templates page UI badges** — remove `very-stale` style; add `manual` and `unknown` styles. Tooltip copy from design.md §UI/UX. `last_modified` column becomes plain secondary text. | attune-gui | pending | Touches Jinja template + `cw-static/style.css` (paths from task 0 recon). Visual regression: manually verify on dashboard. |
| 8 | **Sweep tests for `"very-stale"` assertions** — replace with `"stale"`, or delete redundant tests where age-band granularity was the only thing being asserted. | attune-gui | pending | Driven by grep output from task 0. |
| 9 | **Remove dead code** — `_FRESH_DAYS`, `_STALE_DAYS`, `_staleness()` in `cowork_templates.py` are now unused. Drop the docstring section that describes mtime thresholds. | attune-gui | pending | Smallest possible cleanup commit. |
| 10 | **Docs** — update `README.md` (Templates row of the page table — staleness meaning changed) and `CHANGELOG.md` (under next version's "Changed" section). | attune-gui | pending | One-paragraph note: the badge now reflects semantic regen-needed, not file age. |

---

## Testing strategy

### Unit (`sidecar/tests/`)

- `test_staleness_cache.py` — covers tasks 1, 2:
  - cache miss → calls `check_staleness` once, populates all paths for the workspace
  - cache hit → no second `check_staleness` call
  - `invalidate_workspace` drops all entries for that workspace
  - `invalidate_path` drops a single entry
  - missing `attune_author` import → returns `"unknown"`, logs once
  - missing `features.yaml` → all paths return `"unknown"`
  - per-feature `check_staleness` exception → only that feature's templates are `"unknown"`
  - template path outside any feature dir → `"manual"`

- `test_cowork_templates.py` (extend existing) — covers task 3:
  - response includes new `staleness` values, never `"very-stale"`
  - `last_modified` field still present, unchanged shape

- `test_commands_author_proxy.py` (extend existing) — covers task 4:
  - maintain success calls both RAG and staleness invalidation

- `test_editor_template_save.py` (extend existing) — covers task 5:
  - save 200 → corresponding cache path invalidated

- `test_editor_ws.py` (extend existing) — covers task 6:
  - file_changed event → corresponding cache path invalidated

### Integration (`sidecar/tests/integration/`)

- One end-to-end test: workspace with mixed fresh/stale templates → GET `/api/cowork/templates` → run maintain → poll until job completes → GET again → previously-stale templates now report `fresh`. Confirms invalidation actually flows through.

### Visual / manual

Local dashboard check at `http://localhost:8765/dashboard/templates`:
- Templates show new badge palette
- `last_modified` is plain secondary text
- After running `author.maintain` from Commands page, reload Templates page → counts agree
- Disable attune-author import (rename installed package temporarily) → all rows show `unknown`, page still renders

### Performance check

On a workspace with ≥100 templates, time the first `list_templates()` call after sidecar restart. Acceptance: < 500ms for cold cache; < 50ms for warm. If cold exceeds 500ms, file a follow-up to push `check_staleness` into a background warmup on workspace-switch.

---

## Rollback plan

The change is additive at the storage layer (no migrations, no persisted state). To roll back:

1. Revert the PR.
2. No data migration needed — the in-memory cache vanishes on sidecar restart.
3. The `staleness` field's domain narrows, so any external consumer asserting `"very-stale"` would break. None known today (single-tenant local dashboard), but worth a `git log -S "very-stale"` sanity check before tagging the release.

Feature-flag option (if needed): gate `list_templates()` on an env var `ATTUNE_GUI_STALENESS_LEGACY=1` that restores the mtime path. Adds complexity; skip unless reviewers ask for it.

---

## Out of scope (deferred / explicitly punted)

- Persisting the freshness cache across sidecar restarts.
- Background-refresh of the Templates page (current manual-reload UX stays).
- Living Docs quality scoring alignment — separate spec if needed.
- Changing the underlying `attune_author.staleness` algorithm.

---

## Definition of done

- [ ] All 10 tasks marked `done`.
- [ ] All unit + integration tests pass.
- [ ] `ruff` + `mypy` clean.
- [ ] Manual visual check on local dashboard passes.
- [ ] Performance check meets the < 500ms cold / < 50ms warm gates.
- [ ] CHANGELOG entry written.
- [ ] PR opened referencing this spec directory.
