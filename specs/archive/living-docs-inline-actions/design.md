# Spec: Living Docs Inline Actions

## Phase 2: Design

**Status**: complete

### Architecture

Each row in the Documents table gets a **computed state** that reflects the full picture: base staleness, in-flight job, and pending review. The row's action column renders the right button(s) for that state. A smart poller keeps the table live while any regen is running.

The separate Review Queue section is removed from the page entirely.

```
┌──────────────────────────────────────────────────────────┐
│ /dashboard/living-docs (single page, no redirects)       │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Per-row cell, state-driven:                        │  │
│  │   current        → (small fresh badge)             │  │
│  │   stale          → [Regenerate]                    │  │
│  │   regenerating   → ⟳ "running attune-author…"      │  │
│  │   pending-review → [Approve] [Revert] + diff       │  │
│  │   errored        → ✗ "<error>" [Retry]             │  │
│  └────────────────────────────────────────────────────┘  │
│         │                                                │
│  GET /api/living-docs/rows                               │
│  (composed endpoint, server-side join)                   │
│         ▲                                                │
│         │                                                │
│  Smart poll, 1.5 s while any row is `regenerating`       │
│  Stops when no rows have regen_job_id                    │
│  No location.reload — DOM patch in place                 │
└──────────────────────────────────────────────────────────┘
```

To build each row the endpoint does:

1. `docs = store.list_docs()` — base status from the last scan
2. `queue = store.list_queue(reviewed=False)` — unreviewed items keyed by `doc_id`
3. `jobs = registry.list_jobs()` — filter to `name == "living-docs.regenerate"`, keyed by `args["doc_id"]`, keep most recent per doc_id

Then per doc: `computed_state = _project_doc_state(doc, queue_item, job)`.

### API changes

New endpoint: **`GET /api/living-docs/rows`**. No query parameters (future: `?persona=`).

Response shape:

```json
{
  "rows": [
    {
      "id": "auth/concept",
      "feature": "auth",
      "depth": "concept",
      "persona": "end_user",
      "base_status": "stale",
      "computed_state": "pending-review",
      "reason": "feature config changed",
      "last_modified": "2026-04-01T12:00:00+00:00",
      "regen_job_id": null,
      "regen_job_status": null,
      "regen_job_error": null,
      "queue_item_id": "e1a2b3c4",
      "diff_summary": "3 insertions(+), 1 deletion(-)"
    }
  ]
}
```

Fields `regen_job_id`, `regen_job_status`, `regen_job_error` are `null` unless the computed state is `regenerating` or `errored`. `queue_item_id` and `diff_summary` are `null` unless the computed state is `pending-review`.

Existing `/docs` and `/queue` endpoints stay untouched — they remain useful standalone for debugging and future surfaces.

### Data model changes

None. The composed endpoint is a read-only projection over existing models (`DocEntry`, `ReviewItem`, `Job`).

### UI/UX

**State priority rule (locked):**

```
regenerating  >  pending-review  >  errored  >  missing  >  stale  >  current
```

Rationale: the most action-requiring state wins the display. A doc that is simultaneously stale AND has a regen job running shows `regenerating` — the user's next action is to wait, not to click Regenerate again.

| State | Condition |
|---|---|
| `regenerating` | job exists AND `job.status in ("pending", "running")` |
| `pending-review` | unreviewed queue item exists (regardless of base_status) |
| `errored` | job exists AND `job.status == "errored"` AND no unreviewed queue item |
| `missing` | `doc.base_status == "missing"` AND no higher-priority state applies |
| `stale` | `doc.base_status == "stale"` AND no higher-priority state applies |
| `current` | default |

**Actions per state:**

| State | Action column renders |
|---|---|
| `current` | — (empty) |
| `stale` | **Regenerate** button |
| `missing` | **Regenerate** button |
| `pending-review` | **Approve** + **Revert** buttons; `diff_summary` one-liner below |
| `regenerating` | Spinner + last job log line (truncated to 60 chars); no buttons |
| `errored` | Error badge + last error message (truncated); **Retry** button |

The page must render correctly with zero JS — initial paint is the full state. JS only adds live updates.

### Cross-layer impact

attune-gui only. No changes to attune-rag, attune-help, or attune-author.

**Infrastructure preserved from PR #12 (do not refactor or rename):**

- `_regenerate_doc_executor` in `routes/living_docs.py`
- Job name `"living-docs.regenerate"`
- `POST /api/living-docs/docs/{id}/regenerate` endpoint
- `LivingDocsStore.add_to_queue()` / `.approve()` / `.revert()`
- The "Review →" follow-up link in `jobs.html` (still useful for users who navigate directly to Jobs)

### Tradeoffs & alternatives

**Locked design decisions** (debated and closed in the counsel session that produced this spec; do not reopen during implementation):

1. **Smart polling at 1.5s** — not configurable, not WebSocket, not longer interval.
2. **Composed `/api/living-docs/rows` endpoint** — server-side join, not client-side.
3. **State priority rule** — `regenerating > pending-review > errored > missing > stale > current`.
4. **Drop the Review Queue section** — it moves inline; the separate section is deleted.
5. **No `location.reload()`** — DOM patching only.

| Option | Pros | Cons | Chosen? |
|---|---|---|---|
| Smart polling, 1.5s | Trivial to implement and test; invisible to user; auto-stops when idle | Slightly more frontend complexity than `setInterval` reload | **Yes** |
| WebSocket push | Real-time | Connection lifecycle, reconnect, auth — multiple bug-fix rounds in editor's WS subsystem; latency budget here doesn't justify it | No |
| Naive 4s polling with `location.reload()` | Simplest to write | Loses scroll/focus, jarring, prohibited | No |
| Composed `/api/living-docs/rows` endpoint | Single round-trip; testable Python join (`_project_doc_state`); declarative template | Slightly more code than extending `/docs` | **Yes** |
| Extend `/docs` directly | ~30 min less today | Becomes a god-object as more inline-action surfaces land (Templates is next candidate) | No |
| Multiple thin endpoints + frontend join | No backend change | 3× fetches per poll, race conditions when endpoints fall out of sync, distributed state in JS | No |
| Server-Sent Events | Simpler than WS | Reframes the polling question rather than solving it; still need a hydration endpoint | No |

**Migration path** if smart polling proves inadequate: introduce a WS without changing the projection-endpoint contract — the same JSON shape can be served via WS push instead of polled. Easy to upgrade later; hard to downgrade.
