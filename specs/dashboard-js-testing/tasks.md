# Tasks: Testable Cowork dashboard JS

> Phase 3 for `specs/dashboard-js-testing/`. Read `design.md` first.
> Single layer: **attune-gui**. Branch off current `main` (batch panel
> from attune-gui#67 must be present in the tree).

**Status**: complete (2026-06-17) — shipped in attune-gui#68 (batch-panel ES module + Vitest, tasks 0–7 done, verified live); #67 was the prerequisite panel

## Implementation order

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0 | Branch off current `main` (post-#67) | done | `feat/dashboard-js-testing` off `fdea8ce` |
| 1 | Create `static_cw/batch-panel.js` — pure `isTerminal` / `batchView` / `shouldClose` (+ `TERMINAL`) | done | DOM-free; logic lifted verbatim from the inline IIFE |
| 2 | Create `static_cw/batch-panel.test.js` — 7 pure-logic cases | done | 14 assertions (it.each expands); colocated |
| 3 | Extend `editor-frontend/vitest.config.ts` include glob | done | added `../sidecar/attune_gui/static_cw/**/*.test.js` |
| 4 | Rewrite the inline panel script as `<script type="module">` glue | done | imports `batchView`/`shouldClose`; DOM-apply only |
| 5 | Run Vitest — dashboard tests pass **and** editor tests still pass | done | 107 passed (10 files); editor `src/**` still collected |
| 6 | Live re-verify the Living Docs page | done | `/cw-static/batch-panel.js` 200, SSE 200, panel hidden on no-batch, no console errors |
| 7 | Pattern doc: "Testing dashboard JS" | done | `static_cw/README.md` (colocated) |

> Shipped — all tasks complete; behavior-preserving, verified live.

## Testing strategy

Per `design.md` → Testing strategy. Pure-logic Vitest (Node env, no
jsdom) in `static_cw/batch-panel.test.js`:

1. `batchView({state:"none"})` → `{visible:false}`.
2. `batchView` error → visible, "Status unavailable", `detail` passthrough.
3. `batchView` pending → `pct` = done/total, `counts` string, label =
   `processing_status`.
4. `batchView` terminal → "Completed — N succeeded, M errored".
5. `isTerminal` → true for `ended`/`canceled`/`expired` and any
   `ended_at`; false otherwise.
6. `shouldClose` → true for none/error/terminal; false for pending
   non-terminal (**reconnect-suppression invariant**).
7. `request_count: 0` → `pct: 0`, not `NaN`.

Regression guard: task 5 must show the editor's existing `src/**/*.test.ts`
suite still collected and green after the include-glob change (don't
narrow it).

## Rollback plan

One-commit revert: restore the inline IIFE in `living_docs.html`, delete
`batch-panel.{js,test.js}`, remove the `vitest.config.ts` include line.
No route/schema/data migration. The other 7 inline blocks are untouched.

## Notes / guardrails

- **Behavior-preserving only.** No visual or behavioral change to the
  panel; task 6 live-verify is the gate.
- **Keep the module DOM-free** — any `document`/`window`/`EventSource`
  reference belongs in the inline shim, not `batch-panel.js`, or it won't
  import under Vitest (Node).
- **Don't narrow the editor glob** — task 3 *adds* an include entry; the
  editor's `src/**/*.test.ts` must keep running.
- **Scope discipline:** only the batch panel this PR. The other 7 inline
  blocks are explicitly follow-on work (the doc from task 7 is what makes
  them cheap).
