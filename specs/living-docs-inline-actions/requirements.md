# Living Docs — Inline Actions Redesign

**Status:** Approved (Phases 1–3)
**Branch:** `feat/living-docs-inline-actions` off `main`
**Predecessor:** PR #12 (`fix/living-docs-regen-jobs`) — routed Regenerate through the Jobs system. This spec builds the UI on top; it does NOT change the executor or job name.

---

## 1. Problem

The current Living Docs page has two disconnected sections:

1. **Documents table** — shows doc status; Regenerate button navigates away to `/dashboard/jobs`
2. **Review queue** — below the fold; no visible connection to the doc that produced each item

The user flow is:
> Click Regenerate → land on Jobs page → wait → navigate back to Living Docs → scroll to Review Queue → Approve/Revert

Every step after the first is friction. There is no way to watch regen progress without leaving the page, and Approve/Revert are invisible until the user remembers to scroll down.

---

## 2. Solution — Unified Rows with Inline Actions

Each row in the Documents table gets a **computed state** that reflects the full picture: base staleness, in-flight job, and pending review. The row's action column renders the right button(s) for that state. A smart poller keeps the table live while any regen is running.

The separate Review Queue section is removed from the page entirely.

### 2.1 Why smart polling, not WebSocket

This is a single-user localhost sidecar. WebSocket infrastructure adds complexity (connection lifecycle, reconnect, auth) for zero benefit. A 1.5s REST poll is invisible to the user and trivial to implement and test. Poll is active only while at least one row has a live `regen_job_id`; it stops itself automatically.

`location.reload()` is prohibited — it resets scroll position, flashes the page, and loses any partially-typed workspace input.

### 2.2 Why a composed endpoint, not client-side join

The client currently calls three endpoints (`/docs`, `/queue`, `/jobs`) and the template joins them in Python at render time. A composed `/api/living-docs/rows` endpoint moves the join server-side. Benefits:

- One network round-trip per poll instead of three
- State logic lives in Python where it's testable (`_project_doc_state`)
- Template stays declarative — renders what it's given

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

### 2.3 Row data derivation

To build each row the endpoint does:

1. `docs = store.list_docs()` — base status from the last scan
2. `queue = store.list_queue(reviewed=False)` — unreviewed items keyed by `doc_id`
3. `jobs = registry.list_jobs()` — filter to `name == "living-docs.regenerate"`, keyed by `args["doc_id"]`, keep most recent per doc_id

Then per doc: `computed_state = _project_doc_state(doc, queue_item, job)`

### 2.4 State priority rule (locked)

```
regenerating  >  pending-review  >  errored  >  missing  >  stale  >  current
```

This is a design decision, not a preference. Rationale: the most action-requiring state wins the display. A doc that is simultaneously stale AND has a regen job running shows `regenerating` — the user's next action is to wait, not to click Regenerate again.

Definitions:

| State | Condition |
|---|---|
| `regenerating` | job exists AND `job.status in ("pending", "running")` |
| `pending-review` | unreviewed queue item exists (regardless of base_status) |
| `errored` | job exists AND `job.status == "errored"` AND no unreviewed queue item |
| `missing` | `doc.base_status == "missing"` AND no higher-priority state applies |
| `stale` | `doc.base_status == "stale"` AND no higher-priority state applies |
| `current` | default |

### 2.5 Actions per state

| State | Action column renders |
|---|---|
| `current` | — (empty) |
| `stale` | **Regenerate** button |
| `missing` | **Regenerate** button |
| `pending-review` | **Approve** + **Revert** buttons; diff_summary one-liner below |
| `regenerating` | Spinner + last job log line (truncated to 60 chars); no buttons |
| `errored` | Error badge + last error message (truncated); **Retry** button |

---

## 3. 10 Ordered Tasks

### Task 1 — Extract `_project_doc_state` (pure function)

**File:** `sidecar/attune_gui/routes/living_docs.py`

Add a module-level function:

```python
def _project_doc_state(
    doc: dict[str, Any],
    queue_item: dict[str, Any] | None,
    job: dict[str, Any] | None,
) -> str:
```

Returns one of: `"regenerating"`, `"pending-review"`, `"errored"`, `"missing"`, `"stale"`, `"current"`.

Input contracts:
- `doc` — a `DocEntry.to_dict()` snapshot; `doc["status"]` is `"current"`, `"stale"`, or `"missing"`
- `queue_item` — a `ReviewItem.to_dict()` snapshot for the most recent **unreviewed** item for this `doc_id`, or `None`
- `job` — a `Job.to_dict()` snapshot for the most recent `living-docs.regenerate` job for this `doc_id`, or `None`

Must not import from `jobs.py` or `living_docs_store.py` (takes plain dicts — keeps tests fast).

### Task 2 — Composed `/api/living-docs/rows` endpoint

**File:** `sidecar/attune_gui/routes/living_docs.py`

```
GET /api/living-docs/rows
```

No query parameters for now (future: `?persona=`). Returns `{"rows": [...]}` per §2.2.

Implementation sketch:

```python
@router.get("/rows")
async def list_rows() -> dict[str, Any]:
    docs = await get_store().list_docs()
    queue_items = await get_store().list_queue(reviewed=False)
    all_jobs = get_registry().list_jobs()

    queue_by_doc: dict[str, dict] = {}
    for qi in queue_items:
        queue_by_doc.setdefault(qi["doc_id"], qi)

    regen_jobs: dict[str, dict] = {}
    for j in all_jobs:
        if j["name"] != "living-docs.regenerate":
            continue
        doc_id = j["args"].get("doc_id", "")
        if doc_id not in regen_jobs:
            regen_jobs[doc_id] = j  # list_jobs() already newest-first

    rows = []
    for doc in docs:
        doc_id = doc["id"]
        qi = queue_by_doc.get(doc_id)
        job = regen_jobs.get(doc_id)
        state = _project_doc_state(doc, qi, job)
        rows.append({
            "id": doc_id,
            "feature": doc["feature"],
            "depth": doc["depth"],
            "persona": doc["persona"],
            "base_status": doc["status"],
            "computed_state": state,
            "reason": doc.get("reason"),
            "last_modified": doc.get("last_modified"),
            "regen_job_id": job["id"] if state in ("regenerating", "errored") and job else None,
            "regen_job_status": job["status"] if state in ("regenerating", "errored") and job else None,
            "regen_job_error": job.get("error") if state == "errored" and job else None,
            "queue_item_id": qi["id"] if state == "pending-review" and qi else None,
            "diff_summary": qi.get("diff_summary") if state == "pending-review" and qi else None,
        })
    return {"rows": rows}
```

### Task 3 — Unit tests for `_project_doc_state`

**File:** `sidecar/tests/test_living_docs_inline.py` (new file)

Required test cases — cover every combination that hits a different branch:

| doc.status | queue_item | job.status | expected |
|---|---|---|---|
| `current` | None | None | `current` |
| `stale` | None | None | `stale` |
| `missing` | None | None | `missing` |
| `current` | exists | None | `pending-review` |
| `stale` | exists | None | `pending-review` |
| `current` | None | `running` | `regenerating` |
| `stale` | None | `pending` | `regenerating` |
| `current` | None | `errored` | `errored` |
| `stale` | None | `errored` | `errored` |
| `stale` | exists | `running` | `regenerating` (regen beats pending-review) |
| `stale` | exists | `errored` | `pending-review` (pending-review beats errored) |
| `current` | None | `completed` | `current` (completed job is irrelevant) |
| `stale` | None | `completed` | `stale` (completed job is irrelevant) |
| `missing` | None | `running` | `regenerating` |

Also test `/api/living-docs/rows` HTTP endpoint (one happy-path integration test — seed store + registry, assert response shape and computed_state values).

### Task 4 — Server-rendered initial paint

**File:** `sidecar/attune_gui/routes/cowork_pages.py`

Replace the `page_living_docs` handler to use `list_rows()` instead of the three separate calls. Pass `rows` to the template instead of `docs` + `queue`.

**File:** `sidecar/attune_gui/templates/living_docs.html`

Rewrite the Documents table to use `rows` instead of `docs`. Each `<tr>` gets:

```html
<tr data-doc-id="{{ row.id }}" data-state="{{ row.computed_state }}">
```

The action column uses Jinja conditionals on `row.computed_state` to render the right button(s) per §2.5.

Add a `<div class="diff-summary dim small">` inside the row (hidden unless state is `pending-review`) for the diff one-liner.

Remove the separate Review Queue `<section id="review-queue">` block entirely.

Remove the "Review queue" badge link from the `{% block actions %}` header.

The page must render correctly with zero JS — initial paint is the full state. JS only adds live updates.

### Task 5 — JS: smart polling + DOM patching

Still in `living_docs.html` `{% block scripts %}`.

Replace the existing Regenerate click handler (which navigated to `/dashboard/jobs`) with one that POSTs to regenerate and then **starts the poller** instead of navigating away.

Poller logic:

```js
let _pollTimer = null;

function _startPoll() {
  if (_pollTimer) return;
  _pollTimer = setInterval(_poll, 1500);
}

function _stopPoll() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

async function _poll() {
  if (document.hidden) return;
  const data = await AttuneUI.api('/api/living-docs/rows').catch(() => null);
  if (!data) return;
  _applyRows(data.rows);
  const hasLive = data.rows.some(r => r.computed_state === 'regenerating');
  if (!hasLive) _stopPoll();
}

function _applyRows(rows) {
  rows.forEach(row => {
    const tr = document.querySelector(`tr[data-doc-id="${CSS.escape(row.id)}"]`);
    if (!tr) return;
    tr.dataset.state = row.computed_state;
    _renderStateBadge(tr, row);
    _renderActionCell(tr, row);
  });
}
```

Start the poller on page load if any row already has `computed_state === 'regenerating'` (covers the reload-mid-job case).

`_renderStateBadge` and `_renderActionCell` write to specific child elements identified by `data-slot` attributes set in the Jinja template (e.g. `data-slot="badge"`, `data-slot="actions"`).

Do NOT use `innerHTML` on `<tr>` — patch the identified slots only to avoid clobbering event listeners on sibling cells.

### Task 6 — Wire Regenerate button

The Regenerate button (states `stale`, `missing`) posts to `/api/living-docs/docs/{id}/regenerate`. On success:

1. Optimistically set `tr.dataset.state = 'regenerating'` and render the spinner slot.
2. Call `_startPoll()`.
3. Show toast `"Regen started"` (no navigation).

On failure: toast error, re-enable button.

### Task 7 — Wire Approve and Revert buttons

Approve (`/api/living-docs/queue/{queue_item_id}/approve`): on success, call `_poll()` immediately (don't wait for next interval) to refresh the row.

Revert (`/api/living-docs/queue/{queue_item_id}/revert`): same — poll immediately after. No `location.reload()`.

Both buttons pull their IDs from `tr.dataset` attributes set by Task 4 Jinja rendering (e.g. `data-queue-item-id="{{ row.queue_item_id or '' }}"`).

### Task 8 — Cleanup (lands with or after Task 5)

- Remove the `setTimeout(() => location.reload(), ...)` calls from the workspace form and scan button. Replace with `_poll()` after a short debounce, or just `_poll()` directly.
- Remove the `setTimeout(() => location.assign('/dashboard/jobs'), ...)` from the old Regenerate handler (already replaced in Task 6, but make sure it's gone).
- Remove the `.btn-approve` and `.btn-revert` handlers from the old queue section (removed in Task 4, but audit the script block).
- Remove the "Review queue" header badge wiring if any JS references it.

### Task 9 — Playwright smoke test

**File:** `sidecar/tests/e2e/test_living_docs_inline.py` (new file, or add to existing e2e suite if one exists)

Three scenarios:
1. **Page loads without JS** — disable JS in Playwright, load `/dashboard/living-docs`, assert table rows render with correct badge text.
2. **Regenerate starts poller** — click Regenerate, assert spinner appears in the row, assert no navigation away.
3. **Approve clears row** — seed a pending-review row, click Approve, assert row transitions to `current` state without page reload.

Skip these tests in CI if Playwright is not installed (`pytest.importorskip("playwright")`).

### Task 10 — Open PR

One PR, title: `feat(living-docs): inline actions + smart polling`. Link to this spec. No squash.

---

## 4. Testing Strategy

The keystone is **unit tests on `_project_doc_state`** (Task 3). The function is pure — no I/O, no fixtures — so the full matrix of 14 cases runs in milliseconds. Get the priority rule right here and the composed endpoint and DOM patching follow mechanically.

After each task:
```bash
pytest sidecar/tests -q
ruff check sidecar/
make build-editor   # only if editor-frontend/ was touched (it won't be in this spec)
```

---

## 5. Dependencies

```
Task 1 → Task 3 (tests need the function)
Task 1 → Task 2 (endpoint calls _project_doc_state)
Task 2 → Task 3 (integration test hits the endpoint)
Task 4 → Task 5 (JS patches slots defined by Task 4 Jinja)
Task 4 → Task 6 (Regenerate button is in Task 4 template)
Task 5 → Task 7 (poller used by Approve/Revert handlers)
Task 8: lands with or after Task 5 (cleanup of old handlers)
Task 9: after Tasks 6–8 (tests the wired-up UI)
Task 10: after Task 9
```

Tasks 1 → 2 → 3 must land before Tasks 4 → 5.

---

## 6. Out of Scope

These are explicitly excluded. Do not implement even if they seem like obvious adjacent improvements:

- **Bulk-regenerate-all button** — own spec
- **Full unified-diff inline preview** — only `diff_summary` one-liner (from `ReviewItem.diff_summary`) is shown
- **Templates page migration** — structurally similar but a separate spec; do not touch `templates.html` or the Templates route
- **WebSocket transport** — smart polling is the specified approach
- **Optimistic UI on Approve/Revert** — poll after action, no optimistic state flip

---

## 7. Locked Design Decisions

These were debated and closed in the counsel session that produced this spec. Do not reopen them during implementation:

1. **Smart polling at 1.5s** — not configurable, not WebSocket, not longer interval
2. **Composed `/api/living-docs/rows` endpoint** — server-side join, not client-side
3. **State priority rule** — `regenerating > pending-review > errored > missing > stale > current`
4. **Drop the Review Queue section** — it moves inline; the separate section is deleted
5. **No `location.reload()`** — DOM patching only

---

## 8. Infrastructure Preserved from PR #12

These stay exactly as they are. Do not refactor or rename:

- `_regenerate_doc_executor` in `routes/living_docs.py`
- Job name `"living-docs.regenerate"`
- `POST /api/living-docs/docs/{id}/regenerate` endpoint
- `LivingDocsStore.add_to_queue()` / `.approve()` / `.revert()`
- The "Review →" follow-up link in `jobs.html` (still useful for users who navigate directly to Jobs)
