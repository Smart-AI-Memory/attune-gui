# Tasks: Testable Cowork dashboard JS

> Phase 3 for `specs/dashboard-js-testing/`. Read `design.md` first.
> Single layer: **attune-gui**. Branch off current `main` (batch panel
> from attune-gui#67 must be present in the tree).

**Status**: approved (2026-06-14)

## Implementation order

| # | Task | Status | Notes |
|---|------|--------|-------|
| 0 | Branch off current `main` (post-#67) | pending | the inline `batchProgress` IIFE must exist in `living_docs.html` to extract |
| 1 | Create `static_cw/batch-panel.js` — pure `isTerminal` / `batchView` / `shouldClose` (+ `TERMINAL`) | pending | DOM-free, `window`-free; exact logic lifted from the current inline IIFE |
| 2 | Create `static_cw/batch-panel.test.js` — 7 pure-logic cases | pending | colocated; `import { … } from './batch-panel.js'` |
| 3 | Extend `editor-frontend/vitest.config.ts` include glob | pending | add `"../sidecar/attune_gui/static_cw/**/*.test.js"` |
| 4 | Rewrite the inline panel script as `<script type="module">` glue | pending | imports `batchView`/`shouldClose`; DOM-apply only, no branching; behavior byte-equivalent |
| 5 | Run Vitest — dashboard tests pass **and** editor tests still pass | pending | `cd editor-frontend && npm test`; confirm both globs collected |
| 6 | Live re-verify the Living Docs page | pending | preview: `GET /api/batch/status/stream` → 200, panel hidden on no-batch, no console errors — identical to today |
| 7 | Pattern doc: "Testing dashboard JS" | pending | short page (extract pure fn → module → Vitest); cite batch-panel as the example; note the other 7 inline blocks follow this |

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
