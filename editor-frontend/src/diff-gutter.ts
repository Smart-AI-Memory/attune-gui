/**
 * Line-level diff gutter.
 *
 * Shows ``+`` (added), ``M`` (modified), and ``-`` (deleted) markers in
 * a CodeMirror gutter, computed from the difference between the editor's
 * current text and the base text the user opened.
 *
 * Implementation uses jsdiff line diffs — fast, deterministic, no DOM
 * required for the diff itself. The gutter re-renders on every doc
 * change; for templates of a few hundred lines this is comfortably
 * under one millisecond and avoids the complexity of incremental
 * range-set updates. We can move to a Decoration-based approach later
 * if profiling demands it.
 */

import { gutter, GutterMarker } from "@codemirror/view";
import {
  type Extension,
  StateEffect,
  StateField,
  RangeSetBuilder,
} from "@codemirror/state";
import { diffLines } from "diff";

type Kind = "added" | "removed" | "modified";

class DiffMarker extends GutterMarker {
  constructor(readonly kind: Kind) {
    super();
  }
  override toDOM(): Node {
    const el = document.createElement("span");
    el.className = `attune-diff-marker attune-diff-${this.kind}`;
    el.textContent = this.kind === "added" ? "+" : this.kind === "removed" ? "−" : "M";
    return el;
  }
  override eq(other: GutterMarker): boolean {
    return other instanceof DiffMarker && other.kind === this.kind;
  }
}

const ADDED = new DiffMarker("added");
const MODIFIED = new DiffMarker("modified");
const REMOVED = new DiffMarker("removed");

interface MarkerEntry {
  /** 1-indexed line in the current document. */
  line: number;
  marker: DiffMarker;
}

/** Compute per-line markers given the current text vs. the base text. */
export function computeDiffMarkers(base: string, current: string): MarkerEntry[] {
  if (base === current) return [];
  const parts = diffLines(base, current);
  const entries: MarkerEntry[] = [];
  let line = 1;
  for (let i = 0; i < parts.length; i += 1) {
    const part = parts[i];
    const next = parts[i + 1];
    const count = part.count ?? part.value.split("\n").length - 1;
    if (part.added) {
      // If the previous chunk was a removal of the same size, treat as
      // modification rather than add+remove.
      const prev = parts[i - 1];
      const isReplace = prev?.removed && (prev.count ?? 1) === count;
      const marker = isReplace ? MODIFIED : ADDED;
      for (let k = 0; k < count; k += 1) {
        entries.push({ line: line + k, marker });
      }
      line += count;
    } else if (part.removed) {
      // If followed by an addition of the same size, the addition will
      // emit MODIFIED markers — skip emitting "removed" markers here.
      const isReplace = next?.added && (next.count ?? 1) === count;
      if (!isReplace) {
        // Mark the line where the removed text used to be.
        entries.push({ line: Math.max(line, 1), marker: REMOVED });
      }
      // Removed lines do not advance `line` — they no longer exist in
      // the current document.
    } else {
      line += count;
    }
  }
  return entries;
}

/** State effect carrying the current set of diff markers. */
const setDiffMarkers = StateEffect.define<MarkerEntry[]>();

const diffMarkersField = StateField.define<MarkerEntry[]>({
  create: () => [],
  update(value, tr) {
    for (const e of tr.effects) {
      if (e.is(setDiffMarkers)) return e.value;
    }
    return value;
  },
});

/**
 * Build the gutter extension and a helper to update markers on doc edits.
 *
 * Caller is expected to dispatch ``updateDiffMarkers(view, base)`` on
 * every meaningful doc change (e.g., from an updateListener).
 */
export function diffGutter(): Extension {
  return [
    diffMarkersField,
    gutter({
      class: "attune-diff-gutter",
      markers(view) {
        const entries = view.state.field(diffMarkersField);
        const builder = new RangeSetBuilder<GutterMarker>();
        for (const { line, marker } of entries) {
          if (line < 1 || line > view.state.doc.lines) continue;
          const lineInfo = view.state.doc.line(line);
          builder.add(lineInfo.from, lineInfo.from, marker);
        }
        return builder.finish();
      },
    }),
  ];
}

/** Recompute markers and dispatch a state effect. */
export function updateDiffMarkers(
  view: { state: { doc: { toString(): string } }; dispatch(spec: unknown): void },
  base: string,
): void {
  const current = view.state.doc.toString();
  const entries = computeDiffMarkers(base, current);
  view.dispatch({ effects: setDiffMarkers.of(entries) });
}
