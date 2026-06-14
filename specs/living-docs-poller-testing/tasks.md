# Tasks: Testable Living Docs poll state machine

> Phase 3 for `specs/living-docs-poller-testing/`. Read `design.md`
> first. Single layer: **attune-gui**. Stacks on `dashboard-js-testing`
> (#68) for the `static_cw/` infra + Vitest include glob.

**Status**: approved (2026-06-14)

## Implementation order

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0 | Branch off `feat/dashboard-js-testing` (#68 infra) | pending | needs the Vitest include glob + static_cw README pattern |
| 1 | Create `static_cw/living-docs-poller.js` — `shouldKeepPolling(rows)` + `POLL_INTERVAL_MS` | pending | pure, DOM-free; defensive over non-array / missing `computed_state` |
| 2 | Create `static_cw/living-docs-poller.test.js` — 5 cases | pending | true/false/empty/defensive + interval constant |
| 3 | Convert the poller `<script>` block to `<script type="module">`; import the module | pending | replace inline `.some(...)` → `shouldKeepPolling`, `1500` → `POLL_INTERVAL_MS`; all other glue unchanged |
| 4 | Run Vitest — new tests + batch-panel + editor suites all green | pending | `cd editor-frontend && npm test` |
| 5 | Live re-verify Living Docs | pending | module 200, page renders, poll start/stop unchanged, no console errors |

## Testing strategy

Per `design.md`. Pure-logic Vitest (no jsdom):

1. `shouldKeepPolling` true when any row `regenerating`.
2. false when none (mix of other states).
3. false for `[]`.
4. false / no-throw for non-array input and rows with `null`/missing
   `computed_state`.
5. `POLL_INTERVAL_MS === 1500`.

Regression: task 4 must show `batch-panel.test.js` and the editor
`src/**/*.test.ts` suites still collected and green.

## Rollback plan

One-commit revert: restore the inline `.some(...)` + `1500`, delete
`living-docs-poller.{js,test.js}`, revert the `<script>` tag. No
API/data migration. Other inline blocks untouched.

## Notes / guardrails

- **Behavior-preserving only.** Task 5 live-verify is the gate.
- **Keep the module DOM/timer-free** — `setTimeout`, `document.hidden`,
  `visibilitychange`, and the initial DOM-query start stay in the inline
  shim.
- **Don't touch** `_renderBadge` / `_renderActions` — the badge/action
  de-dup is a separate deferred spec.
- **Stacks on #68** — open the PR against `main` noting it builds on #68;
  rebase onto `main` once #68 merges.
