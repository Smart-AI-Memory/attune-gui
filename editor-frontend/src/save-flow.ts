/**
 * Save-flow primitives.
 *
 * The server is authoritative on the diff (it knows the on-disk base
 * and computes hunks via difflib). The client uses the returned hunk
 * list to render the per-hunk save modal and to compute the
 * **projected text** for partial selections — the result the save
 * endpoint would write if a given subset of hunks were accepted.
 *
 * The projection logic mirrors `editor_template._apply_accepted_hunks`
 * one-for-one so what the user sees in the projected lint is exactly
 * what the server will write. Keep the two in sync.
 */

import type { Hunk } from "./api";

interface ParsedHeader {
  /** 0-indexed start line in base. */
  start: number;
  /** Number of base lines this hunk covers. */
  count: number;
}

const HEADER_RE = /^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@/;

export function parseHunkHeader(header: string): ParsedHeader {
  const m = HEADER_RE.exec(header);
  if (!m) return { start: 0, count: 0 };
  const start = parseInt(m[1], 10);
  const count = m[2] !== undefined ? parseInt(m[2], 10) : 1;
  // difflib uses 1-indexed line numbers; for count==0 (pure
  // insertion) `start` is the line *before* the inserted content.
  if (count === 0) return { start, count };
  return { start: start - 1, count };
}

/**
 * Reapply only ``acceptedIds`` from ``hunks`` on top of ``baseText``.
 *
 * Mirrors :py:func:`_apply_accepted_hunks` on the server side.
 *
 * @param hunks — full hunk list from `/template/diff`, in document order.
 */
export function applyAcceptedHunks(
  baseText: string,
  hunks: readonly Hunk[],
  acceptedIds: ReadonlySet<string>,
): string {
  if (acceptedIds.size === 0) return baseText;

  const baseLines = baseText.split("\n");
  // `splitlines(keepends=False)` analogue: if base ends with `\n`,
  // the trailing element is "" — drop it so iteration matches Python.
  const trailingNl = baseText.endsWith("\n");
  if (trailingNl) baseLines.pop();

  const out: string[] = [];
  let cursor = 0;

  for (const hunk of hunks) {
    const { start, count } = parseHunkHeader(hunk.header);
    while (cursor < start) {
      if (cursor < baseLines.length) out.push(baseLines[cursor]);
      cursor += 1;
    }
    if (acceptedIds.has(hunk.hunk_id)) {
      for (const raw of hunk.lines) {
        if (raw.startsWith("+") || raw.startsWith(" ")) {
          out.push(raw.slice(1));
        }
        // `-` lines drop from the projection.
      }
    } else {
      for (let offset = 0; offset < count; offset += 1) {
        const idx = start + offset;
        if (idx < baseLines.length) out.push(baseLines[idx]);
      }
    }
    cursor = start + count;
  }

  while (cursor < baseLines.length) {
    out.push(baseLines[cursor]);
    cursor += 1;
  }

  return out.join("\n") + (trailingNl ? "\n" : "");
}

export interface SaveButtonLabel {
  /** Human label for the save button. */
  label: string;
  /** True iff at least one hunk is selected (button enabled). */
  enabled: boolean;
}

export function saveButtonLabel(total: number, accepted: number): SaveButtonLabel {
  if (total === 0) return { label: "No changes", enabled: false };
  if (accepted === 0) return { label: "Save 0 of " + total, enabled: false };
  if (accepted === total) return { label: total === 1 ? "Save 1 hunk" : `Save all ${total} hunks` , enabled: true };
  return { label: `Save ${accepted} of ${total} hunks`, enabled: true };
}
