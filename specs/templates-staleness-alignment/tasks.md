# Tasks — Templates page staleness alignment

**Status:** **superseded by shipped work — closing this spec** (2026-05-22)
**Spec:** [requirements.md](./requirements.md) · [design.md](./design.md)
**Date:** 2026-05-22

---

## What actually shipped

The outcome (Templates page agrees with `attune-author status`) shipped via a leaner path than the design proposed. The `staleness_cache` service module (design.md §Architecture) was **not built** — `check_workspace_staleness` is called inline in `list_templates()` on every request. Single-user localhost sidecar with ≤ a few hundred templates: the perf gate the cache was meant to protect ([< 500ms cold / < 50ms warm](./tasks.md#performance-check)) is met without it. Re-introduce the cache only if a future workspace blows past those numbers.

The `"manual"` staleness value (design.md §API changes) was also not added — `manual` stayed a separate boolean field on the response (`status: manual` in frontmatter), which the UI already renders as its own badge alongside the staleness pill. The staleness domain is now **`fresh` / `stale` / `unknown`** (3 values), not the 4 the design proposed.

### Done

| # | Task | Where it landed |
|---|------|-----------------|
| 3 | Wire `check_workspace_staleness` into `list_templates()`; replace mtime helper | [`routes/cowork_templates.py`](../../sidecar/attune_gui/routes/cowork_templates.py) — PR [#40](https://github.com/Smart-AI-Memory/attune-gui/pull/40) (commit `20f7618`) |
| 8 | Sweep tests for `"very-stale"` assertions | `test_cowork_templates.py`, `test_home_summary.py` — PRs #40, [#43](https://github.com/Smart-AI-Memory/attune-gui/pull/43) |
| 9 | Remove dead `_FRESH_DAYS` / `_STALE_DAYS` / `_staleness()`; drop `very_stale` field on `TemplateKpi`; strip the `{% elif t.staleness == 'very-stale' %}` branch from `templates.html`; simplify `home.html` fresh-ratio math; drop `"very-stale"` from the filter literal in `cowork_pages.py` | PRs #40, #43 (commit `9a30239`) |
| 10 | Docs — CHANGELOG `[Unreleased] § Changed` updated; README templates row carries the new semantics | This worktree (will land with the 0.7.1 release) |

### Punted (re-open as a follow-up spec only if perf or correctness demands it)

| # | Task | Why punted |
|---|------|------------|
| 1 | `staleness_cache` service module | Perf gate met inline; cache is speculative until a workspace exceeds the threshold. Re-open with a measurement, not a hypothesis. |
| 2 | Path → feature mapping helper (as a standalone module) | The 4-line projection now lives inline in `list_templates()` (the `feature_name = rel.parts[0] if len(rel.parts) >= 2 else None` block). Pure function, table-driven tests are still cheap if/when it moves. |
| 4 | Invalidate cache from `_author_proxy(invalidate_after=True)` | Moot without a cache. |
| 5 | Invalidate cache from editor save endpoint | Moot without a cache. |
| 6 | Invalidate cache from watchfiles WS | Moot without a cache. |
| 7 | Add `manual` badge style on the Templates page | `manual` stayed a separate boolean field — UI already shows it as its own badge, so no new style needed. Keep an eye on whether users find the two-badge layout confusing; if so, the right answer is a UI redesign, not promoting `manual` into the staleness enum. |
| 0 | Reconnaissance (badge CSS, fixture audit) | Subsumed by PR #43's direct cleanup; no longer a separate step. |

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

- [x] Templates page agrees with `attune-author status` (the original problem statement).
- [x] `very-stale` removed from the codebase end-to-end (route, UI, KPIs, tests).
- [x] All unit + integration tests pass (`PYTHONPATH=sidecar pytest` clean on touched files).
- [x] CHANGELOG entry written (`[Unreleased] § Changed`, lands with 0.7.1).
- [ ] ~~PR opened referencing this spec directory~~ — superseded by PRs #40 and #43, which closed the work pragmatically without referencing the spec. Acceptable in retrospect; the spec is being closed in lieu of opening a tracking PR.
- [ ] ~~`staleness_cache` service module + invalidation wiring~~ — **punted** (see "What actually shipped" above).
- [ ] ~~`manual` badge style~~ — **not needed** (manual is a separate field, not a staleness value).

### Lesson for next time

The design proposed a cache layer before measuring whether one was needed. The implementation correctly skipped it. Future staleness/perf specs: state the measured baseline first, then design only the layers that move it. The cache stays available as a follow-up if/when measurement justifies it.
