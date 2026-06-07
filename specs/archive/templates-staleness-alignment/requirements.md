# Spec: Templates page staleness alignment

**Status:** approved (Phase 1)
**Layer:** attune-gui (single-layer)
**Author:** Patrick Roebuck (silversurfer562@gmail.com)
**Date:** 2026-05-22

---

## Phase 1: Requirements

### Problem statement

The dashboard exposes two contradictory definitions of "stale":

| Surface | Signal | Source |
|---------|--------|--------|
| `/dashboard/templates` (Templates page) | File mtime: fresh < 14d, stale 14–60d, very-stale ≥ 60d | `sidecar/attune_gui/routes/cowork_templates.py:39-45` |
| `author.maintain` (Commands page) | Semantic-hash mismatch — would regen produce different bytes? | attune-author orchestration (`_AUTHOR_COMMANDS["author.maintain"]`) |

These signals disagree in the common case: a template generated two months ago that still matches its source shows red "very-stale" pills on the Templates page, but `author.maintain` finishes in milliseconds reporting `Stale: 0 / 5` with nothing to regenerate. Users (Patrick, repro 2026-05-22) reasonably conclude either the page is broken or the command is broken — actually they just answer different questions.

**Why now:** Surfaced live during an exploratory dashboard session. The dual-signal confusion blocks trust in the Templates page as an actionable surface, and the inconsistency will only get worse as more "staleness" UIs get added (Living Docs already has its own scoring).

### Scope

**In scope:**
- Replace the mtime-derived `staleness` field returned by `GET /api/cowork/templates` (and consumed by `/dashboard/templates`) with the same semantic-hash signal `author.maintain` uses.
- Demote mtime to a secondary informational field (`last_modified`) — keep it, but it no longer drives the badge.
- A freshness cache so the Templates page doesn't pay the semantic-hash cost on every render (see *Edge cases* below).
- Update the Templates page UI: the "fresh / stale / very-stale" pill becomes a binary "fresh / stale" pill where "stale" = "maintain would change this file."

**Out of scope:**
- Living Docs quality scoring — separate signal, not in conflict here.
- Changing `author.maintain` itself.
- Background-refresh of the Templates page (current behavior — manual reload after maintain — is fine).
- Persisting the freshness cache across sidecar restarts — in-memory is acceptable.

### User stories

1. **As a developer browsing my template library**, I want the "stale" badge on the Templates page to mean *"running maintain would change this file"*, so that I can trust the badge as an actionable signal instead of treating it as a stale-by-age proxy.
2. **As a developer who just ran `author.maintain`** and saw `Stale: 0 / 5`, I want the Templates page to immediately stop showing stale pills on those files, so the dashboard's signals agree across pages.
3. **As a developer with hundreds of templates**, I want the Templates page to render in well under a second, so the new semantic-hash check must be cached, not computed per-request.

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Semantic-hash cost on first load (cold cache) | Compute once on first request after sidecar start; populate an in-memory cache keyed by `(corpus_id, path)`. Subsequent loads use cache. |
| Cache invalidation after `author.maintain` | The `_author_proxy(invalidate_after=True)` wrapper already invalidates the RAG pipeline cache (`commands.py:99-106`). Hook the same callback to drop the staleness cache for affected paths. |
| Cache invalidation on file edit via `/editor` | The editor's atomic-save endpoint (`/template/save`) should drop the cache entry for the saved path. WS `file_changed` events from `watchfiles` should drop entries for externally-edited files. |
| What if `attune-author` isn't installed? | Today: Templates page works because mtime needs no external dep. After change: if `attune_author.orchestration` import fails, fall back to a "freshness unknown" badge (gray, no pill color) — don't break the page. |
| What if the corpus is `kind: "generated"`? | Same semantic-hash signal applies. The "generated-corpus advisory" banner already warns about edits being overwritten — that's separate UX. |
| Display of mtime once it stops driving the badge | Keep as a `last_modified` column (relative, "32d ago") for context. No color, no action implied. |
| Behavior when the semantic-hash check itself errors on a single template | Per-template: log + show "freshness unknown" badge for that row only. Don't fail the whole page. |
| Existing API consumers of the `staleness` field | The field stays in the JSON response; its meaning changes from age-based to hash-based. Tests need updating; no known external consumers (single-tenant dashboard). |

### Affected layers

- [x] attune-gui (sole layer touched)
- [ ] attune-rag
- [ ] attune-help
- [ ] attune-author (consumed as a library — no changes)

### Decision: Approach A (single source of truth)

Three approaches were considered (raised in the 2026-05-22 session):

| Option | Approach | Decision |
|--------|----------|----------|
| **A** | Templates page calls the same semantic-hash signal `author.maintain` uses. mtime drops to a `last_modified` column. One signal, one truth. | **Chosen.** |
| B | Keep mtime, rename the badge to be honest ("60d ago" instead of red "very-stale"). No alignment with maintain. | Rejected — papers over the real bug. |
| C | Two badges: semantic-stale (actionable) + mtime hint (informational). | Rejected — most UI complexity, forces every user to learn two definitions of stale. |

**Rationale for A:**
- Eliminates the contradiction at the root, not the surface.
- "Stale = maintain would change this" is a verifiable, actionable claim. mtime is a proxy that's frequently wrong.
- One badge, one truth — lowest long-term UI maintenance cost.
- The performance concern (semantic hash is heavier than `stat()`) is real but bounded — solved with an in-memory cache keyed by `(corpus_id, path)`, invalidated on maintain / save / file-change.

---

## Phase 2: Design

**Status:** draft (pending — start after this requirements doc is reviewed)

---

## Phase 3: Tasks

**Status:** pending

---

## Phase 4: Implementation

**Status:** pending
