# Spec: Living Docs Inline Actions

**Status**: complete

> Shipped via attune-gui PR #13 (`feat(living-docs): inline actions + smart polling`).
> Predecessor: PR #12 (`fix/living-docs-regen-jobs`) routed Regenerate through the Jobs system; this spec built the UI on top without changing the executor or job name.

---

## Phase 1: Requirements

**Status**: complete

### Problem statement

The Living Docs page splits one logical action (regenerate a stale doc, then approve or revert the result) across three pages and a hidden section:

1. **Living Docs** → user clicks `Regenerate` on a stale doc row.
2. Toast: "Started regen abc12345" → automatic redirect to **Jobs**.
3. Jobs page shows the running job; the user watches `output_lines` stream in for ~30–60s.
4. Job completes; user sees a green `completed` badge.
5. To approve, user must navigate back to **Living Docs** and scroll *past* the 15-row Documents table to find a "Review queue" section near the bottom of the page.
6. Click `Approve` or `Revert` there.

Real consequences observed during dogfooding:

- The user clicked Regenerate, watched the job complete, and never found the Approve/Revert buttons (they're below the fold of a separate page they have to navigate back to).
- A `manifest.features` iteration bug had been swallowed for an unknown duration by the legacy fire-and-forget BackgroundTask; surfacing it required moving to the Jobs system, which was a prerequisite for any further UX iteration.
- Six small UX patches in 90 minutes of dogfooding — banner fixes, badge fixes, jump-to-anchor links, Jobs-page follow-up links — without resolving the underlying too-many-hops problem.

The honest fix is structural: the doc row IS the action surface. Stay on Living Docs the whole time.

### Scope

**In scope:**

- Per-row state machine on the Documents table: `current` / `stale` / `regenerating` / `pending-review` / `errored` / `missing`.
- Inline action affordances in each row's last column — `Regenerate`, `Approve` + `Revert`, `Retry`, etc. — that change with the row's state.
- Inline progress feedback while a regen is running (spinner + last log line from the underlying job).
- A composed endpoint (`/api/living-docs/rows`) that joins docs, queue, and jobs server-side and returns rows ready to render.
- Smart polling (1.5s) so in-flight regen jobs update the row that owns them without leaving the page. Polling stops automatically once no row is `regenerating`.

**Out of scope** (named explicitly — do not implement even if they seem like obvious adjacent improvements):

- **Bulk-regenerate-all** button — own spec.
- **Full unified-diff inline preview** — only the `diff_summary` one-liner is shown.
- **Templates page migration** — structurally similar but a separate spec; do not touch `templates.html` or the Templates route.
- **WebSocket transport** — smart polling is the specified approach.
- **Optimistic UI on Approve/Revert** — poll after action, no optimistic state flip.

### User stories

1. *As a docs author*, when I see a doc is stale, I click `Regenerate` and the row immediately shows a spinner with live progress — without leaving the page.
2. *As a docs author*, when the regen completes, the same row becomes my approval surface — `Approve` and `Revert` buttons appear right where the action started, with the diff summary visible.
3. *As a docs author*, when a regen errors, I see the error in the row (not buried on a Jobs page) with a `Retry` button.
4. *As a power user*, I can still hit the Jobs page directly to see *all* in-flight work across all surfaces — the Living Docs work just isn't *forced* through that page anymore.

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Multiple regens running simultaneously (3 stale docs, click 3 buttons) | Each row has its own state. Three spinners; three independent state machines. The Jobs system already handles concurrency. |
| Regen kicked off via API (not the dashboard) | The composed endpoint sees the queue item the same way regardless of trigger. The row picks up `pending-review` state on next poll. |
| User leaves the page mid-regen | When they return, the page render reads the current job state from the registry; rows whose underlying job is still running show the spinner and start the poller on load. |
| Two browser tabs both open Living Docs | Both reflect the same backend state. Approve in tab A → tab B's row updates on next poll. Approve+Approve race is idempotent (queue item flips to `reviewed`; second approve no-ops). |
| `git diff --stat` is slow on large templates | Cache the `diff_summary` on the queue item (already does). Frontend renders the cached summary inline; full-diff expansion is a follow-up. |
| Regen errors with `Feature 'X' not in manifest` | Error surfaces in the row with the available-features list (same content the Jobs page used to show). `Retry` button is only useful after the user fixes the manifest. |

### Affected layers

- [ ] attune-rag (backend) — none
- [x] attune-gui (frontend + sidecar) — composed endpoint, redesigned `living_docs.html` per-row state machine, smart-polling JS controller, removed redirect-to-Jobs flow
- [ ] attune-help (mobile/docs) — none
- [ ] attune-author (authoring/infra) — none
