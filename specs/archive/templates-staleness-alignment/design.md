# Design — Templates page staleness alignment

**Status:** approved (Phase 2)
**Spec:** [requirements.md](./requirements.md)
**Date:** 2026-05-22

---

## Architecture

The Templates page becomes a **read-through view onto a freshness cache** populated from `attune_author.staleness.check_staleness`. mtime stops driving the badge entirely.

```
┌──────────────────────────┐       ┌────────────────────────┐
│ /dashboard/templates     │       │ /api/cowork/templates  │
│ (Jinja, renders pills)   │◀──────│ list_templates()       │
└──────────────────────────┘  JSON └──────────┬─────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │ staleness_cache.get_or_compute │
                              │ (per (workspace, path))        │
                              └──────────┬────────────────────┘
                                         │ miss
                                         ▼
                              ┌───────────────────────────────┐
                              │ attune_author.staleness        │
                              │ .check_staleness(manifest, …)  │
                              │ → per-feature is_stale         │
                              └───────────────────────────────┘

   Invalidation events:
     - author.maintain success    → drop entries for the workspace
     - editor /template/save 200  → drop entry for (workspace, path)
     - watchfiles file_changed    → drop entry for (workspace, path)
```

### Key shift in data model

`attune_author.staleness.check_staleness` returns **per-feature** verdicts (one `FeatureStaleness` per entry in `features.yaml`). The Templates page lists **per-file** entries. The cache must therefore:

1. Resolve each template `*.md` to its owning feature.
2. Project the feature's `is_stale` onto every template file that derives from it.

Mapping rule (matches the convention attune-author writes today): templates live under `<help_dir>/templates/<feature>/…`. Files outside any feature directory (and files in the new `manual` flow) get `staleness: "manual"` — they aren't auto-regenerated, so "stale" is not meaningful for them.

## API changes

`GET /api/cowork/templates` response stays structurally the same, but the `staleness` field's domain narrows:

| Old value | New value | Meaning |
|-----------|-----------|---------|
| `"fresh"` | `"fresh"` | `author.maintain` would not change this file |
| `"stale"` | `"stale"` | `author.maintain` would regenerate this file |
| `"very-stale"` | *(removed)* | Subsumed by `"stale"` — age is no longer the signal |
| — | `"manual"` *(new)* | File is hand-authored; not regenerated; stale-check N/A |
| — | `"unknown"` *(was: OSError fallback)* | Freshness check failed for this row; existing badge style reused |

The `last_modified` field remains. The new `manual` field on the response already exists (read from frontmatter) — no change there.

**No new endpoints.** The freshness cache is a sidecar-internal module, not surfaced over HTTP.

### Module layout

New: `sidecar/attune_gui/services/staleness_cache.py`

Public surface:

```python
def get_template_staleness(
    workspace: Path,
    template_rel_path: Path,
) -> Literal["fresh", "stale", "manual", "unknown"]: ...

def invalidate_workspace(workspace: Path) -> None: ...
def invalidate_path(workspace: Path, template_rel_path: Path) -> None: ...
```

Internals:
- In-process dict cache, keyed `(workspace_str, template_rel_str) → status`.
- Populated lazily; first call for a workspace runs `check_staleness` once, then projects every feature's verdict onto every owned template path in a single pass. Subsequent per-path calls are O(1) lookups.
- Graceful-degrade: if `attune_author.orchestration` or `attune_author.staleness` is not importable, return `"unknown"` and log once per workspace. Don't break the page.
- No persistence. In-memory only. Cleared on sidecar restart (per the requirements out-of-scope decision).

## Data model changes

None at the storage layer. The cache is ephemeral. Frontmatter and `features.yaml` continue to be the only persisted truth.

## UI/UX

**Templates page badge** (Jinja partial that renders the `staleness` field):

| Status | Color | Label | Tooltip |
|--------|-------|-------|---------|
| `fresh` | green | `Fresh` | "Up to date — running maintain would not change this file." |
| `stale` | amber | `Stale` | "Running maintain would regenerate this file." |
| `manual` | gray | `Manual` | "Hand-authored; not subject to regeneration." |
| `unknown` | gray | `Unknown` | "Freshness check unavailable — attune-author not loaded." |

Remove the `very-stale` style entirely.

New **`last_modified`** column treatment: keep the existing relative-time string ("32d ago"), but render it as plain secondary text — no color, no badge styling, no implied action.

### Triggering the cache on page load

`list_templates()` already iterates each `*.md` file. For each path, replace the inline `_staleness(mtime)` call with `staleness_cache.get_template_staleness(workspace, rel_path)`. The cache populates the whole workspace on first call inside that iteration.

## Cross-layer impact

None. The only cross-layer touch is **importing** `attune_author.staleness.check_staleness` — already on the dependency path via `commands.py`. No new dependencies on attune-rag or attune-help.

attune-author owns the staleness signal and remains the source of truth; we are only consuming it.

## Cross-cutting: invalidation hooks

Three sites need to call into the cache:

1. **`_author_proxy(invalidate_after=True)`** in `commands.py:99-106` — already invalidates the RAG pipeline cache after `author.maintain`. Add a sibling call:

   ```python
   from attune_gui.services.staleness_cache import invalidate_workspace
   invalidate_workspace(Path(project_root_str))
   ```

   This means *every* `author.*` command that opts into `invalidate_after=True` drops the cache for the affected workspace. That is correct — any author-side write can change freshness.

2. **Editor save endpoint** (`/api/corpus/<id>/template/save` in `routes/editor_template.py`) — on 200 OK, call `invalidate_path(workspace, saved_rel_path)`. The save just changed bytes on disk, so re-derive next request.

3. **Watchfiles WebSocket** (`routes/editor_ws.py`) — on `file_changed` event for a tracked template path, call `invalidate_path`. Catches external edits.

For #2 and #3 we need the workspace path. The corpus → workspace mapping already exists (the editor knows its corpus root); reuse that lookup.

## Tradeoffs & alternatives

| Option | Pros | Cons | Chosen? |
|--------|------|------|---------|
| In-memory cache, populated lazily | Simple, no persistence concerns, matches existing in-memory patterns (`tech.md` calls this "honest") | Cold-start cost on first Templates page load after sidecar restart | **Yes** |
| Persisted cache on disk (e.g., `~/.attune-gui/staleness-cache.json`) | Survives restarts, faster cold start | Persistence + invalidation surface bugs; cache can drift from disk silently | No — out of scope per requirements |
| Compute per-request, no cache | Trivial code | Slow on large libraries; semantic-hash is much heavier than `stat()` | No |
| Replace mtime with a "last_regen_check" timestamp from `concept.md` frontmatter | Reuses existing data, no compute | Doesn't actually answer "would maintain change this?" — still a proxy | No — same root problem as today |

## Failure modes & graceful degrade

| Failure | Behavior |
|---------|----------|
| `attune_author` not importable | Cache returns `"unknown"` for all paths; page renders with gray badges. Log once per workspace per sidecar lifetime. |
| `features.yaml` missing in workspace | Same as above — no manifest means no semantic-hash signal. Treat all templates as `"unknown"`. |
| `check_staleness` raises on a specific feature | Cache that feature's templates as `"unknown"`; other features still resolve normally. |
| Template path doesn't map to any feature in the manifest | Mark as `"manual"`. Matches today's frontmatter-driven manual flag. |
| Cache memory growth | Bounded by number of templates × number of workspaces visited. Realistic ceiling: thousands of entries, single-digit KB. No eviction needed. |

## Open questions for the tasks phase

These don't block design approval but need answers before implementation:

1. **Test fixtures:** does attune-author already publish a test helper that builds a manifest + sources + templates triplet for staleness assertions, or do we need to build it in attune-gui's test suite?
2. **Existing tests asserting `very-stale`:** sweep needed before we delete the status value.
3. **Frontend pill CSS:** where the badge styles live (Jinja template? `cw-static/style.css`?) and whether removing `very-stale` is one place or several.
