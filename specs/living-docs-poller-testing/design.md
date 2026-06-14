# Design: Testable Living Docs poll state machine

> Phase 2 design for `specs/living-docs-poller-testing/`. Read
> `requirements.md` first. Single layer: **attune-gui**. Reuses the
> no-build ES-module + Vitest pattern from
> [`dashboard-js-testing`](../dashboard-js-testing/) (and depends on its
> `static_cw/` infra + Vitest include glob — that PR merges first).

**Status**: approved (2026-06-14) — tasks: [`tasks.md`](tasks.md)

---

## Architecture

Same pattern as the batch panel: the **one pure decision** in the poller
moves to a `static_cw/` ES module; the inline `<script>` becomes a
`type="module"` shim that keeps all the imperative glue (timers, DOM,
`visibilitychange`) and calls the module.

The poller's only branch-worthy, bug-prone logic is the **stop
condition** at
[`living_docs.html:200`](attune-gui/sidecar/attune_gui/templates/living_docs.html):

```js
if (!data.rows.some(r => r.computed_state === 'regenerating')) { _stopPoll(); return; }
…
_scheduleNextPoll(1500);
```

Extracted module:

```js
// static_cw/living-docs-poller.js  (NEW)
export const POLL_INTERVAL_MS = 1500;

/** Keep polling iff at least one row is still regenerating. */
export function shouldKeepPolling(rows) {
  return Array.isArray(rows) && rows.some(
    (r) => r && r.computed_state === "regenerating",
  );
}
```

Everything else — `_startPoll` / `_stopPoll` / `_scheduleNextPoll`
(timers), the `visibilitychange` pause/resume, `_poll`'s fetch +
try/catch, `_applyRows` / `_renderBadge` / `_renderActions`, the action
button wiring, and the ws-form / scan-btn handlers — **stays inline**.
The block is converted to `<script type="module">` so it can `import`;
its functions were already block-scoped, and nothing external references
them (handlers attach via `addEventListener`, not inline `onclick`), so
module scope + `defer` semantics are safe.

The `_poll` change is one line:

```js
import { shouldKeepPolling, POLL_INTERVAL_MS } from '/cw-static/living-docs-poller.js';
…
if (!shouldKeepPolling(data.rows)) { _stopPoll(); return; }
…
_scheduleNextPoll(POLL_INTERVAL_MS);
```

> **Note on the initial-start check.** `_startPoll()` is also kicked off
> on load by a DOM query (`tr[data-state="regenerating"]`). That reads
> the rendered table, not row data, so it stays inline — `shouldKeepPolling`
> operates on the `/api/living-docs/rows` payload, which is the poll path.

## API changes

None. Pure client refactor; the poller consumes the same
`/api/living-docs/rows` shape.

## Data model changes

None.

## UI/UX

No change — polling cadence, start/stop behavior, hidden-tab pause, and
all row rendering are identical. The only delta is `<script type="module">`
(deferred) replacing the inline `<script>`; the block only attaches
handlers and an optional initial poll, so deferral is safe. Verified
live.

## Cross-layer impact

- **attune-gui** only: new `static_cw/living-docs-poller.js` + test, a
  one-block edit to `living_docs.html`.
- Depends on `dashboard-js-testing` (#68) for the `static_cw/` convention
  + the Vitest include glob — this work **stacks on that branch** and
  rebases onto `main` after it merges.

## Tradeoffs & alternatives

| Option | Pros | Cons | Chosen? |
|--------|------|------|---------|
| **Extract `shouldKeepPolling` + interval; keep glue inline** | Tests the one bug-prone decision; tiny, behavior-preserving; reuses the pattern | Most of the block stays untested (but it's imperative glue with no logic to test) | ✅ |
| Extract the whole poller (timers + visibility) into the module with injected `setTimeout`/`document` | More "coverage" | Mocking timers/visibility is high-ceremony for low value; the glue has no branching worth it | ❌ |
| Leave it inline | No change | The stop condition stays untested — the whole point | ❌ |
| De-dup badge/action maps too | Fixes the bigger drift risk | Out of scope (own spec) — needs an API-payload decision | ❌ (deferred) |

## Testing strategy

`static_cw/living-docs-poller.test.js` (Vitest, Node env, no jsdom):

1. `shouldKeepPolling` → true when any row is `regenerating`.
2. → false when no row is `regenerating` (mix of
   `current`/`stale`/`missing`/`pending-review`/`errored`).
3. → false for `[]`.
4. → false / no-throw for non-array input and rows with missing/`null`
   `computed_state` (defensive guards).
5. `POLL_INTERVAL_MS` is exported and equals 1500 (pins the cadence the
   shim relies on).

Plus a live re-verify: load `/dashboard/living-docs`, confirm the page
renders and (where a regenerating row exists) polling start/stop is
unchanged; no console errors; module served 200.

## Rollback

One-commit revert: restore the inline `.some(...)` check + `1500`, drop
`living-docs-poller.{js,test.js}`, revert the `<script>` tag. No
API/data migration; other blocks untouched.
